import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from rsq import token
from data import perfumes
from aiogram.types import FSInputFile
from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    MenuButtonDefault
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message
from aiogram.types import MenuButtonDefault
from PIL import Image, ImageOps, ImageDraw, ImageFilter
import io
import requests
from aiogram import Router
import aiohttp
router = Router()

#import requests
#FLASK_URL = "http://127.0.0.1:5000/"
user_favorites = {}


""""
async def track(telegram_id, event, value=""):
    async with aiohttp.ClientSession() as session:
        await session.post(
            "http://127.0.0.1:5000/api/track",
            json={
                "telegram_id": telegram_id,
                "event": event,
                "value": value
            }
        )
def auth_user(message):
    payload = {
        "telegram_id": message.from_user.id,
        "username": message.from_user.username
    }

    r = requests.post(f"{FLASK_URL}/api/telegram/auth", json=payload)
    r.raise_for_status()
    user_id = r.json()["user_id"]

    return user_id
"""
""""
def get_user_cards(telegram_id):
    r = requests.get(f"{FLASK_URL}/api/cards/{telegram_id}")
    r.raise_for_status()
    return r.json()
"""
"""
def load_cards(telegram_id):
    r = requests.get(f"http://127.0.0.1:5000/api/cards/{telegram_id}")
    r.raise_for_status()
    return r.json()
"""
SEARCH_FILTERS = {
    "volumes": ["30 мл", "50 мл", "100 мл", "200 мл"],
    "notes": ["цитрус", "цветочные", "древесные", "восточные", 
              "фруктовые", "мускус", "амбра", "ваниль", "пряные"]
}
"""
def add_card(telegram_id, product_id):
    r = requests.post(
        f"{FLASK_URL}/api/card/add/telegram",
        json={
            "telegram_id": telegram_id,
            "product_id": product_id
        }
    )
    r.raise_for_status()
"""

ITEMS_PER_PAGE = 5
bot = Bot(token=token)
dp = Dispatcher()

# Новые состояния для разных типов поиска
class SearchState(StatesGroup):
    waiting_query = State()
    waiting_note = State()
    waiting_brand = State()
    browsing = State()

async def resize_photo(photo_path: str, max_size: tuple = (1000, 1000), 
                      border_radius: int = 20, shadow_offset: int = 5) -> FSInputFile:
    """
    Создает фото со стильной рамкой как на примере
    max_size: (ширина, высота) в пикселях
    border_radius: радиус скругления углов
    shadow_offset: смещение тени
    """
    # Открываем изображение
    with Image.open(photo_path) as img:
        # Конвертируем RGBA в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаем белый фон для прозрачных изображений
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        
        # Сохраняем оригинальные пропорции
        original_width, original_height = img.size
        
        # Вычисляем новые размеры с сохранением пропорций
        ratio = min(max_size[0] / original_width, max_size[1] / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # Изменяем размер
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Создаем маску для скругленных углов
        mask = Image.new('L', (new_width, new_height), 0)
        draw = ImageDraw.Draw(mask)
        
        # Рисуем скругленный прямоугольник
        draw.rounded_rectangle(
            [(0, 0), (new_width, new_height)],
            radius=border_radius,
            fill=255
        )
        
        # Применяем маску к изображению
        img.putalpha(mask)
        
        # Создаем изображение с тенью (большего размера)
        shadow_size = (new_width + shadow_offset * 2, new_height + shadow_offset * 2)
        shadow_img = Image.new('RGBA', shadow_size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        
        # Рисуем тень (темный прямоугольник со скругленными углами)
        shadow_draw.rounded_rectangle(
            [(shadow_offset, shadow_offset), 
             (new_width + shadow_offset, new_height + shadow_offset)],
            radius=border_radius,
            fill=(50, 50, 50, 150)  # Полупрозрачный темный цвет
        )
        
        # Немного размываем тень для мягкости
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=3))
        
        # Создаем финальное изображение
        final_img = Image.new('RGBA', shadow_size, (255, 255, 255, 0))
        
        # Накладываем тень
        final_img.paste(shadow_img, (0, 0), shadow_img)
        
        # Накладываем основное изображение поверх тени
        main_img_position = (
            (shadow_size[0] - new_width) // 2,
            (shadow_size[1] - new_height) // 2
        )
        final_img.paste(img, main_img_position, img)
        
        # Сохраняем во временный файл
        temp_path = f"temp_{photo_path.split('/')[-1]}"
        final_img.save(temp_path, "PNG", quality=95, optimize=True)
        
        return FSInputFile(temp_path)

def order_keyboard(source: str, index: int):
    kb = InlineKeyboardBuilder()

    kb.button(
        text="📱 Сделать заказ",
        callback_data="order_info"
    )

    kb.button(
        text="⬅️ Назад",
        callback_data=f"order_back:{source}:{index}"
    )

    kb.adjust(1)
    return kb.as_markup()
@dp.callback_query(F.data.startswith("order_back:"))
async def order_back(callback: CallbackQuery, state: FSMContext):
    _, source, index = callback.data.split(":")
    index = int(index)
    data = await state.get_data()
    photo_id = data.get("order_photo_id")
    
    # Удаляем сообщение "Сделать заказ"
    await callback.message.delete()
    
    # Если фото есть, удаляем старое фото
    if photo_id:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=photo_id
        )
    
    # Очищаем данные о фото
    await state.update_data(order_photo_id=None)

    # Удаляем старое сообщение с пагинацией
    prev_message_id = data.get("order_message_id")
    if prev_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=prev_message_id
            )
        except Exception as e:
            print(f"Error deleting previous message: {e}")

    # 🔙 КАТАЛОГ
    if source == "catalog":
        perfume = perfumes[index]
        framed = await resize_photo(perfume["photo"])

        # Отправляем новую карточку товара с пагинацией
        new_message = await callback.message.answer_photo(
            framed,
            caption=(f"<b>{perfume['name']}</b>\n"
                     f"Пол: {perfume['category']}\n"
                     f"Объём: {perfume['volume']}"),
            parse_mode="HTML",
            reply_markup=catalog_card_keyboard(index, callback.from_user.id)
        )

        # Сохраняем message_id нового сообщения
        await state.update_data(order_message_id=new_message.message_id)

    # 🔙 КАТЕГОРИЯ
    elif source == "category":
        items = data.get("cat_items", [])
        perfume = items[index]

        framed = await resize_photo(perfume["photo"])

        # Отправляем новую карточку товара с пагинацией
        new_message = await callback.message.answer_photo(
            framed,
            caption=f"<b>{perfume['name']}</b>",
            parse_mode="HTML",
            reply_markup=category_card_keyboard(
                index,
                len(items),
                data.get("back_prefix", "gender"),
                perfume,
                callback.from_user.id
            )
        )

        # Сохраняем message_id нового сообщения
        await state.update_data(order_message_id=new_message.message_id)

    # 🔙 ПОИСК
    elif source == "search":
        results = data.get("search_results", [])
        perfume = results[index]

        framed = await resize_photo(perfume["photo"])

        # Отправляем новую карточку товара с пагинацией
        new_message = await callback.message.answer_photo(
            framed,
            caption=f"<b>{perfume['name']}</b>",
            parse_mode="HTML",
            reply_markup=search_card_keyboard(
                index,
                len(results),
                callback.from_user.id,
                perfume
            )
        )

        # Сохраняем message_id нового сообщения
        await state.update_data(order_message_id=new_message.message_id)

    await callback.answer()


@dp.callback_query(F.data == "order_info")
async def order_info(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get("order_photo_id")

    # источник возврата
    source = data.get("back_view")
    index = (
        data.get("catalog_index")
        or data.get("back_index")
        or 0
    )

    kb = InlineKeyboardBuilder()
    kb.button(
        text="⬅️ Назад",
        callback_data=f"order_back:{source}:{index}"
    )
    kb.adjust(1)
    
    # 🧹 удаляем старое сообщение с пагинацией (если оно есть)
    prev_message_id = data.get("order_message_id")
    if prev_message_id:
        try:
            await call.bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=prev_message_id
            )
        except Exception as e:
            print(f"Error deleting previous message: {e}")
    
    # 🧹 удаляем photo2 (если оно есть)
    if photo_id:
        await call.bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=photo_id
        )

    # очищаем id фото и старое сообщение
    await state.update_data(order_photo_id=None, order_message_id=None)

    # 📄 отправляем информацию о заказе
    order_message = await call.message.answer(
        """<u>Для оформления заказа обратитесь к человеку</u> который <b>пригласил Вас в чат</b> - https://t.me/aromo_code

<b>Или напишите Нашим администраторам</b>

Лидия - @LidiyaKlimenteva  
Николай - @Naum_SW

🎁 <b>При покупке двух и более ароматов подарок.</b>
""",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

    # Сохраняем message_id нового сообщения, чтобы не было дубликатов
    await state.update_data(order_message_id=order_message.message_id)

    await call.answer()



@dp.callback_query(F.data.startswith("back_to_search_"))
async def back_to_search(callback: CallbackQuery, state: FSMContext):
    try:
        index = int(callback.data.replace("back_to_search_", ""))
    except ValueError:
        await callback.answer("Ошибка в данных")
        return
    
    data = await state.get_data()
    results = data.get("search_results", [])
    
    if not results or index >= len(results):
        await callback.answer("Результаты поиска не найдены")
        return
    
    await state.update_data(search_index=index)
    perfume = results[index]
    
    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(perfume["photo"], 
                                     max_size=(800, 800), 
                                     border_radius=20, 
                                     shadow_offset=8)
    
    # Формируем заголовок
    search_type = data.get("search_type", "поиска")
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {perfume.get('category', 'не указано')}\n"
        f"Объём: {perfume.get('volume', 'не указано')}\n"
    )
    
    if search_type == "note":
        caption += f"<i>Найдено по ноте: {data.get('search_query', '')}</i>"
    elif search_type == "brand2":
        caption += f"<i>Найдено по бренду: {data.get('search_query', '')}</i>"
    
    # Редактируем сообщение с товаром
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=framed_photo,
                caption=caption,
                parse_mode="HTML"
            ),
            reply_markup=search_card_keyboard(index, len(results))
        )
    except:
        # Если нельзя редактировать, отправляем новое
        await callback.message.answer_photo(
            photo=framed_photo,
            caption=caption,
            reply_markup=search_card_keyboard(index, len(results)),
            parse_mode="HTML"
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("back_to_category_"))
async def back_to_category(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    
    if len(parts) < 5:  # back_to_category_type_index
        await callback.answer("Ошибка в данных")
        return
    
    category_type = parts[3]
    category_index = int(parts[4])
    
    data = await state.get_data()
    items = data.get("cat_items", [])
    
    if not items or category_index >= len(items):
        await callback.answer("Категория не найдена")
        return
    
    perfume = items[category_index]
    
    # Обновляем состояние
    await state.update_data(cat_index=category_index)
    
    # Формируем список категорий для отображения
    categories = []
    category2 = perfume.get("category2", [])
    
    if isinstance(category2, str):
        categories = [category2]
    elif isinstance(category2, list):
        categories = category2
    elif not category2:
        categories = [perfume.get("category", "не указано")]
    
    # Формируем текст категорий
    if isinstance(categories, list) and len(categories) > 0:
        categories_text = ", ".join(categories)
    else:
        categories_text = str(categories)
    
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {categories_text}\n"
        f"Объём: {perfume.get('volume', 'не указано')}"
    )
    
    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(
        perfume["photo"], 
        max_size=(800, 800), 
        border_radius=20, 
        shadow_offset=8
    )
    
    # Редактируем сообщение с товаром
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=framed_photo,
                caption=caption,
                parse_mode="HTML"
            ),
            reply_markup=category_card_keyboard(category_index, len(items), category_type, perfume)
        )
    except:
        # Если нельзя редактировать, отправляем новое
        await callback.message.answer_photo(
            photo=framed_photo,
            caption=caption,
            reply_markup=category_card_keyboard(category_index, len(items), category_type, perfume),
            parse_mode="HTML"
        )
    
    await callback.answer()
    
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 Посмотреть весь каталог")
            ],
            [
                KeyboardButton(text="📂 Категории"),
                KeyboardButton(text="🔍 Поиск")
            ],
            [
                KeyboardButton(text="⭐ Избранное"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def favorite_button(telegram_id: int,perfume_id: int,source: str,index: int):
    user_favs = user_favorites.get(telegram_id, set())

    if perfume_id in user_favs:
        return (
            "❌ Удалить из избранного",
            f"fav_remove:{perfume_id}:{source}:{index}"
        )
    else:
        return (
            "⭐ Добавить в избранное",
            f"fav_add:{perfume_id}:{source}:{index}"
        )





def categories_keyboard():
    kb = InlineKeyboardBuilder()

    kb.button(text="👩 Для неё", callback_data="cat_gender_women")
    kb.button(text="👨 Для него", callback_data="cat_gender_men")
    kb.button(text="⚧ Унисекс", callback_data="cat_gender_unisex")

    kb.button(text="✨ Нишевые", callback_data="cat_scent_niche")
    kb.button(text="🌸 Цветочные", callback_data="cat_scent_floral")
    kb.button(text="🍋 Цитрусовые", callback_data="cat_scent_citrus")
    kb.button(text="🌳 Древесные", callback_data="cat_scent_woody")
    kb.button(text="🔥 Восточные", callback_data="cat_scent_oriental")
    kb.button(text="🍓 Фруктовые", callback_data="cat_scent_fruity")

    kb.adjust(2, 1, 1, 2, 2)
    return kb.as_markup()

# Клавиатура для выбора типа поиска

def favorites_keyboard(index: int, total: int, uid: int):
    items = [p for p in perfumes if p["id"] in user_favorites.get(uid, set())]
    perfume = items[index]

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️", callback_data=f"fav_prev_{index}")
    kb.button(text=f"{index+1}/{total}", callback_data="noop")
    kb.button(text="➡️", callback_data=f"fav_next_{index}")
    kb.button(text="❌ Удалить", callback_data=f"fav_remove:{perfume['id']}:favorites:{index}")
    kb.adjust(3, 1)

    return kb.as_markup()

@dp.callback_query(F.data.regexp(r"^fav_(prev|next)_\d+$"))
async def fav_navigation(callback: CallbackQuery):
    uid = callback.from_user.id
    action, index = callback.data.split("_")[1:]
    index = int(index)

    items = [p for p in perfumes if p["id"] in user_favorites.get(uid, [])]

    if not items:
        await callback.answer()
        return

    if action == "next" and index < len(items) - 1:
        index += 1
    elif action == "prev" and index > 0:
        index -= 1

    perfume = items[index]

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=FSInputFile(perfume["photo"]),
            caption=f"<b>{perfume['name']}</b>",
            parse_mode="HTML"
        ),
        reply_markup=favorites_keyboard(index, len(items), uid)
    )

    await callback.answer()


@dp.message(F.text == "⭐ Избранное")
async def show_favorites(message: Message):
    uid = message.from_user.id
    fav_ids = list(user_favorites.get(uid, set()))

    if not fav_ids:
        await message.answer("😔 У вас пока нет избранных ароматов")
        return

    index = 0
    perfume = next(p for p in perfumes if p["id"] == fav_ids[index])

    framed_photo = await resize_photo(perfume["photo"])
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {perfume['category']}\n"
        f"Объём: {perfume['volume']}"
    )

    await message.answer_photo(
        photo=framed_photo,
        caption=caption,
        reply_markup=favorites_keyboard(index, len(fav_ids), uid),
        parse_mode="HTML"
    )

"""
@dp.callback_query_handler(lambda c: c.data.startswith("fav_page:"))
async def favorites_page(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    await show_favorites(call.message, call.from_user.id, page)
"""
@dp.callback_query(F.data.startswith("fav_add:"))
async def fav_add(callback: CallbackQuery, state: FSMContext):
    _, perfume_id, source, index = callback.data.split(":")
    perfume_id = int(perfume_id)
    index = int(index)
    uid = callback.from_user.id

    user_favorites.setdefault(uid, set()).add(perfume_id)

    await update_fav_keyboard(callback, state, source, index, uid)
    await callback.answer("⭐ Добавлено в избранное")



@dp.callback_query(F.data.startswith("fav_remove:"))
async def fav_remove(callback: CallbackQuery, state: FSMContext):
    _, perfume_id, source, index = callback.data.split(":")
    perfume_id = int(perfume_id)
    index = int(index)
    uid = callback.from_user.id

    user_favorites.get(uid, set()).discard(perfume_id)

    # если удаляем из раздела "Избранное"
    if source == "favorites":
        items = [p for p in perfumes if p["id"] in user_favorites.get(uid, set())]

        if not items:
            await callback.message.edit_caption(
                caption="😔 У вас больше нет избранных ароматов",
                reply_markup=None
            )
            await callback.answer("Избранное пусто")
            return

        index = min(index, len(items) - 1)
        perfume = items[index]

        framed_photo = await resize_photo(perfume["photo"])

        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=framed_photo,
                caption=f"<b>{perfume['name']}</b>",
                parse_mode="HTML"
            ),
            reply_markup=favorites_keyboard(index, len(items), uid)
        )

        await callback.answer("❌ Удалено из избранного")
        return

    # остальные источники (catalog / search / category)
    await update_fav_keyboard(callback, state, source, index, uid)
    await callback.answer("❌ Удалено из избранного")



async def update_fav_keyboard(callback, state: FSMContext, source, index, uid):
    if source == "catalog":
        markup = catalog_card_keyboard(index, uid)

    elif source == "category":
        data = await state.get_data()
        items = data.get("cat_items", [])
        prefix = data.get("back_prefix", "gender")

        markup = category_card_keyboard(
            index,
            len(items),
            prefix,
            items[index],
            uid
        )

    elif source == "search":
        data = await state.get_data()
        results = data.get("search_results", [])

        markup = search_card_keyboard(
            index,
            len(results),
            uid,
            results[index]
        )

    else:
        return

    await callback.message.edit_reply_markup(reply_markup=markup)


@dp.message(F.text == "📦 Посмотреть весь каталог")
async def catalog_start(message: Message):
    perfume = perfumes[0]

    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(perfume["photo"], 
                                     border_radius=20, 
                                     shadow_offset=4)
    
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {perfume['category']}\n"  
        f"Объём: {perfume['volume']}\n"  
    )

    await message.answer_photo(
        photo=framed_photo,
        caption=caption,
        reply_markup=catalog_card_keyboard(0, message.from_user.id),
        parse_mode="HTML"
    )
def back_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="back")
    return kb.as_markup()

# Функции поиска
def search_perfumes_by_name(query: str):
    query = query.lower()
    return [
        p for p in perfumes
        if query in p["name"].lower()
    ]

def search_card_keyboard(index: int, total: int, telegram_id: int, perfume):
    
    fav_text, fav_cb = favorite_button(telegram_id,perfume["id"],source="search",index=index)

    kb = InlineKeyboardBuilder()

    kb.button(text="⬅️", callback_data=f"search_prev_{index}")
    kb.button(text=f"{index+1}/{total}", callback_data="noop")
    kb.button(text="➡️", callback_data=f"search_next_{index}")

    kb.button(
    text="ℹ️ Подробнее",callback_data=f"search_open_{index}")
    kb.button(text=fav_text, callback_data=fav_cb)

    kb.adjust(3, 1, 1)
    return kb.as_markup()


@dp.message(F.text == "/start")
async def start(message: Message):
    text = """🌸 <b>Добро пожаловать в мир изысканных ароматов!</b> 🌸
Вы любите качественный парфюм, но не готовы переплачивать? У Нас — идеальное решение: премиальные ароматы, но по приятной цене. А также нишевая линейка ароматов от известного бренда.

<b>Почему Наши ароматы — Ваш лучший выбор?</b>
Ароматы созданы известными парфюмерами по мотивам известных брендов. Тот же характер, те же ноты, тот же шарм.

<b>Качественный состав</b> — используем проверенные парфюмерные компоненты, безопасные и стойкие.
Имеются все сертификаты качества и "честный знак".

<b>Отличная стойкость</b> — ароматы держат положенное время и более, не теряя глубины и шлейфа.

<b>Доступная цена!</b> Мы отказались от дорогостоящей коммерческой рекламы, для того чтобы Вы могли  экономить до 90 % по сравнению с ценами на люксовые бренды.
<b>Отличный шанс обрести роскошный парфюм без переплат!</b>

Ниже для Вас доступен просмотр всего каталога - более 50ти ароматов; категории ароматов и поиск по совпадению слов."""
    #user_id = auth_user(message)
    #await track(message.from_user.id, "bot_start")
    await message.answer(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    text = """🌸 <b>Добро пожаловать в мир изысканных ароматов!</b> 🌸
Вы любите качественный парфюм, но не готовы переплачивать? У Нас — идеальное решение: премиальные ароматы, но по приятной цене. А также нишевая линейка ароматов от известного бренда.

<b>Почему Наши ароматы — Ваш лучший выбор?</b>
Ароматы созданы известными парфюмерами по мотивам известных брендов. Тот же характер, те же ноты, тот же шарм.

<b>Качественный состав</b> — используем проверенные парфюмерные компоненты, безопасные и стойкие.
Имеются все сертификаты качества и "честный знак".

<b>Отличная стойкость</b> — ароматы держат положенное время и более, не теряя глубины и шлейфа.

<b>Доступная цена!</b> Мы отказались от дорогостоящей коммерческой рекламы, для того чтобы Вы могли  экономить до 90 % по сравнению с ценами на люксовые бренды.
<b>Отличный шанс обрести роскошный парфюм без переплат!</b>

Ниже для Вас доступен просмотр всего каталога - более 50ти ароматов; категории ароматов и поиск по совпадению слов."""
    
    await callback.message.answer(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(Command("catalog"))
async def catalog_command(message: Message):
    kb = InlineKeyboardBuilder()
    for p in perfumes:
        kb.button(text=p["name"], callback_data=f"perf_{p['id']}")
    kb.adjust(1)

    await message.answer(
        "📦 <b>Весь каталог:</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )



@dp.message(Command("categories"))
async def show_categories_command(message: Message):
    await message.answer(
        "📂 В данном разделе Вы сможете выбрать нужную категорию ароматов:",
        reply_markup=categories_keyboard()
    )

# Обработчики выбора типа поиска
"""
@dp.callback_query(F.data == "search_by_name")
async def search_by_name_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await callback.message.edit_text("Поиск по названию Вашего любимого аромата известного бренда либо по названию аромата нашего бренда. Введите название:")
    await callback.answer()
"""

@dp.callback_query(F.data.startswith("cat_gender_"))
async def show_gender_category_handler(callback: CallbackQuery, state: FSMContext):
    gender_type = callback.data.replace("cat_gender_", "")
    
    # Маппинг callback-данных на значения категорий
    gender_map = {
        "women": "для неё",
        "men": "для него", 
        "unisex": "унисекс"
    }
    
    target_gender = gender_map.get(gender_type)
    if not target_gender:
        await callback.answer("Неизвестная категория")
        return
    
    # Фильтрация по category2 (списку категорий)
    items = []
    for p in perfumes:
        categories = p.get("category2", [])
        
        # Обрабатываем разные форматы category2
        if isinstance(categories, str):
            # Если строка - преобразуем в список с одним элементом
            if categories == target_gender:
                items.append(p)
        elif isinstance(categories, list):
            # Если список - проверяем наличие
            if target_gender in categories:
                items.append(p)
        # Для обратной совместимости: если category2 не определено или пусто, используем category
        else:
            if p.get("category") == target_gender:
                items.append(p)
    
    if not items:
        await callback.message.answer("😔 В этой категории пока нет товаров")
        await callback.answer()
        return
    
    await state.update_data(
        cat_items=items,
        cat_index=0,
        cat_type="gender"
    )
    
    perfume = items[0]
    
    # Формируем список категорий для отображения
    categories = []
    category2 = perfume.get("category2", [])
    
    if isinstance(category2, str):
        categories = [category2]  # Превращаем строку в список
    elif isinstance(category2, list):
        categories = category2
    elif not category2:
        categories = [perfume.get("category", "не указано")]
    
    # ФИКС: Проверяем, что categories действительно список
    print(f"DEBUG: categories type = {type(categories)}, value = {categories}")
    
    # Добавляем информацию о поле и объеме
    if isinstance(categories, list) and len(categories) > 0:
        # Если это список, соединяем элементы через запятую
        categories_text = ", ".join(categories)
    else:
        # Если по какой-то причине не список, просто выводим как есть
        categories_text = str(categories)
    
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {categories_text}\n"
        f"Объём: {perfume.get('volume', 'не указано')}"
    )
    
    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(perfume["photo"], 
                                     max_size=(800, 800), 
                                     border_radius=20, 
                                     shadow_offset=8)
    
    await callback.message.answer_photo(
        photo=framed_photo,
        caption=caption,
        reply_markup=category_card_keyboard(
    0,
    len(items),
    "gender",
    perfume,
    callback.from_user.id
),

        parse_mode="HTML"
    )
    
    await callback.answer()

@dp.callback_query(F.data.regexp(r"^(gender|scent)_(prev|next)_\d+$"))
async def category_navigation_handler(callback: CallbackQuery, state: FSMContext):
    prefix, direction, current = callback.data.split("_")
    current = int(current)
    telegram_id = callback.from_user.id
    data = await state.get_data()
    items = data.get("cat_items", [])
    
    if not items:
        await callback.answer("Данные не найдены")
        return

    if direction == "next" and current < len(items) - 1:
        index = current + 1
    elif direction == "prev" and current > 0:
        index = current - 1
    else:
        await callback.answer()
        return

    await state.update_data(
    back_view="category",
    back_index=index,
    back_items=items,
    back_prefix=prefix
)
    perfume = items[index]
    
    # Формируем список категорий для отображения
    categories = []
    category2 = perfume.get("category2", [])
    
    if isinstance(category2, str):
        categories = [category2]
    elif isinstance(category2, list):
        categories = category2
    elif not category2:
        categories = [perfume.get("category", "не указано")]
    
    # Формируем текст категорий
    if isinstance(categories, list) and len(categories) > 0:
        categories_text = ", ".join(categories)
    else:
        categories_text = str(categories)
    
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {categories_text}\n"
        f"Объём: {perfume.get('volume', 'не указано')}"
    )

    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(
        perfume["photo"], 
        max_size=(800, 800), 
        border_radius=20, 
        shadow_offset=8
    )

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=framed_photo,
            caption=caption,
            parse_mode="HTML"
        ),
        reply_markup=category_card_keyboard(index,len(items),prefix,perfume,telegram_id)
    )

    await callback.answer()

@dp.message(F.text == "📂 Категории")
async def show_categories(message: Message):
    await message.answer(
        "📂 В данном разделе Вы сможете выбрать нужную категорию ароматов:",
        reply_markup=categories_keyboard()
    )

def catalog_card_keyboard(index: int, telegram_id: int):
    perfume = perfumes[index]
    fav_text, fav_cb = favorite_button(telegram_id,perfume["id"],source="catalog",index=index)

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️", callback_data=f"nav_prev_{index}")
    kb.button(text=f"{index+1}/{len(perfumes)}", callback_data="noop")
    kb.button(text="➡️", callback_data=f"nav_next_{index}")

    kb.button(text="ℹ️ Подробнее", callback_data=f"perf_{perfume['id']}")
    kb.button(text=fav_text, callback_data=fav_cb)
    
    kb.adjust(3, 1, 1)

    return kb.as_markup()


@dp.callback_query(F.data.startswith("perf_"))
async def show_perfume(callback: CallbackQuery, state: FSMContext):
    perfume_id = int(callback.data.replace("perf_", ""))
    perfume_index = next(i for i, p in enumerate(perfumes) if p["id"] == perfume_id)
    perfume = perfumes[perfume_index]

    # 🔐 сохраняем, откуда пришли
    await state.update_data(
        back_view="catalog",
        catalog_index=perfume_index
    )

    # 📸 ОДИН раз отправляем photo2 и сохраняем message_id
    photo_msg = await callback.message.answer_photo(
        photo=FSInputFile(perfume["photo2"])
    )

    await state.update_data(order_photo_id=photo_msg.message_id)

    # 📝 длинное описание отдельным сообщением
    await callback.message.answer(
        f"<b>Описание:</b>\n{perfume['description']}",
        reply_markup=order_keyboard("catalog", perfume_index),
        parse_mode="HTML"
    )

    await callback.answer()



@dp.callback_query(F.data.regexp(r"^search_(prev|next)_\d+$"))
async def search_navigation(callback: CallbackQuery, state: FSMContext):
    _, direction, current = callback.data.split("_")
    current = int(current)

    data = await state.get_data()
    results = data["search_results"]
    index = data["search_index"]

    if direction == "next" and current < len(results) - 1:
        index = current + 1
    elif direction == "prev" and current > 0:
        index = current - 1
    else:
        await callback.answer()
        return

    await state.update_data(
    search_index=index,
    back_view="search",
    back_index=index,
    back_results=results
)

    perfume = results[index]
    
    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(perfume["photo"], 
                                     max_size=(800, 800), 
                                     border_radius=20, 
                                     shadow_offset=8)
    
    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=framed_photo,
            caption=(
                f"<b>{perfume['name']}</b>\n"
                f"Пол: {perfume.get('category', 'не указано')}\n"
                f"Объём: {perfume.get('volume', 'не указано')}\n"
            ),
            parse_mode="HTML"
        ),
            reply_markup=search_card_keyboard(
        index,
        len(results),
        callback.from_user.id,
        perfume
    )
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("search_open_"))
async def search_open(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[-1])

    data = await state.get_data()
    results = data["search_results"]
    perfume = results[index]

    await state.update_data(
        back_view="search",
        back_index=index
    )
    photo_msg = await callback.message.answer_photo(
    photo=FSInputFile(perfume["photo2"])
)
    await state.update_data(order_photo_id=photo_msg.message_id)


    await callback.message.answer(
        f"<b>Описание:</b>\n{perfume.get('description','')}",
        reply_markup=order_keyboard("search", index),
        parse_mode="HTML"
    )

    await callback.answer()



# Обработчики поиска по разным типам
@dp.message(SearchState.waiting_query)
async def search_by_name_handler(message: Message, state: FSMContext):
    query = message.text.lower().strip()
    results = search_perfumes_by_name(query)

    if not results:
        await message.answer(
        """😔 Ничего не найдено попробуйте еще раз:\n 
Поиск по названию Вашего любимого аромата известного бренда либо по названию аромата нашего бренда. Введите название:"""
    )
    # состояние НЕ очищаем

    if len(results) == 0:
        return
    perfume = results[0]
    await state.update_data(
        search_results=results,
        search_index=0,
        search_type="name",
        search_query=query
    )

    
    await state.set_state(SearchState.waiting_query)
    framed_photo = await resize_photo(perfume["photo"])

    await message.answer_photo(
        photo=framed_photo,
        caption=(
            f"<b>{perfume['name']}</b>\n"
            f"Пол: {perfume.get('category', 'не указано')}\n"
            f"Объём: {perfume.get('volume', 'не указано')}"
        ),
            reply_markup=search_card_keyboard(
        0,
        len(results),
        message.from_user.id,
        perfume
    ),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.answer(
        "В данном разделе Вы сможете выбрать нужную категорию ароматов:",
        reply_markup=categories_keyboard()
    )

@dp.message(F.text == "🔍 Поиск")
async def search_reply(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await message.answer(
        "Поиск по названию Вашего любимого аромата известного бренда либо по названию аромата нашего бренда. Введите название:"
    )


@dp.callback_query(F.data.regexp(r"^(gender|scent)_(prev|next)_\d+$"))
async def category_navigation_handler(callback: CallbackQuery, state: FSMContext):
    prefix, direction, current = callback.data.split("_")
    current = int(current)

    data = await state.get_data()
    items = data.get("cat_items", [])
    
    if not items:
        await callback.answer("Данные не найдены")
        return

    if direction == "next" and current < len(items) - 1:
        index = current + 1
    elif direction == "prev" and current > 0:
        index = current - 1
    else:
        await callback.answer()
        return

    await state.update_data(
    back_view="category",
    back_index=index,
    back_items=items,
    back_prefix=prefix
)
    perfume = items[index]
    
    # Добавляем информацию о поле и объеме
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {perfume.get('category', 'не указано')}\n"
        f"Объём: {perfume.get('volume', 'не указано')}"
    )

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=FSInputFile(perfume["photo"]),
            caption=caption,
            parse_mode="HTML"
        ),
        reply_markup=category_card_keyboard(index, len(items), prefix, perfume)
    )

    await callback.answer()

@dp.callback_query(F.data.regexp(r"^nav_(prev|next)_\d+$"))
async def catalog_navigation(callback: CallbackQuery):
    parts = callback.data.split("_")
    
    if len(parts) != 3:
        await callback.answer("Неверный формат данных")
        return
    
    direction = parts[1]
    index = int(parts[2])

    if direction == "next" and index < len(perfumes) - 1:
        index += 1
    elif direction == "prev" and index > 0:
        index -= 1
    else:
        await callback.answer()
        return

    perfume = perfumes[index]
    
    # Используем фото со стильной рамкой
    framed_photo = await resize_photo(perfume["photo"],  
                                     border_radius=20, 
                                     shadow_offset=4)

    media = InputMediaPhoto(
        media=framed_photo,
        caption=(
            f"<b>{perfume['name']}</b>\n"
            f"Пол: {perfume['category']}\n"
            f"Объём: {perfume['volume']}\n"
        ),
        parse_mode="HTML"
    )

    await callback.message.edit_media(
        media=media,
        reply_markup=catalog_card_keyboard(index=index,
        telegram_id=callback.from_user.id)
    )

    await callback.answer()

@dp.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()

def category_card_keyboard(index: int, total: int, prefix: str, perfume, telegram_id: int):
    kb = InlineKeyboardBuilder()

    # Навигация
    kb.button(text="⬅️", callback_data=f"{prefix}_prev_{index}")
    kb.button(text=f"{index+1}/{total}", callback_data="noop")
    kb.button(text="➡️", callback_data=f"{prefix}_next_{index}")

    # Подробнее
    kb.button(
        text="ℹ️ Подробнее",
        callback_data=f"cat_open_{prefix}_{index}"
    )
    fav_text, fav_cb = favorite_button(telegram_id,perfume["id"],source="category",index=index)

    kb.button(text=fav_text, callback_data=fav_cb)
    kb.adjust(3, 1, 1)
    return kb.as_markup()


@dp.callback_query(F.data.startswith("cat_scent_"))
async def show_scent_category_handler(callback: CallbackQuery, state: FSMContext):
    scent_map = {
        "floral": "цветочные",
        "citrus": "цитрусовые",
        "niche":"нишевые",
        "woody": "древесные",
        "oriental": "восточные",
        "fruity": "фруктовые",
    }

    key = callback.data.removeprefix("cat_scent_").strip().lower()

    if key not in scent_map:
        await callback.answer(f"❌ Неизвестная категория: {key}")
        return

    category = scent_map[key]
    category_lower = category.casefold()
    
    items = []
    for p in perfumes:
        scent_data = p.get("scent_category", "")
        if isinstance(scent_data, str):
            if category_lower in scent_data.casefold():
                items.append(p)
        elif isinstance(scent_data, list):
            for scent_item in scent_data:
                if isinstance(scent_item, str) and category_lower in scent_item.casefold():
                    items.append(p)
                    break  

    if not items:
        await callback.message.answer("😔 В этой категории пока нет товаров")
        await callback.answer()
        return

    await state.update_data(cat_items=items, cat_index=0)

    perfume = items[0]
    
    # Добавляем информацию о поле и объеме
    caption = (
        f"<b>{perfume['name']}</b>\n"
        f"Пол: {perfume.get('category', 'не указано')}\n"
        f"Объём: {perfume.get('volume', 'не указано')}"
    )

    await callback.message.answer_photo(
        photo=FSInputFile(perfume["photo"]),
        caption=caption,
        reply_markup=category_card_keyboard(
    0,
    len(items),
    "scent",
    perfume,
    callback.from_user.id
),

        parse_mode="HTML",
    )

    await callback.answer()

@dp.callback_query(F.data.startswith("cat_open_"))
async def category_open(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")

    # 🛡 защита
    if len(parts) < 4:
        await callback.answer("Ошибка навигации", show_alert=True)
        return

    category_type = parts[2]
    index = int(parts[3])

    data = await state.get_data()
    items = data.get("cat_items", [])

    if index < 0 or index >= len(items):
        await callback.answer("Товар не найден", show_alert=True)
        return

    perfume = items[index]

    await state.update_data(
        back_view="category",
        back_items=items,
        back_index=index,
        back_prefix=category_type
    )
    photo_msg = await callback.message.answer_photo(
    photo=FSInputFile(perfume["photo2"])
)  
    await state.update_data(order_photo_id=photo_msg.message_id)


    perfume_index = next(
        (i for i, p in enumerate(perfumes) if p["id"] == perfume["id"]),
        0
    )

    await callback.message.answer(
        f"<b>Описание:</b>\n{perfume.get('description','')}",
        reply_markup=order_keyboard("category", index),
        parse_mode="HTML"
    )

    await callback.answer()


async def main():
    await bot.set_my_commands([])
    await bot.set_chat_menu_button(
        menu_button=MenuButtonDefault()
    )
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())