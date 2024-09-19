import json
import logging
import os

import django
from django.conf import settings
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Updater

# Настройка переменной окружения для Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FlowerShop.settings")
django.setup()  # Инициализация Django

# Теперь можно импортировать модели после инициализации Django
from tg_bot.models import Category, Order, Product, UserBot


def delivery_orders(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    logger.info("Открыто меню доставщика")

    delivery_person = UserBot.objects.filter(user_id=user_id, status="delivery").first()
    if not delivery_person:
        update.message.reply_text("У вас нет прав для просмотра заказов.")
        return

    orders = Order.objects.filter(
        delivery_person=delivery_person, status__in=["inDelivery"]
    )

    if not orders.exists():
        update.message.reply_text("У вас нет заказов для доставки.")
        return

    keyboard = []
    for order in orders:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Заказ {order.id} - {order.product}",
                    callback_data=f"order_delivery_{order.id}",
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Список ваших заказов:", reply_markup=reply_markup)


def handle_delivery_order(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Получаем ID заказа
    order_id = query.data.split("_")[2]
    order = Order.objects.get(id=int(order_id))

    # Доступные статусы для изменения доставщиком
    delivery_status_choices = [("inDelivery", "В пути"), ("delivered", "Доставлен")]

    # Создаем клавиатуру для изменения статуса заказа
    keyboard = [
        [
            InlineKeyboardButton(
                status[1], callback_data=f"setDeliveryStatus_{order.id}_{status[0]}"
            )
        ]
        for status in delivery_status_choices
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"👤 Имя: {order.user}\n"
        f"📅 Дата и время желаемой доставки: {order.desired_delivery_date}\n"
        f"💐 Букет: {order.product.name}\n"
        f"💰 Стоимость: {order.product.price} руб.\n"
        f"📞 Телефон: {order.user.phone}\n"
        f"🏠 Адрес доставки: {order.delivery_address}\n"
        f"Текущий статус {order.get_status_display()} \n"
        f"Выберите новый статус для заказа {order.id}:",
        reply_markup=reply_markup,
    )


def set_delivery_status(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Получаем ID заказа и новый статус
    _, order_id, new_status = query.data.split("_")
    order = Order.objects.get(id=int(order_id))

    # Изменяем статус заказа
    order.status = new_status
    order.save()

    query.edit_message_text(
        f"Статус заказа {order.id} успешно изменён на {dict(Order.STATUS_CHOICES).get(new_status)}"
    )


def manager_orders(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    logger.info("Открыто меню менеджера")

    if user_id in UserBot.objects.filter(status="manager"):
        update.message.reply_text("У вас нет прав для просмотра заказов.")
        return

    orders = Order.objects.filter(status__in=["created", "inWork", "inDelivery"])

    if not orders.exists():
        update.message.reply_text("Заказов пока нет.")
        return

    keyboard = []
    for order in orders:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Заказ {order.id} - {order.product}",
                    callback_data=f"order_admin_{order.id}",
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Список всех заказов:", reply_markup=reply_markup)


def handle_order_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = query.data.split("_")[2]
    order = Order.objects.get(id=int(order_id))

    order_details = (
        f"👤 Имя: {order.user}\n"
        f"📅 Дата и время желаемой доставки: {order.desired_delivery_date}\n"
        f"🕒 Время создания заказа: {order.creation_date}\n"
        f"💐 Букет: {order.product.name}\n"
        f"💰 Стоимость: {order.product.price} руб.\n"
        f"📞 Телефон: {order.user.phone}\n"
        f"🏠 Адрес доставки: {order.delivery_address}\n"
        f"Статус: {order.get_status_display()}\n"
        f"📦 Выбранный доставщик: {order.delivery_person}\n"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "Изменить статус заказа", callback_data=f"change_status_{order.id}"
            ),
            InlineKeyboardButton(
                "Назначить доставщика", callback_data=f"assign_delivery_{order.id}"
            ),
        ]
    ]
    replay_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(order_details, reply_markup=replay_markup)


def change_order_status(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = query.data.split("_")[2]
    order = Order.objects.get(id=int(order_id))

    status_choices = Order.STATUS_CHOICES
    keyboard = [
        [
            InlineKeyboardButton(
                status[1], callback_data=f"setStatus_{order.id}_{status[0]}"
            )
        ]
        for status in status_choices
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"Выберите новый статус для заказа {order.id}:", reply_markup=reply_markup
    )


def set_order_status(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    _, order_id, new_status = query.data.split("_")
    order = Order.objects.get(id=int(order_id))

    order.status = new_status
    order.save()

    query.edit_message_text(
        f"Статус заказа {order.id} успешно изменён на {dict(Order.STATUS_CHOICES).get(new_status)}"
    )


def assign_delivery(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = query.data.split("_")[2]
    order = Order.objects.get(id=int(order_id))

    delivery_people = UserBot.objects.filter(status="delivery")

    keyboard = [
        [
            InlineKeyboardButton(
                person.full_name,
                callback_data=f"setDelivery_{order.id}_{person.user_id}",
            )
        ]
        for person in delivery_people
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"Выберите нового доставщика для заказа {order.id}:", reply_markup=reply_markup
    )


# Обработка выбора нового доставщика
def set_delivery_person(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    _, order_id, delivery_person_id = query.data.split("_")
    order = Order.objects.get(id=int(order_id))
    delivery_person = UserBot.objects.get(user_id=delivery_person_id)

    order.delivery_person = delivery_person
    order.save()

    query.edit_message_text(
        f"Доставщик для заказа {order.id} успешно изменён на {delivery_person.full_name}"
    )


# Функция для загрузки данных из JSON
def load_json_data():
    logger.info(f"cчитывается menu.json")
    with open("menu.json", "r", encoding="utf-8") as file:
        return json.load(file)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Функция для создания кнопок с категориями из базы данных
def create_dynamic_buttons():
    categories = Category.objects.all()  # Получаем все категории из базы данных
    dynamic_buttons = [
        {"text": category.name, "callback": f"category_{category.id}"}
        for category in categories
    ]
    return dynamic_buttons


# Функция для объединения статических и динамических кнопок
def create_event_menu():
    json_data = load_json_data()  # Загружаем данные из JSON

    # Если в JSON указано поле "def", вызываем соответствующую функцию для подгрузки кнопок
    dynamic_buttons = []
    if "def" in json_data["event_menu"]:
        if json_data["event_menu"]["def"] == "create_event_menu":
            dynamic_buttons = create_dynamic_buttons()

    # Объединяем кнопки из JSON и динамические кнопки
    buttons = dynamic_buttons + json_data["event_menu"]["buttons"]

    # Создаем клавиатуру для Telegram
    keyboard_buttons = [
        [InlineKeyboardButton(button["text"], callback_data=button["callback"])]
        for button in buttons
    ]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    return json_data["event_menu"]["reply_text"], keyboard


# Хендлер для команды /start
def start(update: Update, context: CallbackContext):
    reply_text, keyboard = create_event_menu()  # Получаем текст и клавиатуру
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=reply_text, reply_markup=keyboard
    )


# Хендлер для обработки нажатий на кнопки
def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data.startswith("category_"):
        category_id = query.data.split("_")[1]
        category = Category.objects.get(id=int(category_id))
        products = Product.objects.filter(categories=category)

        if not products.exists():
            query.edit_message_text("В этой категории нет товаров.")
            return

        context.user_data["products"] = list(products)
        context.user_data["current_product"] = 0
        show_product(update, context)

    elif query.data == "next_product":
        next_product(update, context)

    elif query.data == "prev_product":
        prev_product(update, context)

    elif query.data == "menu_products":
        reply_text, keyboard = create_event_menu()
        query.edit_message_text(text=reply_text, reply_markup=keyboard)


def show_product(update: Update, context: CallbackContext):
    products = context.user_data["products"]
    current_index = context.user_data["current_product"]

    if products and 0 <= current_index < len(products):
        product = products[current_index]

        photo_path = os.path.join(settings.MEDIA_ROOT, product.image.name)

        # Отправляем фото и описание
        with open(photo_path, "rb") as photo:
            update.callback_query.message.reply_photo(
                photo=photo,
                caption=(
                    f"*Описание:* {product.description}\n"
                    f"*Стоимость:* {product.price} руб.\n\n"
                    f"*Хотите что-то еще более уникальное? Подберите другой букет из нашей коллекции или закажите консультацию флориста*"
                ),
                parse_mode="Markdown",
            )
    print(products)
    current_index = context.user_data["current_product"]
    print(current_index)
    product = products[current_index]
    print(product)
    photo_path = os.path.join(settings.MEDIA_ROOT, product.image.name)

    if not os.path.exists(photo_path):
        logger.error(f"Image not found: {photo_path}")
        update.callback_query.edit_message_text(text="Изображение товара не найдено.")
        return

    keyboard = [
        [InlineKeyboardButton("✔ Заказать ", callback_data=f"product_{product.id}")],
        [
            InlineKeyboardButton("◀ Предыдущий", callback_data="prev_product"),
            InlineKeyboardButton("Следующий ▶", callback_data="next_product"),
        ],
        [InlineKeyboardButton("Назад в меню", callback_data="menu_products")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query.message.photo:
        with open(photo_path, "rb") as photo:
            media = InputMediaPhoto(
                photo,
                caption=f"🍰 ***{product.name}***\n\n{product.description}\n\n"
                f"Цена: ***{product.price} руб.***",
                parse_mode="Markdown",
            )
            update.callback_query.message.edit_media(
                media=media, reply_markup=reply_markup
            )


def next_product(update: Update, context: CallbackContext):
    products = context.user_data["products"]
    context.user_data["current_product"] = (
        context.user_data["current_product"] + 1
    ) % len(products)
    show_product(update, context)


def prev_product(update: Update, context: CallbackContext):
    products = context.user_data["products"]
    context.user_data["current_product"] = (
        context.user_data["current_product"] - 1
    ) % len(products)
    show_product(update, context)


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
        CallbackQueryHandler(change_order_status, pattern="^change_status_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(set_order_status, pattern="^setStatus_")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(assign_delivery, pattern="^assign_delivery_")
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
    dispatcher.add_handler(CallbackQueryHandler(handle_button_click))
    dispatcher.add_handler(CallbackQueryHandler(next_product, pattern="^next_product$"))
    dispatcher.add_handler(CallbackQueryHandler(prev_product, pattern="^prev_product$"))

    updater.start_polling()
    updater.idle()
