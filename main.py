import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaAudio, InputMediaPhoto
from telegram.error import BadRequest
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes, ConversationHandler

from config import BOT_TOKEN, USER_ID


# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes):
    context.user_data['cur_data'] = []
    context.user_data['cur_poem'] = ""

    keyboard = [["Стихотворение"],
                ["Вложения"]]
    markup = ReplyKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Здравствуйте! Я помогу вам отправить ваше творчество "
        "для дальнейшей публикации. Выберите тип на клавиатуре.",
        reply_markup=markup
    )

    return 1


async def get_creativity(update: Update, context: ContextTypes):
    keyboard = [["Отмена"]]

    if update.message.text == "Стихотворение":
        await update.message.reply_text(
            "Отправьте, пожалуйста, ваше стихотворение мне. "
            "Я передам!",
            reply_markup=ReplyKeyboardMarkup(keyboard)
        )

        return 2

    else:
        await update.message.reply_text(
            "Отправьте, пожалуйста, ваши материалы мне. "
            "Я передам!",
            reply_markup=ReplyKeyboardMarkup(keyboard)
        )

        return 3


async def get_text(update: Update, context: ContextTypes):
    msg = update.message.text

    if msg == "Отмена":
        await update.message.reply_text(
            "Вы отменили отправку.\n\n"
            "Используйте /start для повторной отправки.",
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    context.user_data['cur_poem'] = msg

    keyboard = [["Отправить"]]
    markup = ReplyKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Отлично! Прикрепите вложения, если таковые имеются. "
        "По окончанию нажмите на кнопку на клавиатуре.",
        reply_markup=markup
    )

    return 3


async def get_materials(update: Update, context: ContextTypes):
    if update.message.text == "Отмена":
        await update.message.reply_text(
            "Вы отменили отправку.\n\n"
            "Используйте /start для повторной отправки.",
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    if update.message.text == "Отправить":
        context.user_data['sender'] = update.message.from_user.username
        await send_materials(update, context)
        await update.message.reply_text(
            "Успешно отправлено! Большое спасибо вам за "
            "проявленный интерес! "
            "Используйте команду /start для повторной "
            "отправки. Буду рад помочь вам!",
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    data = update.message.effective_attachment

    try:
        data = data.file_id
        data = InputMediaAudio(media=data)

    except AttributeError:
        data = data[-1].file_id
        data = InputMediaPhoto(media=data)

    context.user_data['cur_data'].append(data)

    keyboard = [["Отправить"]]
    markup = ReplyKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Добавлено {len(context.user_data['cur_data'])}-е вложение. "
        "По окончанию нажмите на кнопку на клавиатуре.",
        reply_markup=markup
    )

    return 3


async def send_materials(update: Update, context: ContextTypes):
    await context.bot.send_message(
        USER_ID,
        f"Новое уведомление!\n\nОт @{context.user_data['sender']}:"
    )

    if context.user_data['cur_poem']:
        if context.user_data['cur_data']:
            try:
                await context.bot.send_media_group(
                    USER_ID,
                    media=context.user_data['cur_data'],
                    caption=context.user_data['cur_poem'])

            except BadRequest:
                await context.bot.send_media_group(
                    USER_ID,
                    media=[i for i in context.user_data['cur_data']
                           if isinstance(i, InputMediaAudio)],
                    caption=context.user_data['cur_poem'])

                await context.bot.send_media_group(
                    USER_ID,
                    media=[i for i in context.user_data['cur_data']
                           if isinstance(i, InputMediaPhoto)])

        else:
            await context.bot.send_message(USER_ID,
                                           context.user_data['cur_poem'])

    else:
        try:
            await context.bot.send_media_group(
                USER_ID, media=context.user_data['cur_data'])

        except BadRequest:
            await context.bot.send_media_group(
                USER_ID,
                media=[i for i in context.user_data['cur_data']
                       if isinstance(i, InputMediaAudio)])

            await context.bot.send_media_group(
                USER_ID,
                media=[i for i in context.user_data['cur_data']
                       if isinstance(i, InputMediaPhoto)])

    context.user_data['cur_poem'] = ""
    context.user_data['cur_data'] = []


def main():
    # Создаём объект Application.
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        # Точка входа в диалог.
        entry_points=[CommandHandler('start', start)],

        # Состояние внутри диалога.
        states={
            1: [MessageHandler(filters.Text(['Стихотворение',
                                             'Вложения']),
                               get_creativity)],
            2: [MessageHandler(filters.TEXT,
                               get_text)],
            3: [MessageHandler(filters.ALL & ~filters.COMMAND, get_materials)]
        },

        # Точка прерывания диалога. В данном случае — команда /stop.
        fallbacks=[MessageHandler(filters.Text(['Отмена']),
                                  get_materials)]
    )

    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("start", start))

    # Запускаем приложение.
    application.run_polling()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()
