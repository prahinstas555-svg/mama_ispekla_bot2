from groq import Groq
from config import AI_API_KEY
import asyncio
import logging
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    WebAppInfo,
    CallbackQuery,
)

from config import BOT_TOKEN, WEBAPP_URL, MANAGER_ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------- ИИ-КОНСУЛЬТАНТ (Groq) ----------
groq_client = Groq(api_key=AI_API_KEY)

SYSTEM_PROMPT = """
Ты — дружелюбный ИИ-консультант пекарни-кондитерской «Мама Испекла» в Симферополе.
Общайся тепло, уютно, с любовью — как семейная пекарня. Можно использовать эмодзи 🥐🍰🥖, но в меру.
Отвечай кратко и по делу, на русском языке. Если не знаешь точную цену — предложи связаться с менеджером.

ВОТ ЧТО ТЫ ЗНАЕШЬ О ПЕКАРНЕ:

О НАС:
Семейная пекарня. Весь хлеб готовим только на живой закваске!
Ручной способ приготовления хлеба, булочек, пирожков, печенья и тортов.
Только свежие и натуральные продукты. Никаких улучшителей, красителей и консервантов.
Команда профессиональных пекарей и кондитеров, любящих своё дело.

АДРЕСА (Симферополь):
- ул. Жуковского, 10
- бул. Ивана Франко, 24

ЦЕНЫ:
- Средний чек за порцию десерта и кофе: 200–250 ₽
- Панеттоне и куличи на закваске (сезон): 350–550 ₽ за штуку
- Целые торты под заказ: цена индивидуально, зависит от начинки и декора
- Ориентировочная цена торта: от 1500 ₽/кг

ДОСТАВКА:
- Собственная курьерская служба по всему Симферополю
- При заказе от 1000 ₽ — доставка бесплатная
- Бесплатный самовывоз любого заказа

СРОКИ ЗАКАЗА ТОРТОВ:
- Классический торт к празднику: минимум за 3–5 дней
- Сложные/свадебные/многоярусные торты: минимум за 7–10 дней

МЕНЮ:
🍰 Торты и десерты:
- Торт «Карамельно-Маковый» (хит)
- Торт «Чёрный лес» (шоколадно-вишнёвый)
- Торт «Сникерс» (арахис и домашняя карамель)
- Торт «Красный бархат» (с крем-чизом)
- Бенто-торты (с надписями и рисунками под заказ)
- Муссовые пирожные
- Капкейки и трайфлы

🥐 Сладкая выпечка:
- Круассаны классические и с начинками
- Даниши и улитки с сезонными ягодами
- Синнабоны

🍞 Хлеб на закваске:
- Тартин, Ржано-пшеничный, Бородинский, Багеты

🥪 Сытная выпечка:
- Сэндвич «Цыплёнок-Бекон»
- Римская пицца «4 сыра»
- Пироги

ВАЖНО:
- Для оформления заказа предлагай нажать кнопку «🛍 Открыть магазин» внизу.
- Если спрашивают то, чего ты не знаешь — вежливо предложи уточнить у менеджера.
"""

# ---------- FSM СОСТОЯНИЯ для "Помощь к событию" ----------
class EventHelper(StatesGroup):
    waiting_event = State()    # Шаг 1: тип события
    waiting_guests = State()   # Шаг 2: количество гостей
    waiting_budget = State()   # Шаг 3: бюджет


# ---------- НИЖНЯЯ КНОПКА МАГАЗИНА (reply) ----------
def shop_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🛍 Открыть магазин",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )


# ---------- ГЛАВНОЕ МЕНЮ (inline) ----------
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 ИИ-консультант 24/7 — задай вопрос!",
                    callback_data="ai_consultant"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎉 Помощь к событию",
                    callback_data="event_helper"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 Адрес и контакты",
                    callback_data="contacts"
                )
            ],
        ]
    )


# ---------- КНОПКИ ВЫБОРА СОБЫТИЯ ----------
def event_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎂 День рождения", callback_data="event_birthday")],
            [InlineKeyboardButton(text="💍 Свадьба",       callback_data="event_wedding")],
            [InlineKeyboardButton(text="🏢 Корпоратив",    callback_data="event_corporate")],
            [InlineKeyboardButton(text="🎓 Выпускной",     callback_data="event_graduation")],
            [InlineKeyboardButton(text="🎊 Другое",        callback_data="event_other")],
        ]
    )


# ---------- /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()  # сбрасываем любой FSM при старте

    caption = (
        "👋 Добро пожаловать в <b>«Мама Испекла»</b>! 🍰\n\n"
        "🥐 Здесь живёт настоящая домашняя выпечка — "
        "та самая, от которой щемит сердце и "
        "хочется съесть ещё кусочек...\n\n"
        "✨ <b>Мы готовим с любовью:</b>\n"
        "🍞 Хлеб на живой закваске\n"
        "🥐 Хрустящие круассаны и булочки\n"
        "🎂 Торты на любой праздник\n"
        "💝 Бенто-торты с вашими пожеланиями\n\n"
        "🌿 Только натуральные продукты — "
        "никакой химии и консервантов!\n\n"
        "👇 Загляните в каталог — "
        "уверены, вы найдёте что-то особенное!"
    )

    await message.answer_photo(
        photo="https://i.ibb.co/nNHnqHSd/0188ba339143fa0e27abfc92bf635f14-9b9a98d8-327f-4c77-a570-69b306e6cb8e.png",
        caption=caption,
        reply_markup=shop_keyboard(),
        parse_mode="HTML"
    )

    await message.answer(
        "Также вам доступно 👇",
        reply_markup=main_menu()
    )


# ---------- КОНТАКТЫ ----------
@dp.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "📍 <b>Мама Испекла</b>\n\n"
        "Адрес: г. Симферополь, Бульвар Франко, 24\n"
        "Телефон: +7 978 735-30-07\n"
        "Часы работы: 08:00 – 23:00\n"
        "Сайт: mama-ispekla.ru"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# ---------- ИИ-КОНСУЛЬТАНТ ----------
@dp.callback_query(F.data == "ai_consultant")
async def ai_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "🤖 Я ваш ИИ-консультант пекарни «Мама Испекла»! 🥐\n\n"
        "Спросите меня о тортах, доставке, ценах или сроках заказа — "
        "просто напишите вопрос сообщением. ✍️"
    )
    await callback.answer()


# ======================================================
# ---------- 🎉 ПОМОЩЬ К СОБЫТИЮ (FSM) ----------
# ======================================================

@dp.callback_query(F.data == "event_helper")
async def event_helper_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EventHelper.waiting_event)
    await callback.message.answer(
        "🎉 <b>Помощник по подбору торта к событию!</b>\n\n"
        "Я помогу подобрать идеальный торт, "
        "рассчитаю нужный вес и примерную стоимость.\n\n"
        "Шаг 1️⃣ — <b>Какое у вас событие?</b>",
        reply_markup=event_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# Шаг 1: получаем тип события
@dp.callback_query(F.data.startswith("event_"))
async def event_type_chosen(callback: CallbackQuery, state: FSMContext):
    event_map = {
        "event_birthday":   "🎂 День рождения",
        "event_wedding":    "💍 Свадьба",
        "event_corporate":  "🏢 Корпоратив",
        "event_graduation": "🎓 Выпускной",
        "event_other":      "🎊 Другое",
    }
    event_name = event_map.get(callback.data, "Праздник")
    await state.update_data(event=event_name)
    await state.set_state(EventHelper.waiting_guests)

    await callback.message.answer(
        f"Отлично! <b>{event_name}</b> — это будет незабываемо! 🥳\n\n"
        "Шаг 2️⃣ — <b>Сколько примерно будет гостей?</b>\n"
        "Просто напишите число, например: <i>15</i>",
        parse_mode="HTML"
    )
    await callback.answer()


# Шаг 2: получаем количество гостей
@dp.message(EventHelper.waiting_guests)
async def event_guests(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, напишите число гостей цифрами, например: <b>20</b>", parse_mode="HTML")
        return

    guests = int(message.text)
    await state.update_data(guests=guests)
    await state.set_state(EventHelper.waiting_budget)

    await message.answer(
        f"👥 <b>{guests} гостей</b> — понял!\n\n"
        "Шаг 3️⃣ — <b>Какой у вас примерный бюджет на торт?</b>\n"
        "Напишите сумму в рублях, например: <i>5000</i>\n\n"
        "Или напишите <b>любой</b> если бюджет не ограничен 🙌",
        parse_mode="HTML"
    )


# Шаг 3: получаем бюджет → считаем → выдаём рекомендацию через ИИ
@dp.message(EventHelper.waiting_budget)
async def event_budget(message: Message, state: FSMContext):
    budget_text = message.text.strip()
    data = await state.get_data()
    event = data.get("event", "праздник")
    guests = data.get("guests", 10)

    # Рассчитываем вес торта (норма: 150г на человека)
    weight_kg = round(guests * 0.15, 1)
    # Минимум 1 кг
    if weight_kg < 1:
        weight_kg = 1.0

    # Формируем запрос к ИИ
    user_query = (
        f"Мне нужна помощь с выбором торта. "
        f"Событие: {event}. "
        f"Количество гостей: {guests}. "
        f"Бюджет: {budget_text} рублей. "
        f"Рассчитанный вес торта: {weight_kg} кг (по 150г на гостя). "
        f"Порекомендуй 1-2 торта из меню, объясни почему они подойдут, "
        f"укажи примерную стоимость исходя из бюджета, "
        f"и предложи что-то дополнительное (капкейки, пирожные) если бюджет позволяет. "
        f"Напомни про сроки заказа."
    )

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            temperature=0.7,
            max_tokens=700,
        )
        ai_answer = response.choices[0].message.content
    except Exception as e:
        print("Ошибка Groq:", e)
        ai_answer = "😔 Не удалось получить рекомендацию. Пожалуйста, обратитесь к менеджеру."

    # Итоговое сообщение
    result_text = (
        f"🎉 <b>Ваша подборка для события «{event}»</b>\n\n"
        f"👥 Гостей: <b>{guests}</b>\n"
        f"⚖️ Рекомендуемый вес торта: <b>{weight_kg} кг</b>\n"
        f"💰 Бюджет: <b>{budget_text} ₽</b>\n\n"
        f"{'─' * 25}\n\n"
        f"{ai_answer}\n\n"
        f"{'─' * 25}\n"
        f"👇 Готовы заказать? Нажмите <b>«🛍 Открыть магазин»</b> "
        f"или свяжитесь с менеджером!"
    )

    await message.answer(result_text, parse_mode="HTML")

    # Показываем главное меню снова
    await message.answer(
        "Также вам доступно 👇",
        reply_markup=main_menu()
    )

    # Сбрасываем состояние
    await state.clear()


# ======================================================
# ---------- ПРИЁМ ЗАКАЗА ИЗ WEB APP ----------
# ======================================================
@dp.message(F.web_app_data)
async def web_app_order(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        await message.answer("⚠️ Не удалось прочитать заказ. Попробуйте ещё раз.")
        return

    items   = data.get("items", [])
    total   = data.get("total", 0)
    name    = data.get("name", "—")
    phone   = data.get("phone", "—")
    comment = data.get("comment", "—")

    lines = ""
    for it in items:
        title    = it.get("name", "Товар")
        qty      = it.get("qty", 1)
        price    = it.get("price", 0)
        item_sum = it.get("sum", price * qty)
        lines   += f"• {title} × {qty} — {item_sum} ₽\n"

    user = message.from_user

    manager_text = (
        "🛒 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"{lines}\n"
        f"💰 <b>Итого: {total} ₽</b>\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"💬 Комментарий: {comment}\n\n"
        f"🆔 От: @{user.username or '—'} (id {user.id})"
    )
    await bot.send_message(MANAGER_ID, manager_text, parse_mode="HTML")

    await message.answer(
        "✅ <b>Спасибо за заказ!</b>\n\n"
        f"{lines}\n"
        f"💰 Итого: <b>{total} ₽</b>\n\n"
        "Менеджер скоро свяжется с вами для подтверждения. 💙",
        parse_mode="HTML",
    )


# ======================================================
# ---------- ОБРАБОТКА ТЕКСТА → ИИ-КОНСУЛЬТАНТ ----------
# ======================================================
@dp.message(F.text)
async def ai_consultant(message: Message, state: FSMContext):
    if message.text.startswith("/"):
        return

    # Если активен FSM — не перехватываем
    current_state = await state.get_state()
    if current_state is not None:
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text},
            ],
            temperature=0.6,
            max_tokens=600,
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        print("Ошибка Groq:", e)
        await message.answer(
            "😔 Извините, консультант сейчас недоступен. "
            "Попробуйте позже или нажмите «🛍 Открыть магазин»."
        )


# ---------- ЗАПУСК ----------
async def main():
    print("Бот запущен ✅")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
