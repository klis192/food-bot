import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import storage
import ai

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAIN_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🍽 Подобрать блюда", callback_data="suggest"),
        InlineKeyboardButton("🛒 Что купить?", callback_data="tobuy"),
    ],
    [
        InlineKeyboardButton("📋 Мои продукты", callback_data="list"),
        InlineKeyboardButton("🗑 Очистить список", callback_data="clear"),
    ],
])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе решить, что приготовить из имеющихся продуктов.\n\n"
        "Просто напиши мне список продуктов — через запятую или каждый с новой строки.\n\n"
        "Команды:\n"
        "/list — посмотреть список продуктов\n"
        "/clear — очистить список",
        reply_markup=MAIN_KEYBOARD,
    )


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    products = storage.get_products(user_id)
    if not products:
        text = "Список продуктов пуст. Напиши мне что у тебя есть!"
    else:
        text = "Твои продукты:\n" + "\n".join(f"• {p}" for p in products)
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD)


async def clear_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    storage.clear_products(user_id)
    await update.message.reply_text(
        "Список продуктов очищен.", reply_markup=MAIN_KEYBOARD
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Split by commas or newlines
    raw_items = re.split(r"[,\n]+", text)
    products = [item.strip() for item in raw_items if item.strip()]

    if not products:
        await update.message.reply_text(
            "Не понял. Напиши список продуктов через запятую или каждый с новой строки."
        )
        return

    storage.add_products(user_id, products)
    added = ", ".join(products)
    await update.message.reply_text(
        f"Добавлено: {added}\n\nЧто хочешь сделать?",
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "list":
        products = storage.get_products(user_id)
        if not products:
            text = "Список продуктов пуст. Напиши мне что у тебя есть!"
        else:
            text = "Твои продукты:\n" + "\n".join(f"• {p}" for p in products)
        await query.edit_message_text(text, reply_markup=MAIN_KEYBOARD)

    elif query.data == "clear":
        storage.clear_products(user_id)
        await query.edit_message_text(
            "Список продуктов очищен.", reply_markup=MAIN_KEYBOARD
        )

    elif query.data in ("suggest", "tobuy"):
        products = storage.get_products(user_id)
        if not products:
            await query.edit_message_text(
                "Список продуктов пуст. Сначала напиши что у тебя есть!",
                reply_markup=MAIN_KEYBOARD,
            )
            return

        await query.edit_message_text("Думаю... ⏳")

        try:
            if query.data == "suggest":
                result = ai.suggest_dishes_from_available(products)
            else:
                result = ai.suggest_dishes_to_buy(products)
        except Exception as e:
            logger.error("AI error: %s", e)
            await query.edit_message_text(
                "Произошла ошибка при обращении к AI. Попробуй ещё раз.",
                reply_markup=MAIN_KEYBOARD,
            )
            return

        # Telegram message limit is 4096 chars
        if len(result) > 4000:
            result = result[:4000] + "..."

        await query.edit_message_text(result, reply_markup=MAIN_KEYBOARD)


def main():
    storage.init_db()
    token = os.environ["TELEGRAM_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_products))
    app.add_handler(CommandHandler("clear", clear_products))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
