import io
import json
import time
import tools
import telebot
import aiohttp
import asyncio
import requests
from datetime import timedelta
import matplotlib.pyplot as plt
from urllib.parse import urlparse
from urllib.parse import parse_qs
from telebot.async_telebot import AsyncTeleBot

SERVER_ADDRESS = 'https://api.openworkshop.su'
WEBSITE_ADDRESS = 'https://openworkshop.su'

with open('key.json', 'r') as file:
    # Загружаем содержимое файла в переменную
    API_TOKEN = json.load(file)["key"]

bot = AsyncTeleBot(API_TOKEN)


@bot.message_handler(commands=['help', 'start', "старт", "помощь"])
async def send_welcome(message):
    await bot.reply_to(message, """\
Этот бот позволяет скачивать моды со *Steam* через чат *Telegram!* 💨\n
Разработчики не несут ответственность за контент получаемый через бота и ваши намеренья как его использовать. 📄\n
А так же продолжая использовать бота вы подтверждаете, что официально приобрели игру/программу на одной из площадок где она представлена! 🛒
    """, parse_mode="Markdown")
    await bot.reply_to(message, """\
Чтобы получить `ZIP` архив отправьте ссылку на мод или `ID` мода в *Steam* и бот в ответ даст `ZIP` архив 🤝
    """, parse_mode="Markdown")

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text='Клик!', url='https://steamdb.info/sub/17906/apps/'))
    await bot.reply_to(message, """\
Вот список поддерживаемых игр 👀
    """, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=['project', 'проект'])
async def project(message):
    global SERVER_ADDRESS

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text='GitHub проекта', url='https://github.com/Open-Workshop'))
    markup.add(telebot.types.InlineKeyboardButton(text='Telegram канал автора', url='https://t.me/sphere_games'))
    markup.add(telebot.types.InlineKeyboardButton(text='Такой же бот в Discord', url='https://discord.com/api/oauth2/authorize?client_id=1137841106852253818&permissions=2148038720&scope=bot%20applications.commands'))
    markup.add(telebot.types.InlineKeyboardButton(text='API бота', url=SERVER_ADDRESS+'/docs'))
    markup.add(telebot.types.InlineKeyboardButton(text='Сайт', url=WEBSITE_ADDRESS))

    await bot.send_message(message.chat.id, 'Это бесплатный **open-source** проект с **открытым API**! 😍', parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=['statistics', 'статистика'])
async def statistics(message):
    global SERVER_ADDRESS
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(url=SERVER_ADDRESS + "/statistics/info/all", timeout=10)

            text = await response.text()
            info = json.loads(text)

            await bot.send_message(message.chat.id, f"""
Пользователям отправлено {info.get('mods_sent_count')} файлов.
Сервис работает {await tools.format_seconds(seconds=info.get('statistics_days', 0), word="день")}.

У {info.get('games', 0)} игр сохранено {info.get('mods', 0)} модов, {info.get('mods_dependencies', 0)} из которых имеют зависимости на другие моды.
Сервису известно об {await tools.format_seconds(seconds=info.get('genres', 0), word="жанр")} игр и {await tools.format_seconds(seconds=info.get('mods_tags', 0), word="тег")} для модов.
                """)
    except asyncio.TimeoutError:
        await bot.send_message("Превышено время ожидания при получении общей статистики.")


type_map = None

@bot.message_handler(commands=['graph', 'график'])
async def graph(message):
    plt.clf()
    global type_map

    try:
        if not type_map:
            async with aiohttp.ClientSession() as session:
                resource = await session.get(url=SERVER_ADDRESS+"/statistics/info/type_map", headers={"Accept-Language": "ru, en"}, timeout=10)

                content = await resource.text()

                info = json.loads(content)
                type_map = info["result"]
    except:
        await bot.send_message(message.chat.id, "При получении переводов возникла странная ошибка...")

    try:
        async with aiohttp.ClientSession() as session:
            resource = await session.get(url=SERVER_ADDRESS+"/statistics/hour", timeout=10)
            content = await resource.text()
            info = json.loads(content)

            output = await tools.graf(info, "date_time")
            for i in output[0].keys():
                plt.plot(output[0][i][0], output[0][i][1], label=type_map.get(i, "ERROR"))

            # Настройка внешнего вида графика
            plt.title("Статистика сегодня")
            plt.xlabel("Час")
            plt.ylabel("Кол-во обращений")
            plt.legend(fontsize='xx-small')
            # Задаем метки делений на оси x
            plt.xticks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23])
            # Создание объекта для сохранения изображения в памяти
            buffer = io.BytesIO()
            # Сохранение графика в буфер
            plt.savefig(buffer, format='png')
            buffer.seek(0)

            # Отправка изображения через Telegram Bot API
            await bot.send_photo(chat_id=message.chat.id, photo=buffer)
    except:
        await bot.send_message(message.chat.id, "При получении статистики за день возникла странная ошибка...")

    try:
        async with aiohttp.ClientSession() as session:
            plt.clf()

            resource = await session.get(url=SERVER_ADDRESS+"/statistics/day", timeout=10)
            content = await resource.text()
            info = json.loads(content)

            output = await tools.graf(info, "date")

            shift = output[1][0].toordinal()
            for i in output[0].keys():
                plt.plot([x - shift for x in output[0][i][0]], output[0][i][1], label=type_map.get(i, "ERROR"))


            # Настройка внешнего вида графика
            plt.xlabel("День")
            plt.ylabel("Кол-во обращений")
            plt.legend(fontsize='xx-small')
            # Задаем метки делений на оси x
            start_value = 0
            end_value = len(output[1])
            plt.title(f"Статистика за {end_value} последних дней")
            step = 1

            numbers = list(range(start_value, end_value, step))
            dates = [str(output[1][-1] - timedelta(days=(end_value - 1) - i)).removesuffix(" 00:00:00").removeprefix("20")
                     for i in range(start_value, end_value, step)]

            plt.xticks(numbers, dates)
            # Создание объекта для сохранения изображения в памяти
            buffer = io.BytesIO()
            # Сохранение графика в буфер
            plt.savefig(buffer, format='png')
            buffer.seek(0)

            # Отправка изображения через Telegram Bot API
            await bot.send_photo(chat_id=message.chat.id, photo=buffer)
    except:
        await bot.send_message(message.chat.id, "При получении статистики за 7 дней возникла странная ошибка...")


@bot.message_handler(func=lambda message: True)
async def echo_message(message):
    global SERVER_ADDRESS

    try:
        start_time = time.time()

        link = await tools.pars_link(link=message.text)
        if link is bool:
            await bot.reply_to(message, "Ты мне какую-то не правильную ссылку скинул! 🧐")
            return

        if link.isdigit():
            link = int(link)
            if link <= 0:
                await bot.reply_to(message, "Я даже без проверки знаю, что такого мода нету :)")
            else:
                try:
                    async with aiohttp.ClientSession() as session:
                        response = await session.get(url=SERVER_ADDRESS + f"/info/mod/{str(link)}", timeout=10)
                        data = await response.text()

                        # Если больше 30 мб (получаю от сервера в байтах, а значит и сравниваю в них)
                        info = json.loads(data)
                        if info["result"] is not None and info["result"].get("size", 0) > 31457280:
                            markup = telebot.types.InlineKeyboardMarkup()
                            markup.add(telebot.types.InlineKeyboardButton(text='Скачать',
                                                                          url=SERVER_ADDRESS+f'/download/{link}'))
                            await bot.send_message(message.chat.id,
                                                   f"Ого! `{info['result'].get('name', str(link))}` весит {round(info['result'].get('size', 1)/1048576, 1)} мегабайт!\nСкачай его по прямой ссылке 😃",
                                                   parse_mode="Markdown", reply_markup=markup)
                            return
                except:
                    await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=2)_",
                                       parse_mode="Markdown")
                    return -1

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url=SERVER_ADDRESS + f"/download/steam/{str(link)}",
                                               timeout=20) as response:
                            if response.headers.get('content-type') == "application/zip":
                                file_content = await response.read()
                                file_name = await tools.get_name(
                                    response.headers.get("content-disposition", "ERROR.zip"))
                                print(f"File name: {file_name}")
                                file = io.BytesIO(file_content)

                                await bot.send_document(
                                    message.chat.id,
                                    visible_file_name=await tools.get_name(file_name),
                                    document=file,
                                    reply_to_message_id=message.id,
                                    timeout=10)
                                await bot.reply_to(message,
                                                   f"Ваш запрос занял {await tools.format_seconds(round(time.time() - start_time, 1))}")
                                return
                            else:
                                result = await response.read()
                                header_result = response.headers
                except:
                    print("ERROR")
                    await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=3)_", parse_mode="Markdown")
                    return -1

                if header_result.get('content-type') == "application/json":
                    data = json.loads(result.decode())
                    if data["error_id"] == 0 or data["error_id"] == 3:
                        await bot.reply_to(message,
                            "На сервере нету этого мода, но он сейчас его загрузит! _(это может занять некоторое время)_",
                            parse_mode="Markdown")

                        for i in range(60):
                            await asyncio.sleep(1)
                            try:
                                async with aiohttp.ClientSession() as session:
                                    response = await session.get(
                                        url=SERVER_ADDRESS + f"/condition/mod/%5B{str(link)}%5D",
                                        timeout=10)
                                    res = await response.read()
                                    header_result = response.headers
                            except:
                                await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=5)_",
                                                   parse_mode="Markdown")
                                return -1
                            if header_result.get('content-type') == "application/json":
                                data = json.loads(res.decode())
                                if data.get(str(link), None) == None:
                                    markup = telebot.types.InlineKeyboardMarkup()
                                    markup.add(telebot.types.InlineKeyboardButton(text='Список поддерживаемых игр 👀',
                                                                                  url='https://steamdb.info/sub/17906/apps/'))
                                    await bot.reply_to(message, "Серверу не удалось загрузить этот мод 😢", reply_markup=markup)
                                    return -1
                                elif data[str(link)] <= 1:
                                    try:
                                        async with aiohttp.ClientSession() as session:
                                            response = await session.get(url=SERVER_ADDRESS + f"/info/mod/{str(link)}",
                                                                         timeout=10)
                                            data = await response.text()

                                            # Если больше 30 мб (получаю от сервера в байтах, а значит и сравниваю в них)
                                            info = json.loads(data)
                                            if info["result"] is not None and info["result"].get("size", 0) > 31457280:
                                                markup = telebot.types.InlineKeyboardMarkup()
                                                markup.add(telebot.types.InlineKeyboardButton(text='Скачать',
                                                                                              url=SERVER_ADDRESS+f'/download/{link}'))
                                                await bot.send_message(message.chat.id,
                                                                       f"Ого! `{info['result'].get('name', str(link))}` весит {round(info['result'].get('size', 1)/1048576, 1)} мегабайт!\nСкачай его по прямой ссылке 😃",
                                                                       parse_mode="Markdown", reply_markup=markup)
                                                return
                                    except:
                                        await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=4)_",
                                                           parse_mode="Markdown")
                                        return -1

                                    try:
                                        async with aiohttp.ClientSession() as session:
                                            async with session.get(url=SERVER_ADDRESS + f"/download/{str(link)}",
                                                                   timeout=20) as response:
                                                if response.headers.get('content-type') == "application/zip":
                                                    file_content = await response.read()
                                                    file_name = await tools.get_name(
                                                        response.headers.get("content-disposition", "ERROR.zip"))
                                                    print(f"File name: {file_name}")
                                                    file = io.BytesIO(file_content)

                                                    await bot.send_document(
                                                        message.chat.id,
                                                        visible_file_name=await tools.get_name(file_name),
                                                        document=file,
                                                        reply_to_message_id=message.id,
                                                        timeout=10)
                                                    await bot.reply_to(message,
                                                                       f"Ваш запрос занял {await tools.format_seconds(round(time.time() - start_time, 1))}")
                                                    return
                                                else:
                                                    markup = telebot.types.InlineKeyboardMarkup()
                                                    markup.add(telebot.types.InlineKeyboardButton(text='Список поддерживаемых игр 👀',
                                                                                                  url='https://steamdb.info/sub/17906/apps/'))
                                                    await bot.reply_to(message, "Серверу не удалось загрузить этот мод 😢", reply_markup=markup)
                                    except:
                                        await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=1)_",
                                                           parse_mode="Markdown")

                                    return
                            else:
                                await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=1)_",
                                                   parse_mode="Markdown")
                                return
                        await bot.reply_to(message, "Превышено время ожидания ответа с сервера!")
                        return -1

                    elif data["error_id"] == 1:
                        await bot.reply_to(message,
                            "Сервер запускается и не может сейчас грузить моды! Повтори попытку через пару минут :)")
                    elif data["error_id"] == 2:
                        await bot.reply_to(message, "Сервер говорит что такого мода не существует 😢")
                    else:
                        await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=2)_", parse_mode="Markdown")
                else:
                    await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=3)_", parse_mode="Markdown")
        else:
            if link is str and (
                    link.startswith("https://steamcommunity.com") or link.startswith("https://store.steampowered.com")):
                await bot.reply_to(message, "Мне нужна ссылка конкретно на мод! _(или его ID)_", parse_mode="Markdown")
            elif link is str and (link.startswith("https://") or link.startswith("http://")):
                await bot.reply_to(message, "Пока что я умею скачивать только со Steam 😿")
            else:
                await bot.reply_to(message, "Если ты хочешь скачать мод, то просто скинь ссылку или `ID` мода в чат!", parse_mode="Markdown")
    except:
        await bot.reply_to(message, "Ты вызвал странную ошибку...\nПопробуй загрузить мод еще раз!")


asyncio.run(bot.polling())