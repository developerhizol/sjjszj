import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SEED = os.getenv("SEED")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

FRAGMENT_API_URL = "https://fragment-api.tech/api/v1"

class BuyStarsState(StatesGroup):
    waiting_username = State()
    waiting_quantity = State()
    waiting_confirm = State()

async def get_stars_price(quantity: int) -> float:
    url = f"{FRAGMENT_API_URL}/stars/price"
    headers = {"accept": "application/json"}
    params = {"quantity": quantity}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return float(data.get("price_ton", 0))
            return 0

async def buy_stars(username: str, quantity: int) -> dict:
    url = f"{FRAGMENT_API_URL}/stars/buy"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {
        "seed": SEED,
        "wallet_version": "V5R1",
        "username": username if username.startswith("@") else f"@{username}",
        "quantity": quantity,
        "payment_method": "ton",
        "show_sender": True
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            return await resp.json()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить звёзды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])
    await message.answer(
        "🤖 *Telegram Stars Shop*\n\n"
        "Покупка звёзд через TON блокчейн\n"
        "💰 Цена как на Fragment.com\n\n"
        "Выбери действие:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "buy_stars":
        await callback.message.edit_text(
            "✍️ Введи *username* получателя\n"
            "Например: `@durov` или просто `durov`",
            parse_mode="Markdown"
        )
        await state.set_state(BuyStarsState.waiting_username)
        await callback.answer()
    
    elif callback.data == "help":
        await callback.message.edit_text(
            "📖 *Инструкция*\n\n"
            "1. Нажми «Купить звёзды»\n"
            "2. Введи username получателя\n"
            "3. Введи количество звёзд (от 50 до 4999)\n"
            "4. Подтверди покупку\n\n"
            "⭐ Звёзды придут мгновенно!",
            parse_mode="Markdown"
        )
        await callback.answer()

@dp.message(BuyStarsState.waiting_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    await state.update_data(username=username)
    
    await message.answer(
        f"✅ Получатель: @{username}\n\n"
        "✍️ Введи количество звёзд (от 50 до 4999)"
    )
    await state.set_state(BuyStarsState.waiting_quantity)

@dp.message(BuyStarsState.waiting_quantity)
async def process_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity < 50 or quantity > 4999:
            await message.answer("❌ Количество должно быть от 50 до 4999")
            return
    except ValueError:
        await message.answer("❌ Введи число")
        return
    
    data = await state.get_data()
    username = data.get("username")
    await state.update_data(quantity=quantity)
    
    price = await get_stars_price(quantity)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить", callback_data="confirm_buy")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    
    await message.answer(
        f"📝 *Проверь данные*\n\n"
        f"👤 Получатель: @{username}\n"
        f"⭐ Количество: {quantity}\n"
        f"💰 Сумма: {price:.4f} TON\n\n"
        f"Подтверждаешь?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(BuyStarsState.waiting_confirm)

@dp.callback_query(BuyStarsState.waiting_confirm)
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await callback.message.edit_text("❌ Покупка отменена")
        await state.clear()
        await callback.answer()
        return
    
    if callback.data == "confirm_buy":
        await callback.message.edit_text("⏳ Отправка звёзд...")
        await callback.answer()
        
        data = await state.get_data()
        username = data.get("username")
        quantity = data.get("quantity")
        
        try:
            result = await buy_stars(username, quantity)
            
            if result.get("data") or result.get("confirm_referer"):
                price = await get_stars_price(quantity)
                await callback.message.edit_text(
                    f"✅ *Звёзды отправлены!*\n\n"
                    f"👤 Получатель: @{username}\n"
                    f"⭐ Количество: {quantity}\n"
                    f"💰 Сумма: {price:.4f} TON\n\n"
                    f"🎉 Успешно!",
                    parse_mode="Markdown"
                )
            else:
                error = result.get("error", "Неизвестная ошибка")
                await callback.message.edit_text(
                    f"❌ *Ошибка*\n\n"
                    f"`{error}`",
                    parse_mode="Markdown"
                )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ *Ошибка*\n\n"
                f"`{str(e)}`",
                parse_mode="Markdown"
            )
        
        await state.clear()

@dp.message(Command("price"))
async def cmd_price(message: Message):
    await message.answer("✍️ Введи количество звёзд для расчёта цены")
    
    @dp.message()
    async def get_price(msg: Message):
        try:
            quantity = int(msg.text.strip())
            if quantity < 50:
                await msg.answer("❌ Минимум 50 звёзд")
                return
            
            price = await get_stars_price(quantity)
            await msg.answer(
                f"📊 *Цена на Fragment.com*\n\n"
                f"⭐ {quantity} звёзд = {price:.4f} TON",
                parse_mode="Markdown"
            )
        except ValueError:
            await msg.answer("❌ Введи число")

@dp.message(Command("test"))
async def cmd_test(message: Message):
    await message.answer("🔄 Тестируем API...")
    
    try:
        price = await get_stars_price(50)
        result = await buy_stars("durov", 50)
        
        if result.get("data") or result.get("confirm_referer"):
            await message.answer(
                f"✅ API работает!\n\n"
                f"⭐ 50 звёзд = {price:.4f} TON\n"
                f"🎉 Покупка прошла успешно"
            )
        else:
            await message.answer(f"❌ Ошибка: {result}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    print("🤖 Бот запущен...")
    print(f"👤 Сид-фраза: {SEED[:20]}...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())