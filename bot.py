from groq import Groq
from config import AI_API_KEY
import asyncio
import logging
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

from config import BOT_TOKEN, WEBAPP_URL, MANAGER_ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- ИИ-КОНСУЛЬТАНT (Groq) ----------
groq_client = Groq(api_key=AI_API_KEY)

# "Характер" и знания консультанта
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

ДОСТАВКА:
- Собственная курьерская служба по всему Симферополю
- При заказе от 1000 ₽ — доставка бесплатная
- Минимальный заказ для бесплатной доставки: 1000 ₽
- Бесплатный самовывоз любого заказа
- В самой кондитерской можно купить хоть один кусочек, без ограничений

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
- Муссовые пирожные (вкусы меняются каждую неделю)
- Капкейки и трайфлы (ягодные, шоколадные, карамельные)

🥐 Сладкая выпечка:
- Круассаны классические
- Круассаны с начинками (миндаль, шоколад, заварной крем, солёная карамель)
- Даниши и улитки с сезонными ягодами
- Синнабоны (с корицей и крем-чизом)

🍞 Хлеб на закваске:
- Тартин (пшеничный)
- Ржано-пшеничный (с семечками/солодом)
- Бородинский заварной
- Багеты французские

🥪 Сытная выпечка:
- Сэндвич «Цыплёнок-Бекон»
- Римская пицца «4 сыра» (30 см и 40 см)
- Пироги (курица/грибы, мясо, сыр/зелень)

ВАЖНО:
- Для оформления заказа предлагай нажать кнопку «🛍 Открыть магазин» внизу.
- Если спрашивают то, чего ты не знаешь — вежливо предложи уточнить у менеджера.
"""


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
                    text="🤖 ИИ-консультант 24/7 — задай вопрос!", callback_data="ai_consultant"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 Адрес и контакты", callback_data="contacts"
                )
            ],
        ]
    )


# ---------- /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message):
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
async def show_contacts(callback):
    text = (
        "📍 <b>Мама Испекла</b>\n\n"
        "Адрес: г. Симферополь, Бульвар Франко, 24\n"
        "Телефон: +7 978 735-30-07\n"
        "Часы работы: 08:00 – 23:00\n"
        "Сайт: mama-ispekla.ru"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# ---------- ЗАГЛУШКА ИИ (сделаем на Шаге 5) ----------
# ---------- КНОПКА ИИ-КОНСУЛЬТАНТА ----------
@dp.callback_query(F.data == "ai_consultant")
async def ai_start(callback):
    await callback.message.answer(
        "🤖 Я ваш ИИ-консультант пекарни «Мама Испекла»! 🥐\n\n"
        "Спросите меня о тортах, доставке, ценах или сроках заказа — "
        "просто напишите вопрос сообщением. ✍️"
    )
    await callback.answer()


# ---------- ПРИЁМ ЗАКАЗА ИЗ WEB APP ----------
@dp.message(F.web_app_data)
async def web_app_order(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        await message.answer("⚠️ Не удалось прочитать заказ. Попробуйте ещё раз.")
        return

    items = data.get("items", [])
    total = data.get("total", 0)
    name = data.get("name", "—")
    phone = data.get("phone", "—")
    comment = data.get("comment", "—")

    # Список позиций (берём name и sum — как присылает магазин)
    lines = ""
    for it in items:
        title = it.get("name", "Товар")
        qty = it.get("qty", 1)
        price = it.get("price", 0)
        item_sum = it.get("sum", price * qty)
        lines += f"• {title} × {qty} — {item_sum} ₽\n"

    user = message.from_user

    # --- Сообщение МЕНЕДЖЕРУ ---
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

    # --- Подтверждение КЛИЕНТУ ---
    await message.answer(
        "✅ <b>Спасибо за заказ!</b>\n\n"
        f"{lines}\n"
        f"💰 Итого: <b>{total} ₽</b>\n\n"
        "Менеджер скоро свяжется с вами для подтверждения. 💙",
        parse_mode="HTML",
    )

# ---------- ОБРАБОТКА ТЕКСТА → ИИ-КОНСУЛЬТАНT ----------
@dp.message(F.text)
async def ai_consultant(message: Message):
    # Игнорируем команды (они обрабатываются отдельно)
    if message.text.startswith("/"):
        return

    # Показываем "печатает..."
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
