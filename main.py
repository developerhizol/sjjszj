import os
import asyncio
import logging
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import aiohttp
import json

# ==================== ЗАГРУЗКА ПЕРЕМЕННЫХ ====================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SEED_STRING = os.getenv("SEED_STRING")
API_BASE_URL = "https://fragment-api.net"  # фиксированный URL

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== СОСТОЯНИЯ FSM ====================
class BuyStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_stars_amount = State()
    waiting_for_premium_months = State()
    waiting_for_ton_amount = State()
    waiting_for_order_uuid = State()

# ==================== КЛАВИАТУРЫ ====================
def main_keyboard():
    kb = [
        [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy_stars")],
        [InlineKeyboardButton(text="👑 Купить Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="₿ Купить TON", callback_data="buy_ton")],
        [InlineKeyboardButton(text="📋 Проверить заказ", callback_data="check_order")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_keyboard():
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==================== API КЛИЕНТ ====================
class FragmentAPI:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.seed = SEED_STRING
    
    async def create_order(self, username: str, product: str, amount: int) -> dict:
        """
        Создание заказа через API
        product: 'stars', 'premium', 'ton'
        """
        # Генерируем UUID для заказа
        order_uuid = str(uuid.uuid4())
        
        # Формируем запрос в зависимости от продукта
        if product == "stars":
            endpoint = f"{self.base_url}/api/v1/stars/buy"
            payload = {
                "seed": self.seed,
                "username": username,
                "quantity": amount
            }
        elif product == "premium":
            endpoint = f"{self.base_url}/api/v1/premium/buy"
            payload = {
                "seed": self.seed,
                "username": username,
                "months": amount
            }
        elif product == "ton":
            endpoint = f"{self.base_url}/api/v1/ton/topup"
            payload = {
                "seed": self.seed,
                "username": username,
                "amount": amount
            }
        else:
            return {"success": False, "error": "Неизвестный продукт"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        # Сохраняем заказ в память (для проверки статуса)
                        order_data = {
                            "order_uuid": order_uuid,
                            "username": username,
                            "product": product,
                            "amount": amount,
                            "status": "completed",
                            "created_at": datetime.now().isoformat(),
                            "response": data
                        }
                        return {"success": True, "data": order_data}
                    else:
                        return {"success": False, "error": data.get("error", "Ошибка API")}
        except Exception as e:
            logger.error(f"API Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_order_status(self, order_uuid: str) -> dict:
        """
        Получение статуса заказа
        """
        url = f"{self.base_url}/api/v1/orders/{order_uuid}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        return {"success": True, "data": data}
                    else:
                        return {"success": False, "error": data.get("error", "Заказ не найден")}
        except Exception as e:
            logger.error(f"API Error: {e}")
            return {"success": False, "error": str(e)}

# Хранилище заказов (в реальном проекте используйте БД)
orders_storage = {}

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌟 <b>Добро пожаловать в бота для покупки!</b>\n\n"
        "Я помогу вам купить:\n"
        "⭐ Telegram Stars\n"
        "👑 Telegram Premium\n"
        "₿ TON (Gram) на аккаунт\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "info")
async def info_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "⭐ <b>Stars</b>: от 50 до 10 000 000 шт.\n"
        "👑 <b>Premium</b>: 3, 6 или 12 месяцев\n"
        "₿ <b>TON</b>: от 1 до 1000 TON\n\n"
        "Все покупки проходят <b>без KYC</b>.\n"
        "После оплаты средства зачисляются мгновенно.",
        parse_mode="HTML",
        reply_markup=back_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back")
async def back_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_keyboard()
    )
    await callback.answer()

# ==================== ПОКУПКА STARS ====================
@dp.callback_query(lambda c: c.data == "buy_stars")
async def buy_stars_start(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 ⭐", callback_data="stars_50")],
        [InlineKeyboardButton(text="100 ⭐", callback_data="stars_100")],
        [InlineKeyboardButton(text="250 ⭐", callback_data="stars_250")],
        [InlineKeyboardButton(text="500 ⭐", callback_data="stars_500")],
        [InlineKeyboardButton(text="1000 ⭐", callback_data="stars_1000")],
        [InlineKeyboardButton(text="5000 ⭐", callback_data="stars_5000")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="stars_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.answer(
        "⭐ Выберите количество Stars или введите свою сумму:",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("stars_"))
async def process_stars_selection(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")[1]
    
    if data == "custom":
        await callback.message.answer("Введите количество Stars (от 50 до 10 000 000):")
        await state.set_state(BuyStates.waiting_for_stars_amount)
        await callback.answer()
        return
    
    amount = int(data)
    await state.update_data(stars_amount=amount)
    await callback.message.answer("Введите <b>username</b> получателя (например: @durov):", parse_mode="HTML")
    await state.set_state(BuyStates.waiting_for_username)
    await callback.answer()

@dp.message(BuyStates.waiting_for_stars_amount)
async def process_stars_custom(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount < 50 or amount > 10_000_000:
            await message.answer("❌ Количество должно быть от 50 до 10 000 000. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")
        return
    
    await state.update_data(stars_amount=amount)
    await message.answer("Введите <b>username</b> получателя (например: @durov):", parse_mode="HTML")
    await state.set_state(BuyStates.waiting_for_username)

# ==================== ПОКУПКА PREMIUM ====================
@dp.callback_query(lambda c: c.data == "buy_premium")
async def buy_premium_start(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3 месяца", callback_data="premium_3")],
        [InlineKeyboardButton(text="6 месяцев", callback_data="premium_6")],
        [InlineKeyboardButton(text="12 месяцев", callback_data="premium_12")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.answer(
        "👑 Выберите срок Premium:",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("premium_"))
async def process_premium_selection(callback: types.CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    await state.update_data(premium_months=months)
    await callback.message.answer("Введите <b>username</b> получателя (например: @durov):", parse_mode="HTML")
    await state.set_state(BuyStates.waiting_for_username)
    await callback.answer()

# ==================== ПОКУПКА TON ====================
@dp.callback_query(lambda c: c.data == "buy_ton")
async def buy_ton_start(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 TON", callback_data="ton_1")],
        [InlineKeyboardButton(text="5 TON", callback_data="ton_5")],
        [InlineKeyboardButton(text="10 TON", callback_data="ton_10")],
        [InlineKeyboardButton(text="25 TON", callback_data="ton_25")],
        [InlineKeyboardButton(text="50 TON", callback_data="ton_50")],
        [InlineKeyboardButton(text="100 TON", callback_data="ton_100")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="ton_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.answer(
        "₿ Выберите количество TON или введите свою сумму:",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("ton_"))
async def process_ton_selection(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")[1]
    
    if data == "custom":
        await callback.message.answer("Введите количество TON (от 1 до 1000):")
        await state.set_state(BuyStates.waiting_for_ton_amount)
        await callback.answer()
        return
    
    amount = int(data)
    await state.update_data(ton_amount=amount)
    await callback.message.answer("Введите <b>username</b> получателя (например: @durov):", parse_mode="HTML")
    await state.set_state(BuyStates.waiting_for_username)
    await callback.answer()

@dp.message(BuyStates.waiting_for_ton_amount)
async def process_ton_custom(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount < 1 or amount > 1000:
            await message.answer("❌ Количество должно быть от 1 до 1000. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")
        return
    
    await state.update_data(ton_amount=amount)
    await message.answer("Введите <b>username</b> получателя (например: @durov):", parse_mode="HTML")
    await state.set_state(BuyStates.waiting_for_username)

# ==================== ОБЩИЙ ОБРАБОТЧИК USERNAME ====================
@dp.message(BuyStates.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        username = "@" + username
    
    # Получаем данные из состояния
    data = await state.get_data()
    product_type = None
    amount = None
    
    if "stars_amount" in data:
        product_type = "stars"
        amount = data["stars_amount"]
    elif "premium_months" in data:
        product_type = "premium"
        amount = data["premium_months"]
    elif "ton_amount" in data:
        product_type = "ton"
        amount = data["ton_amount"]
    else:
        await message.answer("❌ Ошибка: не выбран продукт. Начните заново.")
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=main_keyboard())
        return
    
    # Отправляем уведомление о начале обработки
    loading_msg = await message.answer(f"⏳ Обрабатываю заказ для {username}...")
    
    # Создаем заказ через API
    api = FragmentAPI()
    result = await api.create_order(username, product_type, amount)
    
    if result["success"]:
        order_data = result["data"]
        order_uuid = order_data.get("order_uuid")
        
        # Сохраняем заказ в хранилище
        orders_storage[order_uuid] = order_data
        
        # Формируем ответ
        product_names = {
            "stars": f"⭐ {amount} Stars",
            "premium": f"👑 Premium на {amount} мес.",
            "ton": f"₿ {amount} TON"
        }
        
        await loading_msg.edit_text(
            f"✅ <b>Успешно!</b>\n\n"
            f"📦 <b>Заказ:</b> {product_names[product_type]}\n"
            f"👤 <b>Получатель:</b> {username}\n"
            f"🆔 <b>UUID:</b> <code>{order_uuid}</code>\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"Средства зачислены на аккаунт!",
            parse_mode="HTML"
        )
    else:
        await loading_msg.edit_text(
            f"❌ <b>Ошибка:</b>\n\n"
            f"{result.get('error', 'Неизвестная ошибка')}",
            parse_mode="HTML"
        )
    
    # Очищаем состояние
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_keyboard())

# ==================== ПРОВЕРКА ЗАКАЗА ====================
@dp.callback_query(lambda c: c.data == "check_order")
async def check_order_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите <b>UUID</b> заказа для проверки:", parse_mode="HTML")
    await state.set_state(BuyStates.waiting_for_order_uuid)
    await callback.answer()

@dp.message(BuyStates.waiting_for_order_uuid)
async def process_order_check(message: types.Message, state: FSMContext):
    order_uuid = message.text.strip()
    
    # Проверяем в локальном хранилище
    if order_uuid in orders_storage:
        order_data = orders_storage[order_uuid]
        product_names = {
            "stars": f"⭐ {order_data['amount']} Stars",
            "premium": f"👑 Premium на {order_data['amount']} мес.",
            "ton": f"₿ {order_data['amount']} TON"
        }
        
        await message.answer(
            f"📋 <b>Информация о заказе</b>\n\n"
            f"🆔 <b>UUID:</b> <code>{order_uuid}</code>\n"
            f"📦 <b>Товар:</b> {product_names[order_data['product']]}\n"
            f"👤 <b>Получатель:</b> {order_data['username']}\n"
            f"📅 <b>Дата:</b> {order_data['created_at']}\n"
            f"✅ <b>Статус:</b> {order_data['status']}",
            parse_mode="HTML"
        )
    else:
        # Проверяем через API
        api = FragmentAPI()
        result = await api.get_order_status(order_uuid)
        
        if result["success"]:
            data = result["data"]
            await message.answer(
                f"📋 <b>Информация о заказе</b>\n\n"
                f"🆔 <b>UUID:</b> <code>{order_uuid}</code>\n"
                f"📦 <b>Статус:</b> {data.get('status', 'Неизвестно')}\n"
                f"👤 <b>Получатель:</b> {data.get('username', 'Неизвестно')}",
                parse_mode="HTML"
            )
        else:
            await message.answer(f"❌ Заказ с UUID <code>{order_uuid}</code> не найден.", parse_mode="HTML")
    
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_keyboard())

# ==================== ЗАПУСК БОТА ====================
async def main():
    print("🚀 Бот запущен...")
    print(f"📡 API URL: {API_BASE_URL}")
    print("🤖 Ожидаю команды...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())