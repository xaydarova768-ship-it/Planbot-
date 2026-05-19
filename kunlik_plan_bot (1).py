#!/usr/bin/env python3
"""
Kunlik Reja Telegram Bot (O'zbekcha)
Ishga tushirish: pip install python-telegram-bot
Keyin: python kunlik_plan_bot.py
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# === SOZLAMALAR ===
BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ"  # @BotFather dan oling

# Conversation states
CHOOSING_ACTION, ADDING_TASK, ADDING_TIME, ADDING_CATEGORY = range(4)

# Kategoriyalar
CATEGORIES = {
    "💼": "Ish",
    "📚": "O'qish",
    "🏃": "Sport",
    "🏠": "Uy",
    "👤": "Shaxsiy",
    "🎯": "Boshqa"
}

logging.basicConfig(level=logging.INFO)

# === XOTIRA (oddiy dict, DB o'rniga) ===
# user_id -> { "date": [...tasks] }
user_plans = {}

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def get_user_tasks(user_id):
    today = get_today()
    return user_plans.get(user_id, {}).get(today, [])

def save_task(user_id, task):
    today = get_today()
    if user_id not in user_plans:
        user_plans[user_id] = {}
    if today not in user_plans[user_id]:
        user_plans[user_id][today] = []
    user_plans[user_id][today].append(task)

def delete_task(user_id, index):
    today = get_today()
    tasks = user_plans.get(user_id, {}).get(today, [])
    if 0 <= index < len(tasks):
        tasks.pop(index)

def toggle_task(user_id, index):
    today = get_today()
    tasks = user_plans.get(user_id, {}).get(today, [])
    if 0 <= index < len(tasks):
        tasks[index]["done"] = not tasks[index].get("done", False)

# === ASOSIY MENYU ===
def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("➕ Vazifa qo'shish", callback_data="add_task"),
            InlineKeyboardButton("📋 Rejam", callback_data="view_plan"),
        ],
        [
            InlineKeyboardButton("✅ Bajarildi", callback_data="complete_task"),
            InlineKeyboardButton("🗑 O'chirish", callback_data="delete_task"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("🔄 Yangilash", callback_data="refresh"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Salom, {user.first_name}! 👋\n\n"
        f"🗓 <b>Kunlik Reja Botiga xush kelibsiz!</b>\n\n"
        f"Bu bot sizga kunlik vazifalaringizni:\n"
        f"• Vaqt bo'yicha rejalashtirish\n"
        f"• Kategoriyalash (ish, sport, o'qish...)\n"
        f"• Kuzatib borish imkonini beradi.\n\n"
        f"Boshlaylik! 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

# === REJANI KO'RISH ===
async def view_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    today_str = datetime.now().strftime("%d.%m.%Y")

    if not tasks:
        text = f"📅 <b>{today_str} — Bugungi reja</b>\n\n❌ Hozircha vazifa yo'q.\n\n➕ Vazifa qo'shing!"
    else:
        text = f"📅 <b>{today_str} — Bugungi reja</b>\n\n"
        by_category = {}
        for i, task in enumerate(tasks):
            cat = task.get("category", "🎯")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((i, task))

        for emoji, items in by_category.items():
            cat_name = CATEGORIES.get(emoji, "Boshqa")
            text += f"\n{emoji} <b>{cat_name}</b>\n"
            for i, task in items:
                status = "✅" if task.get("done") else "⬜"
                time_str = f" 🕐{task['time']}" if task.get("time") else ""
                text += f"  {status} {i+1}. {task['name']}{time_str}\n"

        done = sum(1 for t in tasks if t.get("done"))
        text += f"\n📊 Bajarildi: {done}/{len(tasks)}"

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

# === VAZIFA QO'SHISH — Nom ===
async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ <b>Yangi vazifa</b>\n\nVazifa nomini yozing:\n(Masalan: Kitob o'qish, Zalga borish...)",
        parse_mode="HTML"
    )
    return ADDING_TASK

async def receive_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_task"] = {"name": update.message.text.strip()}
    keyboard = [[InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_time")]]
    await update.message.reply_text(
        "🕐 Vaqtini kiriting (Masalan: 09:00, 14:30)\nYoki o'tkazib yuboring:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADDING_TIME

# === VAQT ===
async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text = update.message.text.strip()
    context.user_data["new_task"]["time"] = time_text
    return await ask_category(update, context)

async def skip_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["new_task"]["time"] = None
    return await ask_category(update, context, is_callback=True)

async def ask_category(update, context, is_callback=False):
    keyboard = [
        [InlineKeyboardButton(f"{e} {n}", callback_data=f"cat_{e}") for e, n in list(CATEGORIES.items())[:3]],
        [InlineKeyboardButton(f"{e} {n}", callback_data=f"cat_{e}") for e, n in list(CATEGORIES.items())[3:]],
    ]
    text = "📁 Kategoriyani tanlang:"
    if is_callback:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ADDING_CATEGORY

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emoji = query.data.replace("cat_", "")
    task = context.user_data.get("new_task", {})
    task["category"] = emoji
    task["done"] = False
    save_task(query.from_user.id, task)

    time_info = f" | 🕐 {task['time']}" if task.get("time") else ""
    cat_name = CATEGORIES.get(emoji, "Boshqa")
    text = (
        f"✅ <b>Vazifa qo'shildi!</b>\n\n"
        f"{emoji} {task['name']}{time_info}\n"
        f"📁 {cat_name}\n\n"
        f"Davom etish:"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

# === BAJARILDI ===
async def complete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    if not tasks:
        await query.answer("❌ Vazifalar yo'q!", show_alert=True)
        return CHOOSING_ACTION

    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if task.get("done") else "⬜"
        keyboard.append([InlineKeyboardButton(
            f"{status} {i+1}. {task['name']}", callback_data=f"toggle_{i}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="refresh")])
    await query.edit_message_text(
        "✅ <b>Bajarildi/Bajarilmadi belgilash:</b>\nVazifaga bosing:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_ACTION

async def toggle_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data.replace("toggle_", ""))
    toggle_task(query.from_user.id, index)
    await complete_task_start(update, context)
    return CHOOSING_ACTION

# === O'CHIRISH ===
async def delete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    if not tasks:
        await query.answer("❌ Vazifalar yo'q!", show_alert=True)
        return CHOOSING_ACTION

    keyboard = []
    for i, task in enumerate(tasks):
        keyboard.append([InlineKeyboardButton(
            f"🗑 {i+1}. {task['name']}", callback_data=f"del_{i}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="refresh")])
    await query.edit_message_text(
        "🗑 <b>Qaysi vazifani o'chirmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_ACTION

async def delete_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data.replace("del_", ""))
    delete_task(query.from_user.id, index)
    await query.answer("✅ O'chirildi!", show_alert=True)
    await view_plan(update, context)
    return CHOOSING_ACTION

# === STATISTIKA ===
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("done"))
    percent = int(done / total * 100) if total else 0
    bar = "🟩" * (percent // 10) + "⬜" * (10 - percent // 10)

    text = (
        f"📊 <b>Bugungi statistika</b>\n\n"
        f"{bar}\n"
        f"✅ Bajarildi: {done}\n"
        f"⬜ Qoldi: {total - done}\n"
        f"📌 Jami: {total}\n"
        f"🏆 Natija: {percent}%\n\n"
    )
    if percent == 100 and total > 0:
        text += "🎉 Ajoyib! Barcha vazifalar bajarildi!"
    elif percent >= 50:
        text += "💪 Yaxshi ketayapti, davom eting!"
    else:
        text += "🔥 Harakatda bo'ling, uddalaysiz!"

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

# === YANGILASH ===
async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏠 <b>Asosiy menyu</b>\nNima qilmoqchisiz?",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )
    return CHOOSING_ACTION

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(add_task_start, pattern="^add_task$"),
                CallbackQueryHandler(view_plan, pattern="^view_plan$"),
                CallbackQueryHandler(complete_task_start, pattern="^complete_task$"),
                CallbackQueryHandler(delete_task_start, pattern="^delete_task$"),
                CallbackQueryHandler(stats, pattern="^stats$"),
                CallbackQueryHandler(refresh, pattern="^refresh$"),
                CallbackQueryHandler(toggle_task_handler, pattern="^toggle_"),
                CallbackQueryHandler(delete_task_handler, pattern="^del_"),
            ],
            ADDING_TASK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_name),
            ],
            ADDING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time),
                CallbackQueryHandler(skip_time, pattern="^skip_time$"),
            ],
            ADDING_CATEGORY: [
                CallbackQueryHandler(receive_category, pattern="^cat_"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
