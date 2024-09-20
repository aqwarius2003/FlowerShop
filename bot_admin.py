import logging
import os

import django
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
)

# Настройка переменной окружения для Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FlowerShop.settings")
django.setup()  # Инициализация Django
# Теперь можно импортировать модели после инициализации Django
from tg_bot.models import Order, UserBot


def delivery_orders(update: Update, context: CallbackContext):
    if update.message:
        user_id = update.message.from_user.id
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        return  # TODO: Добавить проверка если id доставщика не найдено

    logger.info("Открыто меню доставщика")

    delivery_person = UserBot.objects.filter(user_id=user_id, status="delivery").first()
    if not delivery_person:
        if update.message:
            update.message.reply_text("У вас нет прав для просмотра заказов.")
        elif update.callback_query:
            update.callback_query.message.reply_text(
                "У вас нет прав для просмотра заказов."
            )
        return

    orders = Order.objects.filter(
        delivery_person=delivery_person, status__in=["inDelivery"]
    )

    if not orders.exists():
        if update.message:
            update.message.reply_text("У вас нет заказов для доставки.")
        elif update.callback_query:
            update.callback_query.message.reply_text("У вас нет заказов для доставки.")
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
    if update.message:
        update.message.reply_text("Список ваших заказов:", reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.reply_text(
            "Список ваших заказов:", reply_markup=reply_markup
        )


def handle_delivery_order(update: Update, context: CallbackContext):
    logger.info("Просмотр заказа")
    query = update.callback_query
    query.answer()

    order_id = query.data.split("_")[2]
    order = Order.objects.get(id=int(order_id))

    delivery_status_choices = [("inDelivery", "В пути"), ("delivered", "Доставлен")]

    keyboard = [
        [
            InlineKeyboardButton(
                status[1], callback_data=f"setDeliveryStatus_{order.id}_{status[0]}"
            )
        ]
        for status in delivery_status_choices
    ]

    keyboard.append(
        [InlineKeyboardButton("Назад", callback_data="back_to_delivery_orders")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"👤 Имя: {order.user}\n"
        f"📅 Дата и время желаемой доставки: {order.desired_delivery_date}\n"
        f"💐 Букет: {order.product.name}\n"
        f"💰 Стоимость: {order.product.price} руб.\n"
        f"📞 Телефон: {order.user.phone}\n"
        f"🏠 Адрес доставки: {order.delivery_address}\n"
        f"💬 Комментарий к заказу:{order.delivery_comments}\n"
        f"➡ Текущий статус: {order.get_status_display()} \n"
        f"✅ Выберите новый статус для заказа {order.id}:",
        reply_markup=reply_markup,
    )


def go_back_to_delivery_orders(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    delivery_orders(update, context)


def go_back_to_manager_orders(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    manager_orders(update, context)


def set_delivery_status(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    _, order_id, new_status = query.data.split("_")
    order = Order.objects.get(id=int(order_id))

    order.status = new_status
    order.save()

    query.edit_message_text(
        f"Статус заказа {order.id} успешно изменён на {dict(Order.STATUS_CHOICES).get(new_status)}"
    )


def manager_orders(update: Update, context: CallbackContext):
    if update.message:
        user_id = update.message.from_user.id
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        return

    logger.info("Открыто меню менеджера")
    manager_person = UserBot.objects.filter(user_id=user_id, status="manager").first()
    if not manager_person:
        if update.message:
            update.message.reply_text("У вас нет прав для просмотра заказов.")
        elif update.callback_query:
            update.callback_query.message.reply_text(
                "У вас нет прав для просмотра заказов."
            )
        return

    orders = Order.objects.filter(status__in=["created", "inWork", "inDelivery"])

    if not orders.exists():
        if update.message:
            update.message.reply_text("Заказов пока нет.")
        elif update.callback_query:
            update.callback_query.message.reply_text("Заказов пока нет.")
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
    if update.message:
        update.message.reply_text("Список всех заказов:", reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.reply_text(
            "Список всех заказов:", reply_markup=reply_markup
        )


def handle_order_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    logger.info(f"Callback data received: {query.data}")
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
        f"Комментарий для доставщика: {order.delivery_comments or 'Комментария нет'}\n"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "Изменить статус заказа", callback_data=f"change_status_{order.id}"
            ),
            InlineKeyboardButton(
                "Назначить доставщика", callback_data=f"assign_delivery_{order.id}"
            ),
            InlineKeyboardButton(
                "Комментарий доставщику", callback_data=f"comment_delivery_{order.id}"
            ),
        ],
        [InlineKeyboardButton("Назад", callback_data="back_to_manager_orders")],
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
            ),
        ]
        for status in status_choices
    ]
    keyboard.append(
        [InlineKeyboardButton("Назад", callback_data="back_to_manager_orders")]
    )
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
    keyboard.append(
        [InlineKeyboardButton("Назад", callback_data="back_to_manager_orders")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"Выберите нового доставщика для заказа {order.id}:", reply_markup=reply_markup
    )


def add_comment(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = query.data.split("_")[2]
    context.user_data["order_id_for_comment"] = order_id

    query.message.reply_text("Введите ваш комментарий для доставщика:")


def handle_comment_input(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id_for_comment")  # Получаем ID заказа
    if not order_id:
        update.message.reply_text("Не удалось определить заказ для комментария.")
        return

    comment = update.message.text
    order = Order.objects.get(id=int(order_id))

    order.delivery_comments = comment
    order.save()

    update.message.reply_text(f"Комментарий к заказу {order.id} успешно добавлен.")


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


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
