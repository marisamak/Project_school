import asyncio
import random
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# === Конфигурация ===
TOKEN = "8119842007:AAHK5nFjmAqxT7Fv1WDjj1LTAlsuFqSb3Yo"

THEORY_FILE = "theory.json"  # Теория (в формате JSON)
TASKS_FILE = "tasks.json"  # Задачи (в формате JSON)
TESTS_FILE = "tests.json"  # Тесты (в формате JSON)

# === Инициализация ===
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Словарь для хранения текущих задач пользователей
user_tasks = {}

# Словарь для хранения текущих тестов пользователей
user_tests = {}

# Словарь для хранения напоминаний пользователей
user_reminders = {}

# Словарь для хранения состояния пользователей (например, установка напоминаний)
user_states = {}

# Загрузка данных из файлов
with open(THEORY_FILE, "r", encoding="utf-8") as f:
    theory_data = json.load(f)

with open(TASKS_FILE, "r", encoding="utf-8") as f:
    tasks = json.load(f)

with open(TESTS_FILE, "r", encoding="utf-8") as f:
    tests = json.load(f)

# === Вспомогательные функции ===
def get_random_task():
    """Возвращает случайную задачу."""
    return random.choice(tasks)


def check_answer(task, user_answer):
    """Проверяет правильность ответа пользователя."""
    correct_answer = task.get("answer")
    return str(user_answer).strip() == str(correct_answer).strip()


def get_random_test():
    """Возвращает случайный тест."""
    return random.choice(tests)


def get_random_theory():
    """Возвращает случайный раздел теории."""
    return random.choice(theory_data)


async def schedule_reminder(user_id, remind_time):
    """Устанавливает напоминание для пользователя."""
    now = datetime.now()
    delay = (remind_time - now).total_seconds()
    await asyncio.sleep(delay)

    if user_id in user_reminders and user_reminders[user_id] == remind_time:
        del user_reminders[user_id]
        await bot.send_message(
            user_id, "⏰ Напоминание! Пришло время продолжить подготовку. 🚀"
        )


# === Хендлеры ===
@router.message(Command("start"))
async def start_command(message: types.Message):
    """Приветственное сообщение."""
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

    await message.answer(
        "Привет! Я помогу тебе подготовиться к ЕГЭ по физике. Вот что я умею:",
        reply_markup=keyboard,
    )


@router.message(lambda message: message.text == "📘 Теория")
async def send_theory(message: types.Message):
    """Отправляет случайный раздел теории."""
    theory = get_random_theory()
    await message.answer(
        f"📘 <b>{theory['title']}</b>\n\n{theory['content']}", parse_mode="HTML"
    )


@router.message(lambda message: message.text == "📚 Задачи")
async def send_task(message: types.Message):
    """Отправляет пользователю задачу."""
    task = get_random_task()
    user_tasks[message.from_user.id] = task  # Сохраняем задачу для пользователя
    await message.answer(
        f"📚 <b>Задача:</b>\n{task['question']}\n\nℹ️ Напишите свой ответ, таким образом. Пример: 42 н. Обрати внимание, что единицы измерения обязательны и они пишутся со строчной буквы!",
        parse_mode="HTML",
    )


@router.message(lambda message: message.text == "📊 Тесты")
async def send_test(message: types.Message):
    """Отправляет тест пользователю."""
    test = get_random_test()

    # Проверка на наличие ключа 'options' и 'question'
    if not test or "question" not in test or "options" not in test:
        await message.answer("К сожалению, произошла ошибка при загрузке теста.")
        return

    # Сохраняем текущий тест для пользователя
    user_tests[message.from_user.id] = test

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=option)] for option in test["options"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        f"📊 <b>{test['question']}</b>", reply_markup=keyboard, parse_mode="HTML"
    )


@router.message(lambda message: message.text == "⏰ Напоминания")
async def set_reminder(message: types.Message):
    """Переход в режим установки напоминания."""
    user_states[message.from_user.id] = "setting_reminder"  # Устанавливаем состояние пользователя
    await message.answer(
        "⏰ Введите время, когда вы хотите получить напоминание, в формате ЧЧ:ММ. Например: 14:30"
    )


@router.message(lambda message: message.text == "🔗 Полезные ссылки")
async def send_links(message: types.Message):
    """Отправляет полезные ссылки для подготовки."""
    links = [
        "https://fipi.ru/ege",
        "https://ege.sdamgia.ru/",
        "https://physics-ege.sdamgia.ru",
        "https://neznaika.info/",
        "https://neofamily.ru/fizika/smart-directory",
        "https://mizenko23.ru/wp-content/uploads/2019/04/jakovlev_fizika-polnyj_kurs_podgotovki_k_egeh.pdf"
        "https://thenewschool.ru/trainer/physics",
        "https://3.shkolkovo.online/catalog?SubjectId=4",

    ]
    links_text = "\n".join([f"🔗 <a href=\"{link}\">{link}</a>" for link in links])
    await message.answer(f"Вот полезные ресурсы:\n{links_text}", parse_mode="HTML")


@router.message()
async def process_user_message(message: types.Message):
    """Обрабатывает все сообщения пользователя: ответы на задачи, тесты или установку напоминаний."""
    user_id = message.from_user.id

    # Основное меню (после завершения теста или задачи)
    main_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📘 Теория")],
            [KeyboardButton(text="📚 Задачи")],
            [KeyboardButton(text="📊 Тесты")],
            [KeyboardButton(text="🔗 Полезные ссылки")],
            [KeyboardButton(text="⏰ Напоминания")],
        ],
        resize_keyboard=True,
    )

    # Проверка, находится ли пользователь в режиме установки напоминания
    if user_states.get(user_id) == "setting_reminder":
        try:
            # Парсим время из сообщения
            remind_time = datetime.strptime(message.text.strip(), "%H:%M").time()
            now = datetime.now()
            remind_datetime = datetime.combine(now.date(), remind_time)

            # Если время уже прошло, устанавливаем на следующий день
            if remind_datetime < now:
                remind_datetime += timedelta(days=1)

            # Сохраняем напоминание и запускаем задачу
            user_reminders[user_id] = remind_datetime
            await message.answer(f"⏰ Напоминание установлено на {remind_datetime.strftime('%H:%M')}.")
            asyncio.create_task(schedule_reminder(user_id, remind_datetime))

            # Убираем пользователя из режима установки напоминания
            del user_states[user_id]

        except ValueError:
            await message.answer(
                "❌ Неправильный формат времени. Введите время в формате ЧЧ:ММ. Например: 14:30"
            )
        return

    # Проверка: отвечает ли пользователь на тест
    if user_id in user_tests:
        test = user_tests[user_id]
        user_answer = message.text.strip()

        if user_answer == test["answer"]:
            await message.answer("✅ Правильно! Отличная работа!")
        else:
            await message.answer(
                f"❌ Неправильно. Правильный ответ: <b>{test['answer']}</b>",
                parse_mode="HTML",
            )

        # Удаляем текущий тест после ответа
        del user_tests[user_id]

        # Показываем основное меню
        await message.answer("Выберите, что хотите сделать дальше:", reply_markup=main_menu)
        return

    # Проверка: отвечает ли пользователь на задачу
    if user_id in user_tasks:
        task = user_tasks[user_id]
        user_answer = message.text.strip()

        if check_answer(task, user_answer):
            await message.answer("✅ Правильно! Отличная работа!")
            del user_tasks[user_id]  # Удаляем задачу, так как она решена
        else:
            await message.answer(
                f"❌ Неправильно. Попробуйте ещё раз!\n\nℹ️ Подсказка: Обратите внимание на единицы измерения."
            )
        return

    # Если сообщение не распознано
    await message.answer(
        "ℹ️ Вы пока не выбрали задачу или тест. Нажмите '📚 Задачи' или '📊 Тесты', чтобы начать.",
        reply_markup=main_menu,
    )


# === Главный блок ===
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
