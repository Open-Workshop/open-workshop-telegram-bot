from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any

import aiohttp
import matplotlib.pyplot as plt
import telebot
from telebot.async_telebot import AsyncTeleBot

from .config import build_known_command_tokens, load_config
from . import stats as bot_stats
from .utils import extract_filename, format_seconds, is_open_workshop_url, parse_link

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOKEN_ENV_NAMES = ("BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
logger = logging.getLogger(__name__)


def load_api_token() -> str:
    for env_name in TOKEN_ENV_NAMES:
        token = os.getenv(env_name)
        if isinstance(token, str) and token.strip():
            return token.strip()

    env_names = ", ".join(TOKEN_ENV_NAMES)
    raise RuntimeError(f"Bot token is not configured. Set one of: {env_names}.")


def render_template(template: Any, **values: Any) -> str:
    if not isinstance(template, str):
        return str(template)

    try:
        return template.format(**values)
    except Exception:
        return template


def format_message_payload(payload: Any, **values: Any) -> tuple[str, str | None]:
    if isinstance(payload, dict):
        text = render_template(payload.get("text", ""), **values)
        parse_mode = payload.get("parse_mode")
        return text, parse_mode if isinstance(parse_mode, str) else None

    return render_template(payload, **values), None


def build_inline_markup(buttons: list[dict[str, Any]], **values: Any):
    markup = telebot.types.InlineKeyboardMarkup()
    has_buttons = False

    for button in buttons:
        if not isinstance(button, dict):
            continue

        text = render_template(button.get("text", ""), **values)
        url = render_template(button.get("url", ""), **values)
        if text and url:
            markup.add(telebot.types.InlineKeyboardButton(text=text, url=url))
            has_buttons = True

    return markup if has_buttons else None


def normalize_content_type(content_type: str | None) -> str:
    if not isinstance(content_type, str):
        return ""

    return content_type.split(";", 1)[0].strip().lower()


def extract_upstream_error(body: str | bytes, content_type: str | None) -> str:
    if isinstance(body, bytes):
        text = body.decode("utf-8", errors="replace")
    else:
        text = body

    cleaned_text = text.strip()
    if not cleaned_text:
        return "Пустой ответ от сервера."

    normalized_content_type = normalize_content_type(content_type)
    parsed_json: Any = None

    if "json" in normalized_content_type or cleaned_text.startswith("{") or cleaned_text.startswith("["):
        try:
            parsed_json = json.loads(cleaned_text)
        except Exception:
            parsed_json = None

    if isinstance(parsed_json, dict):
        parts: list[str] = []
        for key in ("title", "detail", "message", "error", "description"):
            value = parsed_json.get(key)
            if isinstance(value, str):
                normalized_value = value.strip()
                if normalized_value and normalized_value not in parts:
                    parts.append(normalized_value)

        code = parsed_json.get("code")
        if isinstance(code, str):
            normalized_code = code.strip()
            if normalized_code:
                parts.append(f"code: {normalized_code}")

        status = parsed_json.get("status")
        if isinstance(status, (int, float)) and status and f"status: {int(status)}" not in parts:
            parts.append(f"status: {int(status)}")

        if parts:
            result = "\n".join(parts)
            return result[:3500] + ("..." if len(result) > 3500 else "")

        result = json.dumps(parsed_json, ensure_ascii=False, indent=2)
        return result[:3500] + ("..." if len(result) > 3500 else "")

    return cleaned_text[:3500] + ("..." if len(cleaned_text) > 3500 else "")


def log_upstream_response(stage: str, response: aiohttp.ClientResponse, body: str | bytes) -> None:
    if isinstance(body, bytes):
        preview = body.decode("utf-8", errors="replace")
    else:
        preview = body

    normalized_preview = " ".join(preview.split())
    if len(normalized_preview) > 500:
        normalized_preview = f"{normalized_preview[:497]}..."

    logger.warning(
        "%s: status=%s url=%s content_type=%s body=%s",
        stage,
        response.status,
        response.url,
        response.headers.get("content-type", ""),
        normalized_preview,
    )


async def reply_with_upstream_error(
    message,
    reply_callback,
    *,
    response: aiohttp.ClientResponse,
    body: str | bytes,
    stage: str,
    reply_text: str,
    parse_mode: str | None = None,
) -> None:
    log_upstream_response(stage, response, body)
    error_text = extract_upstream_error(body, response.headers.get("content-type"))
    await reply_callback(message, reply_text.format(error=error_text), parse_mode=parse_mode)


async def run() -> None:
    config = load_config()
    bot_stats.configure(config["statistics"]["db_path"], base_dir=PROJECT_ROOT)
    bot_stats.init_db()

    api_token = load_api_token()
    bot = AsyncTeleBot(api_token)
    register_handlers(bot, config)
    await bot.polling()


def main() -> None:
    asyncio.run(run())


def register_handlers(bot: AsyncTeleBot, config: dict[str, Any]) -> None:
    server_config = config["server"]
    telegram_config = config["telegram"]
    statistics_config = config["statistics"]
    download_config = config["download"]
    response_texts = config["responses"]

    server_address = server_config["api_address"].rstrip("/")
    website_address = server_config["website_address"].rstrip("/")
    docs_path = server_config["docs_path"]

    commands = telegram_config["commands"]
    known_command_tokens = build_known_command_tokens(commands)
    welcome_messages = telegram_config["welcome_messages"]
    project_message = telegram_config["project_message"]
    project_buttons = telegram_config["project_buttons"]

    history_days = max(1, int(statistics_config["history_days"]))
    figure_size = tuple(statistics_config["figure_size"])
    marker = statistics_config["marker"]
    line_width = statistics_config["line_width"]
    legend_fontsize = statistics_config["legend_fontsize"]
    date_format = statistics_config["date_format"]
    statistics_title = statistics_config["title"]
    empty_text = statistics_config["empty_text"]
    period_template = statistics_config["period_template"]
    summary_template = statistics_config["summary_template"]
    graph_title_template = statistics_config["graph_title_template"]
    xlabel = statistics_config["xlabel"]
    ylabel = statistics_config["ylabel"]
    series_labels = statistics_config["series_labels"]

    download_messages = download_config["messages"]
    large_file_threshold_bytes = int(download_config["large_file_threshold_bytes"])
    info_timeout_seconds = float(download_config["info_timeout_seconds"])
    download_timeout_seconds = float(download_config["download_timeout_seconds"])
    telegram_timeout_seconds = float(download_config["telegram_timeout_seconds"])
    large_file_buttons = download_messages["large_file_buttons"]
    archive_buttons = download_messages["archive_buttons"]

    async def safe_reply(message, text: str, **kwargs: Any) -> None:
        try:
            await bot.reply_to(message, text, **kwargs)
        except Exception:
            pass

    async def send_configured_messages(message, entries, **values: Any) -> None:
        for entry in entries:
            text, parse_mode = format_message_payload(entry, **values)
            await safe_reply(message, text, parse_mode=parse_mode)

    def response_text(key: str, **values: Any) -> str:
        return render_template(response_texts[key], **values)

    def download_text(key: str, **values: Any) -> str:
        return render_template(download_messages[key], **values)

    def format_day(value: Any) -> str:
        if not value:
            return "—"
        return date.fromisoformat(str(value)).strftime("%d.%m.%Y")

    @bot.message_handler(commands=commands["help"])
    async def send_welcome(message):
        bot_stats.record_counts(incoming=1, help_command=1)
        await send_configured_messages(
            message,
            welcome_messages,
            server=server_address,
            website=website_address,
            docs_path=docs_path,
        )

    @bot.message_handler(commands=commands["project"])
    async def project(message):
        bot_stats.record_counts(incoming=1, project_command=1)

        markup = build_inline_markup(
            project_buttons,
            server=server_address,
            website=website_address,
            docs_path=docs_path,
        )
        text, parse_mode = format_message_payload(
            project_message,
            server=server_address,
            website=website_address,
            docs_path=docs_path,
        )

        await bot.send_message(
            message.chat.id,
            text,
            parse_mode=parse_mode,
            reply_markup=markup,
        )

    @bot.message_handler(commands=commands["statistics"])
    async def statistics(message):
        bot_stats.record_counts(incoming=1, statistics_command=1)
        summary = bot_stats.get_totals()
        today = bot_stats.get_day()

        if summary["active_days"]:
            period_text = render_template(
                period_template,
                first_day=format_day(summary["first_day"]),
                last_day=format_day(summary["last_day"]),
            )
        else:
            period_text = empty_text

        summary_text = render_template(
            summary_template,
            **summary,
            today_incoming=today["incoming"],
            today_download_attempt=today["download_attempt"],
            today_download_success=today["download_success"],
            today_download_fail=today["download_fail"],
            period_text=period_text,
        )

        await bot.send_message(
            message.chat.id,
            f"{statistics_title}\n\n{summary_text}",
        )

    @bot.message_handler(commands=commands["graph"])
    async def graph(message):
        bot_stats.record_counts(incoming=1, graph_command=1)
        history = bot_stats.get_filled_history(days=history_days)

        if not any(row["incoming"] for row in history):
            await bot.send_message(message.chat.id, empty_text)
            return

        plt.clf()
        figure, axis = plt.subplots(figsize=figure_size)
        x_values = list(range(len(history)))
        labels = [date.fromisoformat(row["day"]).strftime(date_format) for row in history]

        axis.plot(x_values, [row["incoming"] for row in history], label=series_labels["incoming"], marker=marker, linewidth=line_width)
        axis.plot(x_values, [row["download_attempt"] for row in history], label=series_labels["download_attempt"], marker=marker, linewidth=line_width)
        axis.plot(x_values, [row["download_success"] for row in history], label=series_labels["download_success"], marker=marker, linewidth=line_width)
        axis.plot(x_values, [row["download_fail"] for row in history], label=series_labels["download_fail"], marker=marker, linewidth=line_width)
        axis.plot(x_values, [row["invalid_input"] for row in history], label=series_labels["invalid_input"], marker=marker, linewidth=line_width)

        axis.set_title(render_template(graph_title_template, days=history_days))
        axis.set_xlabel(xlabel)
        axis.set_ylabel(ylabel)
        axis.set_xticks(x_values)
        axis.set_xticklabels(labels, rotation=45, ha="right")
        axis.legend(fontsize=legend_fontsize)

        buffer = io.BytesIO()
        figure.tight_layout()
        figure.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        plt.close(figure)

        await bot.send_photo(chat_id=message.chat.id, photo=buffer)

    @bot.message_handler(func=lambda message: True)
    async def echo_message(message):
        download_attempt_started = False
        header_result = None
        result = None

        try:
            message_text = getattr(message, "text", None)
            if not message_text:
                bot_stats.record_counts(incoming=1, invalid_input=1)
                await safe_reply(message, response_text("generic_prompt"), parse_mode="Markdown")
                return

            command_token = message_text.split(maxsplit=1)[0].split("@", 1)[0]
            if command_token in known_command_tokens:
                return

            bot_stats.record_counts(incoming=1)
            start_time = time.time()

            link = parse_link(message_text, website_address)
            if link is False:
                bot_stats.record_counts(invalid_input=1)
                await safe_reply(message, response_text("invalid_link"))
                return

            if link.isdigit():
                mod_id = int(link)
                if mod_id <= 0:
                    bot_stats.record_counts(invalid_input=1)
                    await safe_reply(message, response_text("invalid_id"))
                    return

                bot_stats.record_counts(download_attempt=1)
                download_attempt_started = True

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url=f"{server_address}/mods/{mod_id}",
                            timeout=info_timeout_seconds,
                        ) as response:
                            data = await response.text()
                            if response.status != 200:
                                bot_stats.record_counts(download_fail=1)
                                await reply_with_upstream_error(
                                    message,
                                    safe_reply,
                                    response=response,
                                    body=data,
                                    stage=f"mods/{mod_id}",
                                    reply_text=download_text("unexpected_json"),
                                )
                                return -1

                            try:
                                info = json.loads(data)
                            except json.JSONDecodeError:
                                bot_stats.record_counts(download_fail=1)
                                await reply_with_upstream_error(
                                    message,
                                    safe_reply,
                                    response=response,
                                    body=data,
                                    stage=f"mods/{mod_id}",
                                    reply_text=download_text("unexpected_json"),
                                )
                                return -1

                            if not isinstance(info, dict):
                                bot_stats.record_counts(download_fail=1)
                                await reply_with_upstream_error(
                                    message,
                                    safe_reply,
                                    response=response,
                                    body=data,
                                    stage=f"mods/{mod_id}",
                                    reply_text=download_text("unexpected_json"),
                                )
                                return -1

                            result = info.get("result")
                            if isinstance(result, dict) and result.get("size", 0) > large_file_threshold_bytes:
                                markup = build_inline_markup(
                                    large_file_buttons,
                                    server=server_address,
                                    website=website_address,
                                    docs_path=docs_path,
                                    mod_id=mod_id,
                                )
                                try:
                                    await bot.send_message(
                                        message.chat.id,
                                        download_text(
                                            "large_file_intro",
                                            name=result.get("name", str(mod_id)),
                                            size_mb=round(result.get("size", 1) / 1048576, 1),
                                        ),
                                        parse_mode="Markdown",
                                        reply_markup=markup,
                                    )
                                except Exception:
                                    bot_stats.record_counts(download_fail=1)
                                    await safe_reply(message, download_text("send_direct_link_fail"))
                                    return

                                bot_stats.record_counts(download_success=1)
                                return

                            if "error_id" in info:
                                bot_stats.record_counts(download_fail=1)
                                if info["error_id"] in [0, 1, 3]:
                                    log_upstream_response(f"mods/{mod_id}", response, data)
                                    await safe_reply(message, download_text("no_mod_json"), parse_mode="Markdown")
                                elif info["error_id"] == 2:
                                    log_upstream_response(f"mods/{mod_id}", response, data)
                                    await safe_reply(message, download_text("unknown_mod_json"))
                                else:
                                    await reply_with_upstream_error(
                                        message,
                                        safe_reply,
                                        response=response,
                                        body=data,
                                        stage=f"mods/{mod_id}",
                                        reply_text=download_text("unexpected_json"),
                                    )
                                return

                            bot_stats.record_counts(download_fail=1)
                            await reply_with_upstream_error(
                                message,
                                safe_reply,
                                response=response,
                                body=data,
                                stage=f"mods/{mod_id}",
                                reply_text=download_text("unexpected_json"),
                            )
                            return
                except asyncio.TimeoutError:
                    logger.warning("Timeout while requesting mods/%s", mod_id)
                    bot_stats.record_counts(download_fail=1)
                    await safe_reply(message, download_text("server_timeout_info"), parse_mode="Markdown")
                    return -1
                except Exception:
                    logger.exception("Unexpected error while requesting mods/%s", mod_id)
                    bot_stats.record_counts(download_fail=1)
                    await safe_reply(message, download_text("server_unavailable"))
                    return -1

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url=f"{server_address}/mods/{mod_id}/download",
                            timeout=download_timeout_seconds,
                        ) as response:
                            content_type = normalize_content_type(response.headers.get("content-type"))
                            if content_type == "application/zip":
                                file_content = await response.read()
                                file_name = extract_filename(response.headers.get("content-disposition", "ERROR.zip"))
                                print(f"File name: {file_name}")
                                file = io.BytesIO(file_content)

                                try:
                                    await bot.send_document(
                                        message.chat.id,
                                        visible_file_name=extract_filename(file_name),
                                        document=file,
                                        reply_to_message_id=message.id,
                                        timeout=telegram_timeout_seconds,
                                    )
                                except Exception:
                                    bot_stats.record_counts(download_fail=1)
                                    await safe_reply(message, download_text("send_archive_fail"))
                                    return

                                bot_stats.record_counts(download_success=1)

                                markup = build_inline_markup(
                                    archive_buttons,
                                    server=server_address,
                                    website=website_address,
                                    docs_path=docs_path,
                                    mod_id=mod_id,
                                )
                                await safe_reply(
                                    message,
                                    download_text(
                                        "request_duration",
                                        duration=format_seconds(round(time.time() - start_time, 1)),
                                    ),
                                    reply_markup=markup,
                                )
                                return

                            result = await response.read()
                            header_result = response.headers
                            if response.status != 200:
                                bot_stats.record_counts(download_fail=1)
                                await reply_with_upstream_error(
                                    message,
                                    safe_reply,
                                    response=response,
                                    body=result,
                                    stage=f"mods/{mod_id}/download",
                                    reply_text=download_text("unexpected_download"),
                                )
                                return -1
                except asyncio.TimeoutError:
                    logger.warning("Timeout while requesting mods/%s/download", mod_id)
                    bot_stats.record_counts(download_fail=1)
                    await safe_reply(message, download_text("server_timeout_download"), parse_mode="Markdown")
                    return -1
                except Exception:
                    logger.exception("Unexpected error while requesting mods/%s/download", mod_id)
                    bot_stats.record_counts(download_fail=1)
                    await safe_reply(message, download_text("server_unavailable"))
                    return -1

                normalized_result_type = normalize_content_type(header_result.get("content-type") if header_result else None)
                if normalized_result_type in {"application/json", "application/problem+json"} or result.lstrip().startswith((b"{", b"[")):
                    try:
                        data = json.loads(result.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        bot_stats.record_counts(download_fail=1)
                        await reply_with_upstream_error(
                            message,
                            safe_reply,
                            response=response,
                            body=result,
                            stage=f"mods/{mod_id}/download",
                            reply_text=download_text("unexpected_download"),
                        )
                        return -1

                    if isinstance(data, dict) and data.get("error_id") in [0, 1, 3]:
                        bot_stats.record_counts(download_fail=1)
                        log_upstream_response(f"mods/{mod_id}/download", response, result)
                        await safe_reply(message, download_text("no_mod_json"), parse_mode="Markdown")
                        return

                    if isinstance(data, dict) and data.get("error_id") == 2:
                        bot_stats.record_counts(download_fail=1)
                        log_upstream_response(f"mods/{mod_id}/download", response, result)
                        await safe_reply(message, download_text("unknown_mod_json"))
                        return

                    if isinstance(data, dict) and "error_id" in data:
                        bot_stats.record_counts(download_fail=1)
                        await reply_with_upstream_error(
                            message,
                            safe_reply,
                            response=response,
                            body=result,
                            stage=f"mods/{mod_id}/download",
                            reply_text=download_text("unexpected_download"),
                        )
                        return -1

                bot_stats.record_counts(download_fail=1)
                await reply_with_upstream_error(
                    message,
                    safe_reply,
                    response=response,
                    body=result,
                    stage=f"mods/{mod_id}/download",
                    reply_text=download_text("unexpected_download"),
                )
                return -1
            else:
                bot_stats.record_counts(invalid_input=1)
                if isinstance(link, str) and (
                    link.startswith("https://steamcommunity.com")
                    or link.startswith("https://store.steampowered.com")
                    or is_open_workshop_url(message_text, website_address)
                ):
                    await safe_reply(message, response_text("specific_mod_link"), parse_mode="Markdown")
                elif isinstance(link, str) and (link.startswith("https://") or link.startswith("http://")):
                    await safe_reply(message, response_text("generic_http_link"))
                else:
                    await safe_reply(message, response_text("generic_prompt"), parse_mode="Markdown")
        except Exception:
            logger.exception("Unexpected error while handling incoming message")
            if download_attempt_started:
                bot_stats.record_counts(download_fail=1)
            await safe_reply(message, response_text("unexpected_error"))
