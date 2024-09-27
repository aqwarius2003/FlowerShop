# main.py
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, \
    TelegramError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler, \
    CallbackContext
from datetime import datetime
from bot_admin import get_handlers

import telegram
import re
import django
import os
import logging
from django.conf import settings

# Настройка переменной окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FlowerShop.settings')
django.setup()  # Инициализация Django

from tg_bot.models import Category, Product, PriceRange, UserBot, Order

from bot_admin import (
#    add_comment,
    assign_delivery,
    change_order_status,
    delivery_orders,
    go_back_to_delivery_orders,
    go_back_to_manager_orders,
#    handle_comment_input,
    handle_delivery_order,
    handle_order_selection,
    manager_orders,
    set_delivery_person,
    set_delivery_status,
    set_order_status,
)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Определим состояния
EVENT, BUDGET, PRODUCT_SELECTION, INPUT_DATA, CONFIRMATION = range(5)

users = {}
load_dotenv()
TOKEN = os.getenv('TG_BOT_TOKEN')


# Основное меню с выбором события
def start(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    user_data.clear()
    logger.info(f"Пользователь user {update.effective_user.id}")
    event_chose(update, context)
    return EVENT


def send_photo_message(update: Update, context: CallbackContext, photo_path: str = None, caption: str = None,
                       reply_markup: InlineKeyboardMarkup = None) -> None:
    # Проверка наличия callback_query
    if update.callback_query:
        query = update.callback_query
        query.answer()

        # Загрузка пути к фото из user_data, если не передан
        if photo_path is None:
            logger.info(f"путь фото для сообщения, если патч пустой {context.user_data['photo_path']}")
            photo_path = context.user_data['photo_path']

        # Проверка, изменились ли подпись или разметка
        if query.message.caption != caption or query.message.reply_markup != reply_markup:
            # Редактирование существующего сообщения с фото
            if 'last_photo_message_id' in context.user_data:
                try:
                    context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=context.user_data['last_photo_message_id'],
                        media=InputMediaPhoto(open(photo_path, 'rb'), caption=caption, parse_mode="Markdown"),
                        reply_markup=reply_markup
                    )
                except TelegramError as e:
                    logger.error(f"Ошибка редактирования сообщения: {e}")
            else:
                # Если это первое сообщение с продуктом, отправляем фото
                with open(photo_path, 'rb') as photo:
                    message = query.message.reply_photo(photo=photo, caption=caption, reply_markup=reply_markup,
                                                        parse_mode="Markdown")
                    context.user_data['last_photo_message_id'] = message.message_id
        else:
            # Если ничего не изменилось, просто обновляем ID сообщения
            context.user_data['last_photo_message_id'] = query.message.message_id
    else:
        # Обработка обычного сообщения
        if 'last_photo_message_id' in context.user_data:
            try:
                # Редактирование существующего сообщения с фото
                context.bot.edit_message_media(
                    chat_id=update.message.chat_id,
                    message_id=context.user_data['last_photo_message_id'],
                    media=InputMediaPhoto(open(photo_path, 'rb'), caption=caption, parse_mode="Markdown"),
                    reply_markup=reply_markup
                )
            except TelegramError as e:
                logger.error(f"Ошибка редактирования сообщения: {e}")
        else:
            # Если это первое сообщение с продуктом, отправляем фото
            with open(photo_path, 'rb') as photo:
                message = update.message.reply_photo(photo=photo, caption=caption, reply_markup=reply_markup,
                                                     parse_mode="Markdown")
                context.user_data['last_photo_message_id'] = message.message_id

    # Дополнительная логика для отслеживания состояния сообщений
    logger.info(f"сообщение с фото : {context.user_data['last_photo_message_id']}")


def event_chose(update: Update, context: CallbackContext) -> None:
    logger.info('зашел в меню евент')
    photo_path = os.path.join('static', 'products', 'to', 'event.jpg')

    # Получение списка событий из БД
    events = Category.objects.all()
    keyboard = []
    caption = '**  🎉 Выберите событие или повод подарить цветы 🌹🌹🌹**'
    for event in events:
        keyboard.append([InlineKeyboardButton(event.name, callback_data=f'event_{event.id}_{event.name}')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    send_photo_message(update, context, photo_path, caption, reply_markup)
    context.user_data['event'] = None
    return EVENT


def budget_chose(update: Update, context: CallbackContext) -> int:
    photo_path = os.path.join('static', 'products', 'to', 'budget.jpg')

    # Получение списка бюджетов из БД
    budgets = PriceRange.objects.all()
    keyboard = []
    caption = '** Выберите бюджет презента 💰**'
    # Создаем отдельную строку для каждой кнопки бюджета
    for budget in budgets:
        keyboard.append([InlineKeyboardButton(str(budget), callback_data=f"budget_{budget}")])

    # кнопка "Назад" в отдельной строке
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_event")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    send_photo_message(update, context, photo_path, caption, reply_markup)
    return BUDGET


def generate_list_products(update: Update, context: CallbackContext):
    query = update.callback_query
    logger.info(f"вход в выборку из бд {context.user_data['event']=} и {context.user_data['budget']=}")

    # price_range_str = context.user_data['budget']('руб', '').strip()
    price_range_str = context.user_data['budget'].replace('руб', '').strip()

    # Вариант: "до 1000 руб"
    if "до" in price_range_str:
        max_price = float(price_range_str.replace('до', '').strip())  # Извлекаем максимальную цену
        min_price = 0  # Минимальная цена в этом случае равна 0

    # Вариант: "Без ограничения"
    elif "Без ограничения" in price_range_str:
        min_price = 0  # Минимальная цена равна 0
        max_price = float('inf')  # Максимальная цена как "бесконечность"


    # Вариант: "1001-3000 руб" (диапазон)
    elif "-" in price_range_str:
        price_range_list = price_range_str.split('-')

        if len(price_range_list) != 2:
            logger.info(f"Неправильный формат диапазона цен. {len(price_range_list)=}")
            return BUDGET

        try:
            min_price = float(price_range_list[0].strip())
            max_price = float(price_range_list[1].strip())
        except ValueError:
            logger.info(f"Неправильный формат диапазона цен. 2")
            return BUDGET

    else:
        logger.info("Неправильный формат диапазона цен. 3")
        return BUDGET

    logger.info(f"перед запросом обработка фильтров {min_price=}, {max_price=}, context.user_data['event']")

    # Выборка товаров на основе выбранных событий и бюджета
    filter_conditions = {
        'price__gte': min_price,
        'categories__name': context.user_data['event']
    }
    # Условие для max_price
    if max_price != float('inf'):
        filter_conditions['price__lte'] = max_price

    products = Product.objects.filter(**filter_conditions)
    if products.exists():
        context.user_data['products'] = products
        print(product for product in products)
        context.user_data['current_product'] = 0  # Инициализируем current_product
        show_product(update, context)
    else:
        logger.info("В этой категории нет товаров. сработала (if not products) 234 строка")
        if 'budget' in context.user_data:
            del context.user_data['budget']
        caption = 'Ничего не можем предложить.\nВыберите другой повод или бюджет'
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back_to_budget")]])
        photo_path = os.path.join('static', 'products', 'to', 'error.jpg')
        send_photo_message(update, context, photo_path=photo_path, caption=caption, reply_markup=reply_markup)
        return EVENT


def show_product(update: Update, context: CallbackContext):
    user_data = context.user_data

    products = context.user_data.get('products', [])
    current_index = user_data.get('current_product', 0)

    # Проверка, что список продуктов не пуст и индекс находится в пределах длины списк
    if current_index >= len(products):
        logger.info("Ошибка: неправильный индекс товара - if current_index >= len(products)")
        return ConversationHandler.END

    product = products[current_index]
    context.user_data['selected_product'] = product

    # Получаем путь к изображению
    photo_path = os.path.join(settings.MEDIA_ROOT, product.image.name)

    # Проверка на существование изображения
    if not os.path.exists(photo_path):
        logger.error(f"Image not found: {photo_path}")
        photo_path = os.path.join('static', 'products', 'to', 'error.jpg')
        # return

    # Формируем клавиатуру для продукта
    keyboard = [
        [InlineKeyboardButton("✔ Заказать", callback_data=f'product_{product.id}')],
        [InlineKeyboardButton("◀ Предыдущий", callback_data='prev_product'),
         InlineKeyboardButton("Следующий ▶", callback_data='next_product')],
        [InlineKeyboardButton("Назад в меню", callback_data='back_to_budget')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption = f"***{product.name}***\n\n{product.description}\n\nЦена: ***{product.price} руб.***"
    send_photo_message(update, context, photo_path, caption, reply_markup)


def next_product(update: Update, context: CallbackContext):
    products = context.user_data['products']
    context.user_data['current_product'] = (context.user_data['current_product'] + 1) % len(products)
    show_product(update, context)


def prev_product(update: Update, context: CallbackContext):
    products = context.user_data['products']
    context.user_data['current_product'] = (context.user_data['current_product'] - 1) % len(products)
    show_product(update, context)


def submit_order(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    print("------------------------ВВОШЛИ В Submit ORDer------------------")
    logger.info(
        f"full_name: {context.user_data['name']}, phone {context.user_data['phone']}, "
        f"address: {context.user_data['address']}")

    # Создание пользователя или получение существующего
    user, created = UserBot.objects.get_or_create(user_id=update.effective_user.id,
                                                  defaults={'full_name': context.user_data['name'],
                                                            'phone': context.user_data['phone'],
                                                            'address': context.user_data['address']})
    date_format_input = '%d.%m.%Y %H:%M'
    date_format_output = '%Y-%m-%d %H:%M'
    # Преобразование введенную дату и время
    delivery_date_time_input = context.user_data['delivery_date_time']
    delivery_date_time = datetime.strptime(delivery_date_time_input, date_format_input)
    delivery_date_time_formatted = delivery_date_time.strftime(date_format_output)

    # Создание заказа
    order, created = Order.objects.get_or_create(
        product=context.user_data['selected_product'],
        user=user,
        comment=context.user_data.get('comments', ''),
        delivery_address=context.user_data['address'],
        desired_delivery_date=delivery_date_time_formatted,
        status='created')

    # Сообщение пользователю о подтверждении заказа
    logger.info("Ваш заказ отправлен Менеджер свяжется с вами в ближайшее время.")

    return ConversationHandler.END  # Завершение диалога


# Завершение разговора
def cancel(update: Update, context: CallbackContext) -> int:
    logger.info('Процесс заказа отменен. Напишите /start, чтобы начать заново.')
    return ConversationHandler.END


def error_handler(update: object, context: CallbackContext) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)


def handle_callback(update: Update, context: CallbackContext) -> int:
    """
    Универсальный обработчик для всех callback_data.
    """
    query = update.callback_query
    query.answer()
    callback_data = query.data

    # Разбор данных callback
    if callback_data.startswith("event_"):
        query = update.callback_query
        query.answer()
        event = query.data.split('_')[2]
        context.user_data['event'] = event

        logger.info(
            f"if callback_data.startswith(event_) пользователь {update.effective_user.id} "
            f"выбрал event: {context.user_data['event']}")
        # Переход к выбору бюджета
        budget_chose(update, context)
        return BUDGET

    elif callback_data.startswith("budget_"):
        budget = callback_data.split('_')[1]
        context.user_data['budget'] = budget
        generate_list_products(update, context)
        logger.info(f"пользователь {update.effective_user.id} выбрал budget_: {budget}")
        return PRODUCT_SELECTION

    elif callback_data.startswith("product_"):
        product_id = callback_data.split('_')[1]
        logger.info(f" выбрали товар с ID: {product_id}")
        # Логика выбора товара
        return PRODUCT_SELECTION

    elif callback_data == "back_to_event":
        logger.info("Кнопка 'Назад' нажата. Переход в меню событий.")
        event_chose(update, context)
        return EVENT


def handle_button_click(update: Update, context: CallbackContext):
    """ Обработчик нажатий в меню выбора товара"""
    query = update.callback_query
    query.answer()

    if query.data == 'next_product':
        next_product(update, context)

    elif query.data == 'prev_product':
        prev_product(update, context)

    elif query.data == 'back_to_budget':
        budget_chose(update, context)
        logger.info('back_to_budget')
        return EVENT

    elif query.data.startswith('product_'):
        product_id = int(query.data.split('_')[1])
        context.user_data['product_to_order'] = Product.objects.get(id=product_id)

        logger.info(f"выбран товар {context.user_data['product_to_order']}")
        show_order_form(update, context)
        return INPUT_DATA


def show_order_form(update: Update, context: CallbackContext, error_message=None):
    user_data = context.user_data
    product = context.user_data['selected_product']
    caption = (
            (f"**{error_message}**\n" if error_message else "") +
            f"***{product.name}***\nЦена: ***{product.price} руб.***\n\n"
            f"Имя: {user_data.get('name', 'Не указано')}\n"
            f"Телефон: {user_data.get('phone', 'Не указано')}\n"
            f"Адрес: {user_data.get('address', 'Не указано')}\n"
            f"Дата и время доставки: {user_data.get('delivery_date_time', 'Не указано')}\n"
            f"Комментарий к заказу: {user_data.get('comment', '')}"
    )

    buttons = [
        [InlineKeyboardButton("Введите ФИО", callback_data="input_name")],
        [InlineKeyboardButton("Введите телефон", callback_data="input_phone")],
        [InlineKeyboardButton("Введите адрес", callback_data="input_address")],
        [InlineKeyboardButton("Укажите дату и время доставки", callback_data="delivery_time")],
        [InlineKeyboardButton("Комментарий к заказу", callback_data="input_comment")],
        [InlineKeyboardButton("Отменить заказ", callback_data="cancel_order")],
        [InlineKeyboardButton("Отправить заказ", callback_data="submit_order")]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)
    photo_path = os.path.join(settings.MEDIA_ROOT, product.image.name)

    if not os.path.exists(photo_path):
        logger.error(f"Image not found: {photo_path}")
        return
    user_data['photo_path'] = photo_path

    send_photo_message(update, context, caption=caption, photo_path=photo_path, reply_markup=reply_markup)


# Обработчики ввода данных
def handle_button_click_menu_order(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'input_name':
        caption = "Введите ФИО:"
        send_photo_message(update, context, caption=caption)
        context.user_data['query_data'] = 'input_name'
    elif query.data == 'input_phone':
        caption = "Введите телефон:"
        send_photo_message(update, context, caption=caption)
        context.user_data['query_data'] = 'input_phone'
    elif query.data == 'input_address':
        caption = "Введите адрес:"
        send_photo_message(update, context, caption=caption)
        context.user_data['query_data'] = 'input_address'
    elif query.data == 'delivery_time':
        caption = "Введите дату и время доставки в формате DD.MM.YY HH:MM"
        send_photo_message(update, context, caption=caption)
        context.user_data['query_data'] = 'delivery_time'
    elif query.data == 'input_comment':
        caption = "Введите комментарий к заказу:"
        send_photo_message(update, context, caption=caption)
        context.user_data['query_data'] = 'input_comment'
    elif query.data == 'cancel_order':
        query.message.delete()
        query.message.reply_text("Заказ отменен. Нажмите /start для нового заказа.")
        return ConversationHandler.END
    elif query.data == 'submit_order':
        user_data = context.user_data
        if all([user_data.get('name'), user_data.get('phone'), user_data.get('address'), user_data.get('delivery_date_time')]):
            print('Дошло до заказа')
            submit_order(update, context)
            caption = "Ваш заказ отправлен в обработку!\nМенеджер свяжется с вами в ближайшее время."
            photo_path = os.path.join('static', 'products', 'to', 'call_manager.jpg')
            send_photo_message(update, context, photo_path=photo_path, caption=caption)

            return ConversationHandler.END
        else:
            show_order_form(update, context,
                            error_message="‼️ Пожалуйста, заполните все необходимые поля перед отправкой заказа ‼️")
            return INPUT_DATA

    return INPUT_DATA


# Функция обработки ввода данных
def input_data(update: Update, context: CallbackContext):
    text = update.message.text
    query_data = context.user_data.get('query_data')
    chat_id = update.effective_chat.id

    if 'query_msg_id' in context.user_data:
        context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['query_msg_id'])
        del context.user_data['query_msg_id']

    if query_data == 'input_name':
        context.user_data['name'] = text
    elif query_data == 'input_phone':
        context.user_data['phone'] = text
    elif query_data == 'input_address':
        context.user_data['address'] = text
    elif query_data == 'delivery_time':
# Проверка формата даты и времени
        date_format = '%d.%m.%Y %H:%M'
        try:
# Пробуем преобразовать текст в дату
            delivery_time = datetime.strptime(text, date_format)
            context.user_data['delivery_date_time'] = text
            context.user_data['delivery_time'] = delivery_time
            logger.info('Дата верная: %s', delivery_time)
            print(f'Время доставки: {context.user_data["delivery_time"]}')
        except ValueError:
          # Если формат неверный, отправить ошибку
            error_message = "‼️ Пожалуйста, введите дату и время в формате dd.mm.yyyy HH:MM ‼️"
            show_order_form(update, context, error_message=error_message)
            return INPUT_DATA


    elif query_data == 'input_comment':
        context.user_data['comment'] = text

    context.user_data['query_data'] = None

    context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    show_order_form(update, context)
    return INPUT_DATA


# Основная функция
def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    # Определим обработчики состояний
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            EVENT: [CallbackQueryHandler(handle_callback)],
            BUDGET: [CallbackQueryHandler(handle_callback)],
            PRODUCT_SELECTION: [CallbackQueryHandler(handle_button_click)],
            INPUT_DATA: [CallbackQueryHandler(handle_button_click_menu_order),
                         MessageHandler(Filters.text & ~Filters.command, input_data)],
            CONFIRMATION: [CallbackQueryHandler(submit_order, pattern='^submit_order$')]
        },
        fallbacks=[CommandHandler('cancel', cancel),
                   CommandHandler('manager', manager_orders),
                   CommandHandler('delivery', delivery_orders)]
    )

    for handler in get_handlers():
        dp.add_handler(handler)

    dp.add_handler(conv_handler)


    # Запуск бота
    updater.start_polling()
    updater.idle()


    # Добавление обработчика ошибок
    def error_handler(update: object, context: CallbackContext) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        if isinstance(context.error, telegram.error.BadRequest) and context.error.message == "Message is not modified":
            # Ignore this specific error or handle it differently
            return
        else:
            logger.warning('Update "%s" caused error "%s"' % (update, context.error))

    dp.add_error_handler(error_handler)

    # Запуск бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
