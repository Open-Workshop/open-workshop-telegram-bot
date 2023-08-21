import io
import json
import time
import tools
import telebot
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


type_map = None

#TODO разделить команду на 2 части (общая статистика, графики)
#TODO сделать асинхронным
@bot.message_handler(commands=['statistics', 'статистика'])
async def statistics(message):
    plt.clf()
    global type_map

    try:
        if not type_map:
            res = requests.get(url=SERVER_ADDRESS+"/statistics/info/type_map", headers={"Accept-Language": "ru, en"}, timeout=10)
            info = json.loads(res.content)
            type_map = info["result"]
    except:
        await bot.send_message(message.chat.id, "При получении переводов возникла странная ошибка...")

    try:
        # Произвольные данные
        res = requests.get(url=SERVER_ADDRESS+"/statistics/hour", timeout=10)
        info = json.loads(res.content)

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
        plt.clf()
        # Произвольные данные
        res = requests.get(url=SERVER_ADDRESS+"/statistics/day", timeout=10)
        info = json.loads(res.content)

        output = await tools.graf(info, "date")

        shift = output[1][0].toordinal()
        for i in output[0].keys():
            plt.plot([x - shift for x in output[0][i][0]], output[0][i][1], label=type_map.get(i, "ERROR"))


        # Настройка внешнего вида графика
        plt.title("Статистика за 7 дней")
        plt.xlabel("День")
        plt.ylabel("Кол-во обращений")
        plt.legend(fontsize='xx-small')
        # Задаем метки делений на оси x
        start_value = 0
        end_value = len(output[1])-1
        step = 1

        numbers = list(range(start_value, end_value + 1, step))
        dates = [str(output[1][-1] - timedelta(days=end_value- i)).removesuffix(" 00:00:00").removeprefix("20") for i in range(start_value, end_value + 1, step)]

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

    try:
        res = requests.get(url=SERVER_ADDRESS+"/statistics/info/all", timeout=10)
        info = json.loads(res.content)
        await bot.send_message(message.chat.id, f"""
Пользователям отправлено {info.get('mods_sent_count')} файлов.
Сервис работает {await tools.format_seconds(seconds=info.get('statistics_days', 0), word="день")}.

У {info.get('games', 0)} игр сохранено {info.get('mods', 0)} модов, {info.get('mods_dependencies', 0)} из которых имеют зависимости на другие моды.
Сервису известно об {await tools.format_seconds(seconds=info.get('genres', 0), word="жанр")} игр и {await tools.format_seconds(seconds=info.get('mods_tags', 0), word="тег")} для модов.
        """)
    except:
        await bot.send_message(message.chat.id, "При получении общей статистики возникла странная ошибка...")


#TODO сделать асинхронным
@bot.message_handler(func=lambda message: True)
async def echo_message(message):
    try:
        start_time = time.time()
        mes = message.text

        if mes.startswith("https://steamcommunity.com/sharedfiles/filedetails/") or mes.startswith("https://steamcommunity.com/workshop/filedetails/"):
            parsed = urlparse(mes, "highlight=params#url-parsing")
            captured_value = parse_qs(parsed.query)
            try:
                mes = captured_value['id'][0]
            except:
                await bot.reply_to(message, "Ты мне какую-то не правильную ссылку скинул! 🧐")

        if mes.isdigit():
            mes = int(mes)
            if mes <= 0:
                await bot.reply_to(message, "Я даже без проверки знаю, что такого мода нету :)")
            else:
                try:
                    data = requests.get(url=SERVER_ADDRESS+f"/info/mod/{str(mes)}",
                                        timeout=10)

                    # Если больше 30 мб (получаю от сервера в байтах, а значит и сравниваю в них)
                    info = json.loads(data.content)
                    if info["result"] is not None and info["result"].get("size", 0) > 31457280:
                        markup = telebot.types.InlineKeyboardMarkup()
                        markup.add(telebot.types.InlineKeyboardButton(text='Скачать',
                                                                      url=SERVER_ADDRESS+f'/download/{mes}'))
                        await bot.send_message(message.chat.id,
                                               f"Ого! `{info['result'].get('name', str(mes))}` весит {round(info['result'].get('size', 1)/1048576, 1)} мегабайт!\nСкачай его по прямой ссылке 😃",
                                               parse_mode="Markdown", reply_markup=markup)
                        return
                except:
                    await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=4)_", parse_mode="Markdown")
                    return -1

                try:
                    result = requests.get(url=SERVER_ADDRESS+f"/download/steam/{str(mes)}", timeout=5)
                except:
                    await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=1)_", parse_mode="Markdown")
                    return -1

                if result.headers.get('content-type') == "application/zip":
                    await bot.send_document(
                        message.chat.id,
                        visible_file_name=await tools.get_name(result.headers["content-disposition"]),
                        document=result.content,
                        reply_to_message_id=message.id,
                        timeout=10)
                    await bot.reply_to(message, f"Ваш запрос занял {await tools.format_seconds(round(time.time()-start_time, 1))}")
                elif result.headers.get('content-type') == "application/json":
                    data = json.loads(result.content)
                    if data["error_id"] == 0 or data["error_id"] == 3:
                        await bot.reply_to(message, "На сервере нету этого мода, но он сейчас его загрузит! _(это может занять некоторое время)_", parse_mode="Markdown")

                        for i in range(60):
                            time.sleep(1)
                            try:
                                res = requests.get(url=SERVER_ADDRESS+f"/condition/mod/%5B{str(mes)}%5D",
                                                        timeout=10)
                            except:
                                await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=2)_", parse_mode="Markdown")
                                return -1
                            if res.headers.get('content-type') == "application/json":
                                data = json.loads(res.content)
                                if data.get(str(mes), None) == None:
                                    await bot.reply_to(message, "Серверу не удалось загрузить этот мод 😢")
                                    return -1
                                elif data[str(mes)] <= 1:
                                    try:
                                        data = requests.get(url=SERVER_ADDRESS+f"/info/mod/{str(mes)}",
                                                            timeout=10)

                                        # Если больше 30 мб (получаю от сервера в байтах, а значит и сравниваю в них)
                                        info = json.loads(data.content)
                                        if info["result"] is not None and info["result"].get("size", 0) > 31457280:
                                            markup = telebot.types.InlineKeyboardMarkup()
                                            markup.add(telebot.types.InlineKeyboardButton(text='Скачать',
                                                                                          url=SERVER_ADDRESS+f'/download/{mes}'))
                                            await bot.send_message(message.chat.id,
                                                                   f"Ого! `{info['result'].get('name', str(mes))}` весит {round(info['result'].get('size', 1)/1048576, 1)} мегабайт!\nСкачай его по прямой ссылке 😃",
                                                                   parse_mode="Markdown", reply_markup=markup)
                                            return
                                    except:
                                        await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=4)_",
                                                           parse_mode="Markdown")
                                        return -1

                                    try:
                                        result = requests.get(
                                            url=SERVER_ADDRESS+f"/download/{str(mes)}", timeout=10)
                                    except:
                                        await bot.reply_to(message, "Похоже, что сервер не отвечает 😔 _(point=3)_", parse_mode="Markdown")
                                        return -1

                                    if result.headers.get('content-type') == "application/zip":
                                        await bot.send_document(
                                            message.chat.id,
                                            visible_file_name=await tools.get_name(result.headers["content-disposition"]),
                                            document=result.content,
                                            reply_to_message_id=message.id,
                                            timeout=10)
                                        await bot.reply_to(message, f"Ваш запрос занял {await tools.format_seconds(round(time.time()-start_time, 1))}")
                                    else:
                                        await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=4)_",
                                                           parse_mode="Markdown")

                                    return
                            else:
                                await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=1)_", parse_mode="Markdown")
                                return
                        await bot.reply_to(message, "Превышено время ожидания ответа с сервера!")
                        return -1

                    elif data["error_id"] == 1:
                        await bot.reply_to(message,
                            "Сервер запускается и не может сейчас грузить моды! Повтори попытку через пару минут :)")
                    elif data["error_id"] == 2:
                        await bot.reply_to(message, "Сервер говорит что такого мода не существует 😢")
                    else:
                        await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=2)_",
                                           parse_mode="Markdown")
                else:
                    await bot.reply_to(message, "Сервер прислал неожиданный ответ 😧 _(point=3)_", parse_mode="Markdown")
        else:
            if mes.startswith("https://steamcommunity.com") or mes.startswith("https://store.steampowered.com"):
                await bot.reply_to(message, "Мне нужна ссылка конкретно на мод! _(или его ID)_", parse_mode="Markdown")
            elif mes.startswith("https://") or mes.startswith("http://"):
                await bot.reply_to(message, "Пока что я умею скачивать только со Steam 😿")
            else:
                await bot.reply_to(message, "Если ты хочешь скачать мод, то просто скинь ссылку или `ID` мода в чат!",
                                   parse_mode="Markdown")
    except:
        await bot.reply_to(message, "Ты вызвал странную ошибку...\nПопробуй загрузить мод еще раз!",
                           parse_mode="Markdown")

import asyncio
asyncio.run(bot.polling())