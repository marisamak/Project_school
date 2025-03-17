import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

# === Конфигурация ===
TOKEN = "8119842007:AAHK5nFjmAqxT7Fv1WDjj1LTAlsuFqSb3Yo"

THEORY_FILE = "theory_.json"
TASKS_FILE = "tasks.json"
TESTS_FILE = "tests.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Словари состояний пользователей
user_tasks = {}
user_tests = {}
user_states = {}
user_reminders = {}
user_test_progress = {}

# Загрузка данных
with open(THEORY_FILE, "r", encoding="utf-8") as f:
    theory_data = json.load(f)

with open(TASKS_FILE, "r", encoding="utf-8") as f:
    tasks_data = json.load(f)

with open(TESTS_FILE, "r", encoding="utf-8") as f:
    tests_data = json.load(f)["tests"]

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

# === Основное меню ===
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

# === Теория ===
@router.message(lambda message: message.text == "📘 Теория")
async def send_theory_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{t['номер']}. {t['название']}", callback_data=f"topic_{t['номер']}")]
        for t in theory_data["темы"]
    ])
    await message.answer("Выберите тему:", reply_markup=keyboard)

@router.callback_query(lambda callback: callback.data.startswith("topic_"))
async def handle_topic_selection(callback: CallbackQuery):
    topic_number = int(callback.data.split("_")[1])
    topic = next((t for t in theory_data["темы"] if t["номер"] == topic_number), None)
    if topic:
        await callback.message.answer(f"📘 <b>{topic['название']}</b>\n\n{topic['содержимое']}", parse_mode="HTML")
    else:
        await callback.message.answer("Тема не найдена.")
    await callback.answer()

# === Обработка задач ===
@router.message(lambda message: message.text == "📚 Задачи")
async def send_task_topics(message: types.Message):
    topics = set(task["topic"] for task in tasks_data["tasks"])
    keyboard = InlineKeyboardBuilder()
    for topic in topics:
        keyboard.button(text=topic, callback_data=f"task_topic_{topic}")
    keyboard.adjust(1)
    await message.answer("Выберите тему задач:", reply_markup=keyboard.as_markup())

@router.callback_query(lambda callback: callback.data.startswith("task_topic_"))
async def handle_task_topic_selection(callback: CallbackQuery):
    topic = callback.data.replace("task_topic_", "")
    user_id = callback.from_user.id
    tasks = [task for task in tasks_data["tasks"] if task["topic"] == topic]
    if not tasks:
        await callback.message.answer("❌ Задачи не найдены.")
        return
    user_tasks[user_id] = {"tasks": tasks, "current_task_index": 0}
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
        await message.answer("🎉 Вы решили все задачи!")
        del user_tasks[user_id]
        return

    task = tasks[index]
    await message.answer(f"📚 <b>Задача:</b>\n{task['question']}", parse_mode="HTML")

@router.message()
async def check_task_answer(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_tasks:
        return
    user_state = user_tasks[user_id]
    tasks = user_state["tasks"]
    index = user_state["current_task_index"]
    if index >= len(tasks):
        return
    task = tasks[index]
    try:
        if float(message.text.strip()) == task["answer"]:
            await message.answer("✅ Верно!")
        else:
            await message.answer(f"❌ Неверно. Правильный ответ: {task['answer']}\n\n<b>Решение:</b> {task['solution']}", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Ошибка: введите число.")
    user_tasks[user_id]["current_task_index"] += 1
    await send_next_task(message, user_id)

# === Тесты ===
@router.message(lambda message: message.text == "📊 Тесты")
async def send_test_topics(message: types.Message):
    topics = get_topics()
    if not topics:
        await message.answer("Тесты пока не загружены.")
        return

    # Создаем клавиатуру с темами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for index, topic in enumerate(topics):
        button = InlineKeyboardButton(text=topic, callback_data=f"test_topic_{index}")
        keyboard.inline_keyboard.append([button])

    await message.answer("Выберите тему теста:", reply_markup=keyboard)

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

    # Отправляем первый вопрос
    await send_next_test_question(callback.message, callback.from_user.id)

async def send_next_test_question(message: types.Message, user_id: int):
    if user_id not in user_test_progress:
        await message.answer("❌ Ошибка: прогресс теста не найден.")
        return

    progress = user_test_progress[user_id]
    tests = progress["tests"]
    current_index = progress["current_question_index"]

    if current_index >= len(tests):
        await message.answer("🎉 Вы прошли все вопросы по этой теме!")
        del user_test_progress[user_id]
        return

    test = tests[current_index]
    user_tests[user_id] = test

    if "options" not in test or not test["options"]:
        await message.answer(f"❌ Ошибка: у теста отсутствуют варианты ответов. Вопрос: {test['question']}")
        return

    await message.answer(f"📊 <b>Вопрос {current_index + 1}:</b>\n{test['question']}", parse_mode="HTML")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"answer_{i}")] for i, option in enumerate(test["options"])
    ])

    await message.answer("Выберите вариант ответа:", reply_markup=keyboard)

@router.callback_query(lambda callback: callback.data.startswith("answer_"))
async def handle_answer_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_tests:
        await callback.answer("Ошибка! Вопрос не найден.", show_alert=True)
        return

    test = user_tests[user_id]
    user_answer_index = int(callback.data.split("_")[1]) # Получаем номер ответа

    if user_answer_index in test["answer"]:
        await callback.message.answer("✅ Правильно!")
    else:
        correct_answers = ", ".join([test["options"][i] for i in test["answer"]])
        await callback.message.answer(f"❌ Неправильно. Правильный ответ: <b>{correct_answers}</b>", parse_mode="HTML")

    del user_tests[user_id]

    if user_id in user_test_progress:
        user_test_progress[user_id]["current_question_index"] += 1
        await send_next_test_question(callback.message, user_id)

    await callback.answer()

# === Напоминания ===
@router.message(lambda message: message.text == "⏰ Напоминания")
async def set_reminder(message: types.Message):
    user_states[message.from_user.id] = "setting_reminder"
    await message.answer("⏰ Введите время, когда вы хотите получить напоминание, в формате ЧЧ:ММ. Например: 14:30")

# === Полезные ссылки ===
@router.message(lambda message: message.text == "🔗 Полезные ссылки")
async def send_links(message: types.Message):
    """Отправляет полезные ссылки для подготовки."""
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

# === Универсальный хэндлер ===
@router.message()
async def process_user_message(message: types.Message):
    user_id = message.from_user.id
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

    if user_states.get(user_id) == "setting_reminder":
        try:
            remind_time = datetime.strptime(message.text.strip(), "%H:%M").time()
            now = datetime.now()
            remind_datetime = datetime.combine(now.date(), remind_time)
            if remind_datetime < now:
                remind_datetime += timedelta(days=1)
            user_reminders[user_id] = remind_datetime
            await message.answer(f"⏰ Напоминание установлено на {remind_datetime.strftime('%H:%M')}.")
            asyncio.create_task(schedule_reminder(user_id, remind_datetime))
            del user_states[user_id]
        except ValueError:
            await message.answer("❌ Неправильный формат времени. Введите в формате ЧЧ:ММ (например, 14:30).")
        return

    if user_id in user_tests:
        test = user_tests[user_id]
        user_answer = message.text.strip()
        if check_answer(test, user_answer):
            await message.answer("✅ Правильно!")
        else:
            await message.answer(f"❌ Неправильно. Правильный ответ: <b>{test['options'][test['answer'][0]]}</b>", parse_mode="HTML")
        del user_tests[user_id]

        # Переходим к следующему вопросу
        if user_id in user_test_progress:
            user_test_progress[user_id]["current_question_index"] += 1
            await send_next_test_question(message, user_id)
        return

    await message.answer("ℹ️ Выберите действие через меню.", reply_markup=main_menu_keyboard)

# === Запуск бота ===
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())