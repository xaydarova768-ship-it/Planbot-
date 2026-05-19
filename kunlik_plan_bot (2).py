#!/usr/bin/env python3
import logging
import os
import random
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TIMEZONE = pytz.timezone("Asia/Tashkent")

CHOOSING_ACTION, ADDING_TASK, ADDING_TIME, ADDING_CATEGORY, ADDING_NOTE = range(5)

CATEGORIES = {
    "💼": "Ish",
    "📚": "O'qish",
    "🏃": "Sport",
    "🏠": "Uy ishlari",
    "👤": "Shaxsiy",
    "💊": "Sog'liq",
    "💰": "Moliya",
    "🎯": "Boshqa"
}

MOTIVATSIYA = [
    "💪 Har bir qadam maqsad sari olib boradi!",
    "🔥 Bugun kuchli kun, davom eting!",
    "⭐ Kichik qadamlar katta yutuqlarga olib keladi!",
    "🚀 Muvaffaqiyat har kuni mehnat qilishdan boshlanadi!",
    "🌟 Siz qila olasiz, ishoning o'zingizga!",
    "💡 Bugungi reja — ertangi muvaffaqiyat!",
    "🎯 Focused bo'ling, maqsadga erishing!",
    "✨ Har bir vazifa bajarilganda — g'alaba!",
]

MASLAHATLAR = [
    "📌 Eng muhim 3 ta vazifani belgilab, ulardan boshlang!",
    "⏰ Har bir vazifaga aniq vaqt belgilang.",
    "🧠 Muhim ishlarni ertalab bajarish yaxshi — miya yangi!",
    "📵 Ish vaqtida telefon bildirishnomalarini o'chiring.",
    "💧 Har soatda bir oz suv iching va dam oling.",
    "📝 Kechqurun ertangi rejaingizni tuzing.",
    "🎯 Bir vaqtda faqat bitta ishga e'tibor bering.",
    "🏃 Har kuni kamida 20 daqiqa harakat qiling.",
]

logging.basicConfig(level=logging.INFO)

user_plans = {}
user_settings = {}

def get_today():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_user_tasks(user_id, date=None):
    if date is None:
        date = get_today()
    return user_plans.get(user_id, {}).get(date, [])

def save_task(user_id, task):
    today = get_today()
    if user_id not in user_plans:
        user_plans[user_id] = {}
    if today not in user_plans[user_id]:
        user_plans[user_id][today] = []
    user_plans[user_id][today].append(task)

def toggle_task(user_id, index):
    today = get_today()
    tasks = user_plans.get(user_id, {}).get(today, [])
    if 0 <= index < len(tasks):
        tasks[index]["done"] = not tasks[index].get("done", False)
        if tasks[index]["done"]:
            tasks[index]["done_time"] = datetime.now(TIMEZONE).strftime("%H:%M")

def delete_task_fn(user_id, index):
    today = get_today()
    tasks = user_plans.get(user_id, {}).get(today, [])
    if 0 <= index < len(tasks):
        tasks.pop(index)

def progress_bar(done, total):
    if total == 0:
        return "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
    percent = int(done / total * 100)
    filled = percent // 10
    return "🟩" * filled + "⬜" * (10 - filled) + f" {percent}%"

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Vazifa qo'shish", callback_data="add_task"),
            InlineKeyboardButton("📋 Bugungi reja", callback_data="view_plan"),
        ],
        [
            InlineKeyboardButton("✅ Bajarildi", callback_data="complete_task"),
            InlineKeyboardButton("🗑 O'chirish", callback_data="delete_task"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("📅 Haftalik", callback_data="weekly"),
        ],
        [
            InlineKeyboardButton("💡 Maslahat", callback_data="tip"),
            InlineKeyboardButton("🏠 Bosh menyu", callback_data="home"),
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_settings:
        user_settings[user.id] = {"motivatsiya": True}

    text = (
        f"Salom, {user.first_name}! 👋\n\n"
        f"🗓 <b>Kunlik Reja Botiga xush kelibsiz!</b>\n\n"
        f"Men sizga yordam beraman:\n"
        f"📌 Kunlik vazifalar rejalashtirish\n"
        f"⏰ Vaqt va kategoriya bo'yicha tartib\n"
        f"📊 Statistika va tahlil\n"
        f"💡 Foydali maslahatlar\n\n"
        f"{random.choice(MOTIVATSIYA)}\n\n"
        f"Boshlaylik! 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

async def home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"🏠 <b>Bosh menyu</b>\n\n{random.choice(MOTIVATSIYA)}",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )
    return CHOOSING_ACTION

async def view_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    today_str = datetime.now(TIMEZONE).strftime("%d.%m.%Y")

    if not tasks:
        text = (
            f"📅 <b>{today_str} — Bugungi reja</b>\n\n"
            f"📭 Hali vazifa yo'q!\n\n"
            f"➕ Vazifa qo'shing va produktiv kun o'tkazing!\n\n"
            f"{random.choice(MOTIVATSIYA)}"
        )
    else:
        done = sum(1 for t in tasks if t.get("done"))
        text = f"📅 <b>{today_str} — Bugungi reja</b>\n"
        text += f"{progress_bar(done, len(tasks))}\n"
        text += f"✅ {done}/{len(tasks)} bajarildi\n\n"

        by_cat = {}
        for i, task in enumerate(tasks):
            cat = task.get("category", "🎯")
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append((i, task))

        for emoji, items in by_cat.items():
            text += f"{emoji} <b>{CATEGORIES.get(emoji, 'Boshqa')}</b>\n"
            for i, task in items:
                status = "✅" if task.get("done") else "⬜"
                time_str = f" 🕐{task['time']}" if task.get("time") else ""
                done_t = f" ({task['done_time']})" if task.get("done_time") else ""
                text += f"  {status} {i+1}. {task['name']}{time_str}{done_t}\n"
            text += "\n"

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ <b>Yangi vazifa</b>\n\nVazifa nomini yozing:\n<i>Masalan: Kitob o'qish, Zalga borish, Hisobot yozish...</i>",
        parse_mode="HTML"
    )
    return ADDING_TASK

async def receive_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_task"] = {"name": update.message.text.strip()}
    await update.message.reply_text(
        "🕐 Vaqtini kiriting:\n<i>Masalan: 09:00, 14:30</i>\nYoki o'tkazib yuboring:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Vaqtsiz qo'shish", callback_data="skip_time")]])
    )
    return ADDING_TIME

async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_task"]["time"] = update.message.text.strip()
    return await ask_category(update, context)

async def skip_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["new_task"]["time"] = None
    return await ask_category(update, context, True)

async def ask_category(update, context, is_cb=False):
    cats = list(CATEGORIES.items())
    keyboard = [
        [InlineKeyboardButton(f"{e} {n}", callback_data=f"cat_{e}") for e, n in cats[:4]],
        [InlineKeyboardButton(f"{e} {n}", callback_data=f"cat_{e}") for e, n in cats[4:]],
    ]
    text = "📁 Kategoriyani tanlang:"
    if is_cb:
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
    text = (
        f"✅ <b>Vazifa qo'shildi!</b>\n\n"
        f"{emoji} {task['name']}{time_info}\n"
        f"📁 {CATEGORIES.get(emoji, 'Boshqa')}\n\n"
        f"{random.choice(MOTIVATSIYA)}"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

async def complete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tasks = get_user_tasks(query.from_user.id)
    if not tasks:
        await query.answer("❌ Vazifalar yo'q!", show_alert=True)
        return CHOOSING_ACTION
    keyboard = [[InlineKeyboardButton(
        f"{'✅' if t.get('done') else '⬜'} {i+1}. {t['name']}",
        callback_data=f"toggle_{i}"
    )] for i, t in enumerate(tasks)]
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="home")])
    await query.edit_message_text(
        "✅ <b>Vazifani belgilang:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_ACTION

async def toggle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    toggle_task(query.from_user.id, int(query.data.replace("toggle_", "")))
    await complete_task_start(update, context)
    return CHOOSING_ACTION

async def delete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tasks = get_user_tasks(query.from_user.id)
    if not tasks:
        await query.answer("❌ Vazifalar yo'q!", show_alert=True)
        return CHOOSING_ACTION
    keyboard = [[InlineKeyboardButton(f"🗑 {i+1}. {t['name']}", callback_data=f"del_{i}")] for i, t in enumerate(tasks)]
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="home")])
    await query.edit_message_text(
        "🗑 <b>Qaysi vazifani o'chirmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_ACTION

async def delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ O'chirildi!", show_alert=True)
    delete_task_fn(query.from_user.id, int(query.data.replace("del_", "")))
    await view_plan(update, context)
    return CHOOSING_ACTION

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("done"))
    percent = int(done / total * 100) if total else 0

    text = (
        f"📊 <b>Bugungi statistika</b>\n\n"
        f"{progress_bar(done, total)}\n\n"
        f"✅ Bajarildi: {done}\n"
        f"⬜ Qoldi: {total - done}\n"
        f"📌 Jami: {total}\n"
        f"🏆 Natija: {percent}%\n\n"
    )

    if percent == 100 and total > 0:
        text += "🎉 Ajoyib! Barcha vazifalar bajarildi! Siz zoʻrsiz!"
    elif percent >= 70:
        text += "💪 Juda yaxshi! Davom eting!"
    elif percent >= 40:
        text += "👍 Yaxshi ketayapti, kuchliroq!"
    else:
        text += "🔥 Hali vaqt bor, harakatda bo'ling!"

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from datetime import timedelta
    today = datetime.now(TIMEZONE)
    text = f"📅 <b>Haftalik statistika</b>\n\n"
    
    total_all = 0
    done_all = 0
    
    for i in range(7):
        day = today - timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%d.%m")
        tasks = user_plans.get(user_id, {}).get(date_str, [])
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("done"))
        total_all += total
        done_all += done
        
        if total > 0:
            percent = int(done / total * 100)
            bar = "🟩" * (percent // 20) + "⬜" * (5 - percent // 20)
            text += f"{day_name}: {bar} {done}/{total}\n"
        else:
            text += f"{day_name}: — vazifa yo'q\n"
    
    text += f"\n📊 Jami: {done_all}/{total_all} bajarildi"
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"💡 <b>Bugungi maslahat</b>\n\n"
        f"{random.choice(MASLAHATLAR)}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"{random.choice(MOTIVATSIYA)}"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    return CHOOSING_ACTION

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
                CallbackQueryHandler(weekly, pattern="^weekly$"),
                CallbackQueryHandler(tip, pattern="^tip$"),
                CallbackQueryHandler(home, pattern="^home$"),
                CallbackQueryHandler(toggle_handler, pattern="^toggle_"),
                CallbackQueryHandler(delete_handler, pattern="^del_"),
            ],
            ADDING_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_name)],
            ADDING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time),
                CallbackQueryHandler(skip_time, pattern="^skip_time$"),
            ],
            ADDING_CATEGORY: [CallbackQueryHandler(receive_category, pattern="^cat_")],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    app.add_handler(conv)
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
