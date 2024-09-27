from telegram import Update
from telegram.ext import Updater, CallbackContext, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, Filters
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

# Состояния для обработки календаря и времени
INPUT_DATE, INPUT_TIME = range(2)


# Функция для старта выбора даты
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Добро пожаловать! Нажмите на кнопку, чтобы выбрать дату и время доставки.")
    update.message.reply_text("/input_delivery для ввода даты доставки.")


def ask_for_delivery_date(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    # Создаем календарь
    calendar, step = DetailedTelegramCalendar().build()
    query.edit_message_text(
        f"Выберите {LSTEP[step]}",
        reply_markup=calendar
    )

    return INPUT_DATE


# Функция для обработки выбора даты
def handle_calendar_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    result, key, step = DetailedTelegramCalendar().process(query.data)

    if not result and key:
        # Если дата еще не выбрана, продолжаем показывать календарь
        query.edit_message_text(f"Выберите {LSTEP[step]}", reply_markup=key)
        return INPUT_DATE

    elif result:
        # Если дата выбрана, сохраняем её в контекст пользователя
        context.user_data['delivery_date'] = result
        query.edit_message_text(f"Дата доставки выбрана: {result}\nТеперь введите время доставки (например, 14:00):")

        return INPUT_TIME


# Функция для обработки ввода времени
def handle_time_selection(update: Update, context: CallbackContext):
    user_input = update.message.text

    # Проверяем формат времени
    try:
        delivery_time = user_input.strip()
        # Простейшая проверка формата времени (чч:мм)
        time_parts = delivery_time.split(":")
        if len(time_parts) != 2 or not (0 <= int(time_parts[0]) < 24) or not (0 <= int(time_parts[1]) < 60):
            raise ValueError

        # Сохраняем время в контекст пользователя
        context.user_data['delivery_time'] = delivery_time

        # Показываем пользователю финальную информацию
        update.message.reply_text(
            f"Ваша дата и время доставки: {context.user_data['delivery_date']} {context.user_data['delivery_time']}")

        # Завершаем диалог
        return ConversationHandler.END

    except ValueError:
        # Если время введено неверно, просим ввести повторно
        update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате чч:мм (например, 14:00).")
        return INPUT_TIME


# Функция отмены
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Ввод даты и времени отменен.")
    return ConversationHandler.END


# Основная функция для запуска бота
def main():
    # Токен вашего бота
    TOKEN = "7268072268:AAFAxYs0ZSawqivsxVO3aJSDYiA8pigD_V8"

    # Создаем Updater и Dispatcher
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('input_delivery', ask_for_delivery_date)],
        states={
            INPUT_DATE: [CallbackQueryHandler(handle_calendar_selection)],
            INPUT_TIME: [MessageHandler(Filters.text & ~Filters.command, handle_time_selection)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавляем обработчики
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv_handler)

    # Запускаем бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
