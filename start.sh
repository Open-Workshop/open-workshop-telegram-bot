#!/bin/bash

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

if [ -z "${BOT_TOKEN:-}" ] && [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "Set BOT_TOKEN in the environment or .env before starting the bot."
    exit 1
fi

while true; do
    PYTHONPATH=src screen -S open-workshop-telegram-bot-executor python3 -m open_workshop_telegram_bot
    sleep 60
done
