#!/bin/bash

while true; do
    screen -S open-workshop-telegram-bot-executor python3 main.py
    sleep 60
done