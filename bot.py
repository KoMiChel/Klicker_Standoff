import sqlite3 as sq
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Objects bot, dispather
PAYMENTS_TOKEN = "#"
bot = Bot(token='#')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

#run
async def on_startup(_):
    try:
        print("Bot running")
        sql_start()
    except sq.Error as e:
        print(f"Error: {e}")

#connect to sql
def sql_start():
    try:
        global base, cur
        base = sq.connect('users_Click.db')
        cur = base.cursor()
        if base:
            print('users connect')
        base.execute("""CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY, nic TEXT DEFAULT Нет,
                    balance FLOAT DEFAULT 0, premium TEXT DEFAULT Нет
                )""")
        base.commit()
    except sq.Error as e:
        print(f"При работе с базой данных произошла ошибка: {e}")

async def sql_read(message):

    chat_id = str(message.chat.id)
    cur.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    result = cur.fetchone()

    if result is not None:
        caption = f'💫Главное меню💫\n🗣Ник: {result[1]}\n💰Баланс: {result[2]} gold\n🔸Premium: {result[3]}'
        return caption
    else:
        await bot.send_message(chat_id, "Профиль не найден")
        return "Профиль не найден"


# Обработчик команды /start
@dp.message_handler(commands='start')
async def start(message: types.Message):
    # Отправляем сообщение с главным меню

    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    click_button = types.KeyboardButton('Клик')
    menu_button = types.KeyboardButton('Главное меню')
    info_button = types.KeyboardButton('Важная информация')

    keyboard.add(click_button)
    keyboard.add(menu_button,info_button)

    await message.answer('Добро пожаловать! Этот бот позволяет получать голду Standoff за клики. Деньги с показа рекламы используются для покупки голды в Standoff.', reply_markup=keyboard)

    # Получаем ID пользователя
    chat_id = message.from_user.id
    print(chat_id)
    # Проверяем, есть ли пользователь уже в базе данных
    cur.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    result = cur.fetchone()

    # Если пользователь не найден, добавляем его в таблицу
    if result is None:
        base.execute("""INSERT INTO users (chat_id) VALUES (?)""", (chat_id,))
        base.commit()

# Кнопка "Клик"
@dp.message_handler(lambda message: message.text == 'Клик')
async def click(message: types.Message):
    # Получаем ID пользователя
    chat_id = message.from_user.id

    # Проверяем, есть ли у пользователя подписка Premium
    cur.execute('SELECT premium FROM users WHERE chat_id = ?', (chat_id,))
    result = cur.fetchone()

    if result is not None and result[0] == 'Да':
        increment = 0.5
        cur.execute('SELECT balance FROM users WHERE chat_id = ?', (chat_id,))
        balance = cur.fetchone()[0]
        if (balance * 10) % 200 == 0:
            await message.answer('Это ваше рекламное сообщение!')
    else:
        increment = 0.1
        cur.execute('SELECT balance FROM users WHERE chat_id = ?', (chat_id,))
        balance = cur.fetchone()[0]
        if (balance * 10) % 10 == 0:
            await message.answer('Это ваше рекламное сообщение!')

    # Увеличиваем баланс пользователя
    cur.execute("""UPDATE users SET balance = round(balance + ?, 1) WHERE chat_id = ?""", (increment, chat_id,))
    base.commit()

    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    click_button = types.KeyboardButton('Клик')
    menu_button = types.KeyboardButton('Главное меню')
    info_button = types.KeyboardButton('Важная информация')
    keyboard.add(click_button)
    keyboard.add(menu_button,info_button)

    await message.answer('Клик засчитан.', reply_markup=keyboard)

# Кнопка "Главное меню"
@dp.message_handler(lambda message: message.text == 'Главное меню')
async def return_to_menu(message: types.Message):

    keyboard = InlineKeyboardMarkup(row_width=1, resize_keyboard=True)

    premium_button = InlineKeyboardButton('Купить premium', callback_data='premium')
    card_button = InlineKeyboardButton('Изменить ник', callback_data='nic')
    viv_button = InlineKeyboardButton('Обменять на голду', callback_data='viv')

    keyboard.add(premium_button, card_button, viv_button)

    user_menu = await sql_read(message)
    await bot.send_message(message.from_user.id, text = user_menu, reply_markup=keyboard)

class Form(StatesGroup):
    name = State()

@dp.callback_query_handler(lambda c: c.data == 'nic')
async def process_callback_nic(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, 'Введите свой ник в Standoff:')
    await Form.name.set()

@dp.message_handler(state=Form.name)
async def process_nic(message: types.Message, state: FSMContext):
    # Получаем ID пользователя и ник
    chat_id = message.from_user.id
    nic = message.text

    # Обновляем никнейм в базе данных
    cur.execute("""UPDATE users SET nic = ? WHERE chat_id = ?""", (nic, chat_id,))
    base.commit()

    await message.answer('Ваш ник был успешно обновлен.')
    await state.finish()  # завершить FSM context (сбросить все)

# prices
PRICE = types.LabeledPrice(label="Premium", amount=100*100)  # в копейках (руб)

@dp.callback_query_handler(lambda c: c.data == 'viv')
async def viv(callback_query: types.CallbackQuery):
    message = callback_query.message
    chat_id = str(message.chat.id)
    cur.execute('SELECT balance FROM users WHERE chat_id = ?', (chat_id,))
    balance = cur.fetchone()[0]
    print(balance)

    if balance < 1000:
        await bot.send_message(message.chat.id, "Для обмена нужно накопить больше 1000 gold")
    else:
        await bot.send_message(message.chat.id, "Обмен пока недоступен из-за большого количества пользователей. Попробуйте позже.")

    base.commit()

# buy
@dp.callback_query_handler(lambda c: c.data == 'premium')
async def buy(callback_query: types.CallbackQuery):
    message = callback_query.message

    await bot.send_message(message.chat.id,
                           "Премиум подписка позволяет получать в 5 раз больше gold за клик, а также уменьшает количество рекламы в 4 раза!")
    await bot.send_invoice(message.chat.id,
                           title="Premium подписка",
                           description="Активация подписки Premium",
                           provider_token=PAYMENTS_TOKEN,
                           currency="rub",
                           is_flexible=False,
                           prices=[PRICE],
                           start_parameter="premium-subscription",
                           payload="test-invoice-payload")

# pre checkout  (must be answered in 10 seconds)
@dp.pre_checkout_query_handler(lambda query: True)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# successful payment
@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    print("SUCCESSFUL PAYMENT:")

    chat_id = message.from_user.id
    cur.execute("""UPDATE users SET premium = 'Да' WHERE chat_id = ?""", (chat_id,))
    base.commit()

    payment_info = message.successful_payment.to_python()
    for k, v in payment_info.items():
        print(f"{k} = {v}")

    await bot.send_message(message.chat.id,"Поздравляем, теперь у вас есть premium")


# run long-polling
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)

