import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN
from api_client import StarsAPI

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

api = StarsAPI()

# Состояния для FSM
class BuyStars(StatesGroup):
    waiting_for_username = State()
    waiting_for_amount = State()

# Клавиатура главного меню
def main_keyboard():
    kb = [
        [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy_stars")],
        [InlineKeyboardButton(text="👑 Подарить Premium", callback_data="gift_premium")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌟 Добро пожаловать в бота для покупки Telegram Stars!\n\n"
        "Выберите действие:",
        reply_markup=main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "info")
async def info_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "Бот позволяет покупать Telegram Stars и дарить Premium.\n"
        "Цена: 1 Star ≈ 0.01 TON (ориентировочно)\n\n"
        "Для покупки введите:\n"
        "1. Username получателя (например: @durov)\n"
        "2. Количество Stars (от 50 до 10 000 000)",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_stars")
async def buy_stars_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите <b>username</b> получателя (например: @durov):", parse_mode="HTML")
    await state.set_state(BuyStars.waiting_for_username)
    await callback.answer()

@dp.message(BuyStars.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        username = "@" + username
    
    await state.update_data(username=username)
    await message.answer("Введите <b>количество</b> Stars (от 50 до 10 000 000):", parse_mode="HTML")
    await state.set_state(BuyStars.waiting_for_amount)

@dp.message(BuyStars.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount < 50 or amount > 10_000_000:
            await message.answer("❌ Количество должно быть от 50 до 10 000 000. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")
        return

    data = await state.get_data()
    username = data.get("username")

    await message.answer(f"⏳ Покупаю {amount} Stars для {username}...")

    # Вызов API
    result = await api.buy_stars(username, amount)

    if result["success"]:
        tx_data = result["data"]
        req_id = tx_data.get("data", {}).get("req_id", "N/A")
        await message.answer(
            f"✅ <b>Успешно!</b>\n\n"
            f"⭐ {amount} Stars отправлены на {username}\n"
            f"🆔 ID транзакции: <code>{req_id}</code>\n"
            f"🔗 Подтверждение: {tx_data.get('data', {}).get('confirm_referer', '')}",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ Ошибка: {result['error']}")

    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_keyboard())

@dp.callback_query(lambda c: c.data == "gift_premium")
async def gift_premium_start(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3 месяца", callback_data="prem_3")],
        [InlineKeyboardButton(text="6 месяцев", callback_data="prem_6")],
        [InlineKeyboardButton(text="12 месяцев", callback_data="prem_12")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.answer(
        "👑 Выберите срок Premium для подарка:\n\n"
        "После выбора введите username получателя.",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("prem_"))
async def process_premium_selection(callback: types.CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    await state.update_data(premium_months=months)
    await callback.message.answer(f"Введите <b>username</b> получателя Premium на {months} месяцев:", parse_mode="HTML")
    await state.set_state(BuyStars.waiting_for_username)  # переиспользуем состояние
    await callback.answer()

@dp.message(BuyStars.waiting_for_username)
async def process_premium_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        username = "@" + username
    
    data = await state.get_data()
    months = data.get("premium_months")
    
    if not months:
        # Если это не Premium, а Stars — обрабатываем в другом хендлере
        await state.update_data(username=username)
        await message.answer("Введите количество Stars:")
        await state.set_state(BuyStars.waiting_for_amount)
        return

    await message.answer(f"⏳ Дарю Premium на {months} месяцев для {username}...")

    result = await api.gift_premium(username, months)

    if result["success"]:
        await message.answer(
            f"✅ <b>Успешно!</b>\n\n"
            f"👑 Premium на {months} месяцев подарен {username}",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ Ошибка: {result['error']}")

    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_keyboard())

@dp.callback_query(lambda c: c.data == "back")
async def back_callback(callback: types.CallbackQuery):
    await callback.message.answer("Выберите действие:", reply_markup=main_keyboard())
    await callback.answer()

async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())