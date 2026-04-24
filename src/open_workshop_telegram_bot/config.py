from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "api_address": "https://api.openworkshop.su",
        "website_address": "https://openworkshop.su",
        "docs_path": "/docs",
    },
    "telegram": {
        "commands": {
            "help": ["help", "start", "старт", "помощь"],
            "project": ["project", "проект"],
            "statistics": ["statistics", "статистика"],
            "graph": ["graph", "график"],
        },
        "project_buttons": [
            {
                "text": "GitHub проекта",
                "url": "https://github.com/Open-Workshop",
            },
            {
                "text": "Telegram канал автора",
                "url": "https://t.me/sphere_games",
            },
            {
                "text": "Такой же бот в Discord",
                "url": "https://discord.com/api/oauth2/authorize?client_id=1137841106852253818&permissions=2148038720&scope=bot%20applications.commands",
            },
            {
                "text": "API бота",
                "url": "{server}{docs_path}",
            },
            {
                "text": "Сайт",
                "url": "{website}",
            },
        ],
        "welcome_messages": [
            {
                "text": "Этот бот позволяет скачивать моды с Open Workshop и ассоцированные моды со *Steam* через чат *Telegram!* 💨",
                "parse_mode": "Markdown",
            },
            {
                "text": "Чтобы получить `ZIP` архив отправьте ссылку на мод или `ID` мода в *Open Workshop* или *Steam* и бот в ответ даст `ZIP` архив 🤝",
                "parse_mode": "Markdown",
            },
        ],
        "project_message": {
            "text": "Это бесплатный **open-source** проект с **открытым API**! 😍",
            "parse_mode": "Markdown",
        },
    },
    "statistics": {
        "db_path": "bot_statistics.sqlite3",
        "history_days": 14,
        "figure_size": [12, 6],
        "marker": "o",
        "line_width": 2,
        "legend_fontsize": "xx-small",
        "date_format": "%d.%m",
        "title": "Локальная статистика бота в SQLite.",
        "empty_text": "Пока локальная статистика пустая.",
        "period_template": "Период данных: {first_day} - {last_day}.",
        "summary_template": (
            "Всего обращений: {incoming}.\n"
            "Попыток скачать моды: {download_attempt}.\n"
            "Успешных выдач: {download_success}.\n"
            "Неудачных попыток: {download_fail}.\n"
            "Неподходящих сообщений: {invalid_input}.\n\n"
            "Команды: /help и /start - {help_command}, /project - {project_command}, /statistics - {statistics_command}, /graph - {graph_command}.\n"
            "Сегодня: {today_incoming} обращений, {today_download_attempt} попыток скачивания, {today_download_success} успешных выдач, {today_download_fail} неудач.\n"
            "{period_text}"
        ),
        "graph_title_template": "Локальная статистика за последние {days} дней",
        "xlabel": "День",
        "ylabel": "Количество",
        "series_labels": {
            "incoming": "Все обращения",
            "download_attempt": "Попытки скачивания",
            "download_success": "Успешные выдачи",
            "download_fail": "Неудачные попытки",
            "invalid_input": "Неподходящие сообщения",
        },
    },
    "download": {
        "large_file_threshold_bytes": 31457280,
        "info_timeout_seconds": 10,
        "download_timeout_seconds": 20,
        "telegram_timeout_seconds": 10,
        "messages": {
            "large_file_intro": "Ого! `{name}` весит {size_mb} мегабайт!\nСкачай его по прямой ссылке 😃",
            "large_file_buttons": [
                {
                    "text": "Скачать",
                    "url": "{server}/download/{mod_id}",
                },
                {
                    "text": "Мод на сайте",
                    "url": "{website}/mod/{mod_id}",
                },
            ],
            "archive_buttons": [
                {
                    "text": "Мод на сайте",
                    "url": "{website}/mod/{mod_id}",
                }
            ],
            "send_direct_link_fail": "Не удалось отправить ссылку на прямое скачивание 😔",
            "server_timeout_info": "Похоже, что сервер не отвечает 😔 _(point=2)_",
            "server_timeout_download": "Похоже, что сервер не отвечает 😔 _(point=3)_",
            "send_archive_fail": "Не удалось отправить архив через Telegram 😔",
            "no_mod_json": "На сервере нету этого мода :(",
            "unknown_mod_json": "Сервер говорит что такого мода не существует 😢",
            "unexpected_json": "Сервер прислал неожиданный ответ 😧 _(point=2)_",
            "unexpected_download": "Сервер прислал неожиданный ответ 😧 _(point=3)_",
            "request_duration": "Ваш запрос занял {duration}",
            "server_unavailable": "Похоже, что сервер не отвечает 😔",
        },
    },
    "responses": {
        "invalid_link": "Ты мне какую-то не правильную ссылку скинул! 🧐",
        "invalid_id": "Я даже без проверки знаю, что такого мода нету :)",
        "specific_mod_link": "Мне нужна ссылка конкретно на мод! _(или его ID)_",
        "generic_http_link": "Пока что я умею скачивать только c Open Workshop и ассоцированные моды со Steam 😿",
        "generic_prompt": "Если ты хочешь скачать мод, то просто скинь ссылку или `ID` мода в чат!",
        "unexpected_error": "Ты вызвал странную ошибку...\nПопробуй загрузить мод еще раз!",
    },
}


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        loaded_config = deepcopy(DEFAULT_CONFIG)
    else:
        with config_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)

        if not isinstance(loaded, dict):
            raise ValueError(f"Config file {config_path} must contain a JSON object.")

        loaded_config = _merge_dicts(DEFAULT_CONFIG, loaded)

    telegram = loaded_config.get("telegram")
    if isinstance(telegram, dict):
        commands = telegram.get("commands")
        if isinstance(commands, dict):
            telegram["commands"] = {
                command_name: _ensure_list(aliases)
                for command_name, aliases in commands.items()
            }

        for key in ("project_buttons", "welcome_messages"):
            telegram[key] = _ensure_list(telegram.get(key))

    download = loaded_config.get("download")
    if isinstance(download, dict):
        messages = download.get("messages")
        if isinstance(messages, dict):
            for key in ("large_file_buttons", "archive_buttons"):
                messages[key] = _ensure_list(messages.get(key))

    return loaded_config


def build_known_command_tokens(commands: dict[str, Any]) -> tuple[str, ...]:
    tokens: list[str] = []

    for aliases in commands.values():
        if isinstance(aliases, str):
            aliases = [aliases]

        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            if not isinstance(alias, str):
                continue

            token = alias.strip().split(maxsplit=1)[0]
            if not token:
                continue

            if not token.startswith("/"):
                token = f"/{token.lstrip('/')}"

            token = token.split("@", 1)[0]
            if token not in tokens:
                tokens.append(token)

    return tuple(tokens)
