import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import config

BOT_TOKEN = config.BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Хранение данных пользователей
user_data = {}

# Состояния для FSM
class PomodoroStates(StatesGroup):
    SET_WORK = State()
    SET_BREAK = State()

async def pomodoro_timer(user_id, work_time, break_time):
    try:
        while True:
            # Рабочий интервал
            user_data[user_id]['is_working'] = True
            await bot.send_message(user_id, f"🛠 Начинаем рабочий интервал: {work_time} минут!")
            await asyncio.sleep(work_time * 60)
            
            # Перерыв
            user_data[user_id]['is_working'] = False
            await bot.send_message(user_id, f"☕ Перерыв: {break_time} минут!")
            await asyncio.sleep(break_time * 60)
            
    except asyncio.CancelledError:
        await bot.send_message(user_id, "⏸ Таймер остановлен")
        user_data[user_id]['is_working'] = None

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {
        'work_time': 25,
        'break_time': 5,
        'task': None,
        'is_working': None
    }
    
    text = (
        "🍅 Добро пожаловать в Pomodoro бот!\n\n"
        "Доступные команды:\n"
        "/start_timer - Запустить таймер\n"
        "/stop_timer - Остановить таймер\n"
        "/settings - Настройки интервалов\n"
        "/status - Текущий статус"
    )
    
    await message.answer(text)

@dp.message_handler(commands=['start_timer'])
async def cmd_start_timer(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Сначала выполните /start")
        return
    
    if user_data[user_id]['task'] and not user_data[user_id]['task'].cancelled():
        await message.answer("Таймер уже запущен!")
        return
    
    work_time = user_data[user_id]['work_time']
    break_time = user_data[user_id]['break_time']
    
    user_data[user_id]['task'] = asyncio.create_task(
        pomodoro_timer(user_id, work_time, break_time)
    )
    await message.answer("Таймер запущен!")

@dp.message_handler(commands=['stop_timer'])
async def cmd_stop_timer(message: types.Message):
    user_id = message.from_user.id
    if user_data.get(user_id, {}).get('task'):
        user_data[user_id]['task'].cancel()
        user_data[user_id]['task'] = None
        await message.answer("Таймер остановлен")
    else:
        await message.answer("Нет активных таймеров")

@dp.message_handler(commands=['settings'])
async def cmd_settings(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Рабочее время", "Время отдыха")
    await message.answer(
        "Выберите параметр для настройки:",
        reply_markup=keyboard
    )

@dp.message_handler(text="Рабочее время")
async def set_work_time(message: types.Message):
    await PomodoroStates.SET_WORK.set()
    await message.answer(
        "Введите новое рабочее время (в минутах):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message_handler(text="Время отдыха")
async def set_break_time(message: types.Message):
    await PomodoroStates.SET_BREAK.set()
    await message.answer(
        "Введите новое время отдыха (в минутах):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message_handler(state=PomodoroStates.SET_WORK)
async def process_work_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        time = int(message.text)
        if time <= 0:
            raise ValueError
        user_data[user_id]['work_time'] = time
        await message.answer(f"🕓 Рабочее время установлено: {time} минут")
    except ValueError:
        await message.answer("Пожалуйста, введите целое положительное число")
    await state.finish()

@dp.message_handler(state=PomodoroStates.SET_BREAK)
async def process_break_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        time = int(message.text)
        if time <= 0:
            raise ValueError
        user_data[user_id]['break_time'] = time
        await message.answer(f"🕓 Время отдыха установлено: {time} минут")
    except ValueError:
        await message.answer("Пожалуйста, введите целое положительное число")
    await state.finish()

@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Сначала выполните /start")
        return
    
    status = "не активен"
    if user_data[user_id]['task'] and not user_data[user_id]['task'].cancelled():
        status = "работает" if user_data[user_id]['is_working'] else "перерыв"
    
    text = (
        f"🍅 Текущий статус: {status}\n"
        f"Рабочее время: {user_data[user_id]['work_time']} мин\n"
        f"Время отдыха: {user_data[user_id]['break_time']} мин"
    )
    
    await message.answer(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)