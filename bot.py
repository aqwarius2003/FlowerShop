import logging
import os

import django
from django.conf import settings
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from bot_admin import (
    add_comment,
    assign_delivery,
    change_order_status,
    delivery_orders,
    go_back_to_delivery_orders,
    go_back_to_manager_orders,
    handle_comment_input,
    handle_delivery_order,
    handle_order_selection,
    manager_orders,
    set_delivery_person,
    set_delivery_status,
    set_order_status,
)

# Настройка переменной окружения для Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FlowerShop.settings")
django.setup()  # Инициализация Django

# Теперь можно импортировать модели после инициализации Django
from tg_bot import admin
from tg_bot.models import Category, Order, Product, UserBot


# Функция для загрузки данных из JSON


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Функция для создания кнопок с категориями из базы данных

# Хендлер для команды /start
def start(update: Update, context: CallbackContext):
    # reply_text, keyboard = create_event_menu()  # Получаем текст и клавиатуру

    context.bot.send_message(
        chat_id=update.effective_chat.id, text=reply_text, reply_markup=keyboard
    )


# Основной код для запуска бота
if __name__ == "__main__":
    env = Env()
    env.read_env()

    # tg_chat_id_meneger = int(os.environ["TG_CHAT_ID"])
    tg_bot_token = os.environ["TG_BOT_TOKEN"]
    # bot = telegram.Bot(token=tg_bot_token)

    updater = Updater(token=tg_bot_token)

    # Хендлеры
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("manager", manager_orders))
    dispatcher.add_handler(CommandHandler("delivery", delivery_orders))
    dispatcher.add_handler(
        CallbackQueryHandler(handle_order_selection, pattern="^order_admin_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(
            go_back_to_manager_orders, pattern="^back_to_manager_orders$"
        )
    )
    dispatcher.add_handler(
        CallbackQueryHandler(
            go_back_to_delivery_orders, pattern="^back_to_delivery_orders$"
        )
    )
    dispatcher.add_handler(
        CallbackQueryHandler(change_order_status, pattern="^change_status_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(set_order_status, pattern="^setStatus_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(assign_delivery, pattern="^assign_delivery_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(add_comment, pattern="^comment_delivery_")
    )
    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_comment_input)
    )
    dispatcher.add_handler(
        CallbackQueryHandler(set_delivery_person, pattern="^setDelivery_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(handle_delivery_order, pattern="^order_delivery_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(set_delivery_status, pattern="^setDeliveryStatus_")
    )
    dispatcher.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()
