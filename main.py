import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

# Конфигурация
TOKEN = "8119842007:AAFuBm7Vyw8PYIMdEegV6R6YKw0xycF81JU"

THEORY_FILE = "theory_.json"  # Файл с теорией
TASKS_FILE = "tasks.json"  # Файл с задачами
TESTS_FILE = "tests.json"  # Файл с тестами

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Словари для хранения состояний пользователей
user_tests = {}
user_states = {}
user_reminders = {}
user_test_progress = {}  # Для хранения прогресса теста
user_tasks = {}  # Хранит задачи и текущий индекс для каждого пользователя

STATE_TASKS = "tasks"
STATE_TESTS = "tests"
STATE_NONE = "none"

# Загрузка данных
with open(THEORY_FILE, "r", encoding="utf-8") as f:
    theory_data = json.load(f)

with open("tasks.json", "r", encoding="utf-8") as f:
    tasks_data = json.load(f)

with open(TESTS_FILE, "r", encoding="utf-8") as f:
    tests_data = json.load(f)["tests"]  # Загружаем список тестов

# === Вспомогательные функции ===
def check_answer(test, user_answer):
    try:
        user_answer_index = test["options"].index(user_answer)
        return user_answer_index in test["answer"]
    except ValueError:
        return False

def get_topics():
    return [test["topic"] for test in tests_data]

def get_tests_by_topic(topic):
    for test in tests_data:
        if test["topic"] == topic:
            return test["questions"]
    return []  # Если тема не найдена

async def schedule_reminder(user_id, remind_time):
    now = datetime.now()
    delay = (remind_time - now).total_seconds()
    await asyncio.sleep(delay)
    if user_id in user_reminders and user_reminders[user_id] == remind_time:
        del user_reminders[user_id]
        await bot.send_message(user_id, "⏰ Напоминание! Время продолжить подготовку! 🚀")

# === Хендлеры ===
@router.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📘 Теория")],
            [KeyboardButton(text="📚 Задачи")],
            [KeyboardButton(text="📊 Тесты")],
            [KeyboardButton(text="🔗 Полезные ссылки")],
            [KeyboardButton(text="⏰ Напоминания")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Привет! Я помогу тебе подготовиться к ЕГЭ по физике. Выбери действие:", reply_markup=keyboard)

@router.message(lambda message: message.text == "📘 Теория")
async def send_theory_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for topic in theory_data["темы"]:
        button = InlineKeyboardButton(text=f"{topic['номер']}. {topic['название']}", callback_data=f"topic_{topic['номер']}")
        keyboard.inline_keyboard.append([button])
    await message.answer("Выбери тему:", reply_markup=keyboard)

@router.callback_query(lambda callback: callback.data.startswith("topic_"))
async def handle_topic_selection(callback: CallbackQuery):
    topic_number = int(callback.data.split("_")[1])
    selected_topic = next((t for t in theory_data["темы"] if t["номер"] == topic_number), None)
    if selected_topic:
        response = f"📘 <b>{selected_topic['название']}</b>\n\n{selected_topic['содержимое']}"
        await callback.message.answer(response, parse_mode="HTML")
    else:
        await callback.message.answer("Тема не найдена.")
    await callback.answer()

@router.message(lambda message: message.text == "📚 Задачи")
async def send_task_topics(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_TASKS  # Устанавливаем состояние пользователя в задачи

    topics = set(task["topic"] for task in tasks_data["tasks"])
    keyboard = InlineKeyboardBuilder()
    for topic in topics:
        keyboard.button(text=topic, callback_data=f"task_topic_{topic}")
    keyboard.adjust(1)
    await message.answer("Выбери тему задач:", reply_markup=keyboard.as_markup())


@router.callback_query(lambda callback: callback.data.startswith("task_topic_"))
async def handle_task_topic_selection(callback: CallbackQuery):
    topic = callback.data.replace("task_topic_", "")
    user_id = callback.from_user.id
    tasks = [task for task in tasks_data["tasks"] if task["topic"] == topic]
    if not tasks:
        await callback.message.answer("❌ Задачи не найдены.")
        return

    user_tasks[user_id] = {"tasks": tasks, "current_task_index": 0}
    user_states[user_id] = STATE_TASKS  # Обновляем состояние пользователя на задачи
    await send_next_task(callback.message, user_id)
    await callback.answer()


async def send_next_task(message: types.Message, user_id: int):
    if user_id not in user_tasks:
        await message.answer("❌ Ошибка: задачи не найдены.")
        return

    user_state = user_tasks[user_id]
    tasks = user_state["tasks"]
    index = user_state["current_task_index"]

    if index >= len(tasks):
        await message.answer("🎉 Ты решил все задачи!")
        del user_tasks[user_id]
        return

    task = tasks[index]
    await message.answer(f"📚 <b>Задача:</b>\n{task['question']}", parse_mode="HTML")

@router.message(lambda message: message.text == "📊 Тесты")
async def send_test_topics(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_TESTS  # Устанавливаем состояние пользователя в тесты

    topics = get_topics()
    if not topics:
        await message.answer("Тесты пока не загружены.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for index, topic in enumerate(topics):
        button = InlineKeyboardButton(text=topic, callback_data=f"test_topic_{index}")
        keyboard.inline_keyboard.append([button])

    await message.answer("Выбери тему теста:", reply_markup=keyboard)


@router.callback_query(lambda callback: callback.data.startswith("test_topic_"))
async def handle_test_topic_selection(callback: CallbackQuery):
    topic_index = int(callback.data.replace("test_topic_", ""))
    topics = get_topics()

    if topic_index < 0 or topic_index >= len(topics):
        await callback.message.answer("❌ Ошибка: тема не найдена.")
        return

    topic = topics[topic_index]
    tests = get_tests_by_topic(topic)

    if not tests:
        await callback.message.answer("❌ В этой теме пока нет тестов.")
        return

    # Сохраняем прогресс теста для пользователя
    user_test_progress[callback.from_user.id] = {
        "topic": topic,
        "tests": tests,
        "current_question_index": 0
    }
    user_states[callback.from_user.id] = STATE_TESTS  # Обновляем состояние на тесты

    # Отправляем первый вопрос
    await send_next_test_question(callback.message, callback.from_user.id)
    await callback.answer()


async def send_next_test_question(message: types.Message, user_id: int):
    if user_id not in user_test_progress:
        await message.answer("❌ Ошибка: прогресс теста не найден.")
        return

    progress = user_test_progress[user_id]
    tests = progress["tests"]
    current_index = progress["current_question_index"]

    if current_index >= len(tests):
        await message.answer("🎉 Ты прошел все вопросы по этой теме!")
        del user_test_progress[user_id]
        return

    test = tests[current_index]
    user_tests[user_id] = test

    # Проверяем, есть ли варианты ответов
    if "options" not in test or not test["options"]:
        await message.answer(f"❌ Ошибка: у теста отсутствуют варианты ответов. Вопрос: {test['question']}")
        return

    # Отправляем вопрос
    await message.answer(f"📊 <b>Вопрос {current_index + 1}:</b>\n{test['question']}", parse_mode="HTML")

    # Создаем inline-кнопки для вариантов ответов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"answer_{i}")] for i, option in enumerate(test["options"])
    ])

    # Отправляем список вариантов ответов кнопками
    await message.answer("Выбери вариант ответа:", reply_markup=keyboard)

@router.callback_query(lambda callback: callback.data.startswith("answer_"))
async def handle_answer_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_tests:
        await callback.answer("Ошибка! Вопрос не найден.", show_alert=True)
        return

    test = user_tests[user_id]
    user_answer_index = int(callback.data.split("_")[1])  # Получаем номер ответа

    if user_answer_index in test["answer"]:
        await callback.message.answer("✅ Правильно!")
    else:
        correct_answers = ", ".join([test["options"][i] for i in test["answer"]])
        await callback.message.answer(f"❌ Неправильно. Правильный ответ: <b>{correct_answers}</b>", parse_mode="HTML")

    del user_tests[user_id]

    # Переход к следующему вопросу
    if user_id in user_test_progress:
        user_test_progress[user_id]["current_question_index"] += 1
        await send_next_test_question(callback.message, user_id)

    await callback.answer()  # Закрываем всплывающее уведомление

@router.message(lambda message: message.text == "⏰ Напоминания")
async def set_reminder(message: types.Message):
    # Переход в режим установки напоминания.
    user_states[message.from_user.id] = "setting_reminder"  # Устанавливаем состояние пользователя
    await message.answer(
        "⏰ Введи время, когда ты хочешь получить напоминание, в формате ЧЧ:ММ. Например: 14:30"
    )


@router.message(lambda message: message.text == "🔗 Полезные ссылки")
async def send_links(message: types.Message):
    # Отправляет полезные ссылки для подготовки.
    links = [
        "https://fipi.ru/ege",
        "https://ege.sdamgia.ru/",
        "https://neznaika.info/",
        "https://neofamily.ru/fizika/smart-directory",
        "https://mizenko23.ru/wp-content/uploads/2019/04/jakovlev_fizika-polnyj_kurs_podgotovki_k_egeh.pdf",
        "https://thenewschool.ru/trainer/physics",
        "https://3.shkolkovo.online/catalog?SubjectId=4",

    ]
    links_text = "\n".join([f"🔗 <a href=\"{link}\">{link}</a>" for link in links])
    await message.answer(f"Вот полезные ресурсы:\n{links_text}", parse_mode="HTML")

# После завершения всех задач
async def handle_task_answer(message: types.Message):
    user_id = message.from_user.id
    user_state = user_tasks.get(user_id)

    if user_state is None:
        # Если пользователь не решает задачи
        await message.answer("❌ Ты не решаешь задачи сейчас. Выбери действие через меню.")
        return

    tasks = user_state["tasks"]
    index = user_state["current_task_index"]

    if index >= len(tasks):
        # Если задачи завершены
        await message.answer("🎉 Ты решил все задачи!")
        del user_tasks[user_id]  # Удаляем из user_tasks
        del user_states[user_id]  # Удаляем из user_states
        return

    task = tasks[index]
    try:
        # Проверка ответа пользователя
        user_answer = float(message.text.strip())
        if user_answer == task["answer"]:
            await message.answer(f"✅ Правильный ответ!\n\n<b>Решение:</b> {task['solution']}", parse_mode="HTML")
        else:
            await message.answer(f"❌ Неправильно. Правильный ответ: {task['answer']}\n\n<b>Решение:</b> {task['solution']}", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Введи числовой ответ.")

    # Переход к следующей задаче
    user_tasks[user_id]["current_task_index"] += 1
    await send_next_task(message, user_id)


async def handle_test_answer(message: types.Message):
    user_id = message.from_user.id
    user_test_progress = user_test_progress.get(user_id)

    if user_test_progress is None:
        await message.answer("❌ Ты не проходишь тесты. Выбери действие через меню.")
        return

    tests = user_test_progress["tests"]
    index = user_test_progress["current_question_index"]

    if index >= len(tests):
        # Если тест завершен
        await message.answer("🎉 Ты прошел все тесты!")
        del user_test_progress[user_id]  # Удаляем из user_test_progress
        del user_states[user_id]  # Удаляем из user_states
        return

    test = tests[index]
    user_answer = message.text.strip().lower()

    if user_answer == test["correct_answer"]:
        await message.answer("✅ Правильный ответ!")
    else:
        await message.answer(f"❌ Неправильно. Правильный ответ: {test['correct_answer']}")

    # Переход к следующему вопросу
    user_test_progress[user_id]["current_question_index"] += 1
    await send_next_test_question(message, user_id)


@router.message()
async def process_user_message(message: types.Message):
    user_id = message.from_user.id

    # Проверяем, есть ли у пользователя активное состояние
    user_state = user_states.get(user_id, STATE_NONE)

    if user_state == STATE_TASKS:
        await handle_task_answer(message)
    elif user_state == STATE_TESTS:
        await handle_test_answer(message)
    elif user_state == "setting_reminder":
        await set_reminder(message)
    else:
        await message.answer("ℹ️ Я не понимаю эту команду. Выбери действие через меню.")


async def handle_other_messages(message: types.Message):
    user_id = message.from_user.id

    # Логика для обработки команд
    if message.text.lower() == "/start":
        # Перезапуск меню
        await start_command(message)  # Функция для начала работы с ботом

    elif message.text.lower() == "📘 Теория":
        await send_theory_menu(message)  # Функция для отправки теории

    elif message.text.lower() == "📚 Задачи":
        await send_task_topics(message)  # Функция для отправки списка задач

    elif message.text.lower() == "📊 Тесты":
        await send_test_topics(message)  # Функция для отправки списка тестов

    elif message.text.lower() == "🔗 Полезные ссылки":
        await send_links(message)  # Функция для отправки полезных ссылок

    elif message.text.lower() == "⏰ Напоминания":
        await set_reminder(message)  # Функция для установки напоминания

    else:
        await message.answer("ℹ️ Я не понимаю эту команду. Выбери действие через меню.")


async def set_reminder(message: types.Message):
    user_id = message.from_user.id
    try:
        remind_time = datetime.strptime(message.text.strip(), "%H:%M").time()
        now = datetime.now()
        remind_datetime = datetime.combine(now.date(), remind_time)

        if remind_datetime < now:
            remind_datetime += timedelta(days=1)

        user_reminders[user_id] = remind_datetime
        await message.answer(f"✅ Напоминание установлено на {remind_datetime.strftime('%H:%M')}.")
        asyncio.create_task(schedule_reminder(user_id, remind_datetime))

        # Сбрасываем состояние пользователя
        del user_states[user_id]
    except ValueError:
        await message.answer("❌ Неправильный формат времени. Введи в формате ЧЧ:ММ (например, 14:30).")

    # Главное меню, если команда не распознана
    main_menu_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📘 Теория")],
            [KeyboardButton(text="📚 Задачи")],
            [KeyboardButton(text="📊 Тесты")],
            [KeyboardButton(text="🔗 Полезные ссылки")],
            [KeyboardButton(text="⏰ Напоминания")],
        ],
        resize_keyboard=True,
    )

    await message.answer("ℹ️ Выбери действие через меню.", reply_markup=main_menu_keyboard)

# === Главный блок ===
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())