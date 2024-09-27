#!/bin/bash

# Применение миграций базы данных
python manage.py migrate --noinput

# Запуск Django сервера
python manage.py runserver 0.0.0.0:8000 &

# Запуск Telegram бота
python bot.py &
