import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN = "8755506600:AAE2u8_hwneCbHt2F_Arp-BySl1PWWCqjiA"
ADMIN_ID = 7899678090  # Sizning Telegram ID raqamingiz

DB_FILE = os.path.expanduser("~/catalog_db.json")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        CATALOG = json.load(f)
else:
    CATALOG = {"movies": [], "anime": [], "cartoons": [], "series": []}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(CATALOG, f, ensure_ascii=False, indent=2)

class AddMovieState(StatesGroup):
    category = State()
    title = State()
    year = State()
    genre = State()
    desc = State()
    video = State()

def get_main_menu(is_admin: bool = False):
    kb = [
        [KeyboardButton(text="🎬 Kinolar"), KeyboardButton(text="🍿 Anime")],
        [KeyboardButton(text="🧸 Multfilmlar"), KeyboardButton(text="📺 Seriallar")],
        [KeyboardButton(text="🔥 Trendlar"), KeyboardButton(text="⭐ Eng yaxshi")],
        [KeyboardButton(text="🔎 Qidirish")]
    ]
    # Faqat adminga ko'rinadigan tugma
    if is_admin:
        kb.append([KeyboardButton(text="➕ Kino qo'shish (Admin)")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    greeting = " (Admin 👑)" if is_admin else ""
    await message.answer(
        f"👋 Assalomu alaykum, <b>{message.from_user.first_name}{greeting}</b>!\n\n"
        f"🎬 <b>Cinema Bot</b>ga xush kelibsiz!\n"
        f"Kinoni tanlang va tomosha qiling 🍿",
        reply_markup=get_main_menu(is_admin)
    )

# --- FAQAT ADMIN UCHUN KINO QO'SHISH ---
@dp.message(F.text == "➕ Kino qo'shish (Admin)")
@dp.message(Command("add"))
async def start_add_movie(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, siz admin emassiz! Faqat bot egasi kino qo'sha oladi.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kino", callback_data="addcat_movies"), InlineKeyboardButton(text="🍿 Anime", callback_data="addcat_anime")],
        [InlineKeyboardButton(text="🧸 Multfilm", callback_data="addcat_cartoons"), InlineKeyboardButton(text="📺 Serial", callback_data="addcat_series")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_add")]
    ])
    await message.answer("Qaysi bo'limga qo'shasiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith("addcat_"))
async def set_category(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    cat = call.data.split("_")[1]
    await state.update_data(category=cat)
    await state.set_state(AddMovieState.title)
    await call.message.edit_text("1️⃣ Kino <b>nomini</b> yozing:")

@dp.message(AddMovieState.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovieState.year)
    await message.answer("2️⃣ Chiqarilgan <b>yili</b> (masalan: 2023):")

@dp.message(AddMovieState.year)
async def set_year(message: Message, state: FSMContext):
    await state.update_data(year=message.text.strip())
    await state.set_state(AddMovieState.genre)
    await message.answer("3️⃣ <b>Janri</b> (masalan: Jangari, Komediya):")

@dp.message(AddMovieState.genre)
async def set_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text.strip())
    await state.set_state(AddMovieState.desc)
    await message.answer("4️⃣ Qisqacha <b>tavsifi</b>:")

@dp.message(AddMovieState.desc)
async def set_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text.strip())
    await state.set_state(AddMovieState.video)
    await message.answer(
        "5️⃣ Endi kino <b>VIDEOSINI</b> yuboring!\n\n"
        "<i>(Video faylni to'g'ridan-to'g'ri yuboring yoki kanaldan forward qilib tashlang)</i>"
    )

@dp.message(AddMovieState.video)
async def set_video(message: Message, state: FSMContext):
    video_id = None
    is_document = False

    if message.video:
        video_id = message.video.file_id
    elif message.document:
        video_id = message.document.file_id
        is_document = True
    else:
        await message.answer("⚠️ Iltimos, video fayl yuboring!")
        return

    data = await state.get_data()
    all_items = [item for cat in CATALOG.values() for item in cat]
    new_id = (max([i["id"] for i in all_items]) + 1) if all_items else 1

    new_item = {
        "id": new_id,
        "title": data["title"],
        "year": data.get("year", ""),
        "genre": data.get("genre", ""),
        "desc": data.get("desc", ""),
        "video_id": video_id,
        "is_document": is_document
    }

    cat = data["category"]
    if cat not in CATALOG:
        CATALOG[cat] = []
    CATALOG[cat].append(new_item)
    save_db()

    await state.clear()
    await message.answer(
        f"🎉 <b>«{new_item['title']}» muvaffaqiyatli saqlandi!</b>",
        reply_markup=get_main_menu(is_admin=True)
    )

@dp.callback_query(F.data == "cancel_add")
async def cancel_add(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")

# --- KINO RO'YXATI VA TOMOSHA QILISH ---
def get_items_keyboard(items):
    buttons = []
    for item in items:
        buttons.append([InlineKeyboardButton(text=f"🎬 {item['title']} ({item.get('year', '')})", callback_data=f"sendvideo_{item['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(F.text.in_(["🎬 Kinolar", "🍿 Anime", "🧸 Multfilmlar", "📺 Seriallar"]))
async def show_category(message: Message):
    mapping = {
        "🎬 Kinolar": "movies",
        "🍿 Anime": "anime",
        "🧸 Multfilmlar": "cartoons",
        "📺 Seriallar": "series",
    }
    cat_key = mapping[message.text]
    items = CATALOG.get(cat_key, [])
    if not items:
        await message.answer(f"{message.text} bo'limi hozircha bo'sh.")
        return
    await message.answer(f"<b>{message.text} ro'yxati:</b>\n<i>Kerakli kinoni tanlang:</i>", reply_markup=get_items_keyboard(items))

@dp.callback_query(F.data.startswith("sendvideo_"))
async def send_movie_video(call: CallbackQuery):
    item_id = int(call.data.split("_")[1])
    all_items = [item for cat in CATALOG.values() for item in cat]
    item = next((i for i in all_items if i['id'] == item_id), None)
    
    if not item or not item.get("video_id"):
        await call.answer("❌ Bu kinoning video fayli topilmadi.", show_alert=True)
        return

    caption = (
        f"🎬 <b>{item['title']}</b> ({item.get('year', '')})\n"
        f"🏷 Janr: {item.get('genre', '')}\n\n"
        f"📝 {item.get('desc', '')}\n\n"
        f"🍿 <i>Maroqli tomosha tilaymiz!</i>"
    )

    await call.message.answer("Marhamat, kino yuborilmoqda... ⏳")
    try:
        if item.get("is_document"):
            await call.message.answer_document(document=item["video_id"], caption=caption)
        else:
            await call.message.answer_video(video=item["video_id"], caption=caption)
    except Exception as e:
        await call.message.answer(f"Xatolik: {e}")
    await call.answer()

@dp.message(F.text == "🔥 Trendlar")
async def show_trends(message: Message):
    all_items = [item for cat in CATALOG.values() for item in cat]
    if not all_items:
        await message.answer("Kontent mavjud emas.")
        return
    await message.answer("🔥 <b>Trenddagi kinolar:</b>", reply_markup=get_items_keyboard(all_items))

@dp.message(F.text == "⭐ Eng yaxshi")
async def show_top(message: Message):
    all_items = [item for cat in CATALOG.values() for item in cat]
    if not all_items:
        await message.answer("Kontent mavjud emas.")
        return
    await message.answer("⭐ <b>Eng yaxshi kinolar:</b>", reply_markup=get_items_keyboard(all_items))

@dp.message(F.text == "🔎 Qidirish")
async def ask_search(message: Message):
    await message.answer("Qidirayotgan kino nomini yozing:")

@dp.message()
async def search_handler(message: Message):
    query = message.text.lower().strip()
    all_items = [item for cat in CATALOG.values() for item in cat]
    results = [i for i in all_items if query in i['title'].lower() or query in i.get('genre', '').lower()]
    if not results:
        await message.answer("🔍 Hech narsa topilmadi.")
        return
    await message.answer(f"🔍 <b>«{message.text}» bo'yicha topilgan kinolar:</b>", reply_markup=get_items_keyboard(results))

async def main():
    print("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
