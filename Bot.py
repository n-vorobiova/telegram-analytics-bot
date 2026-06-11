import asyncio
import logging
import os
import io
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from aiogram.filters import CommandStart
import matplotlib.pyplot as plt
import numpy as np

# Налаштування логування для моніторингу роботи бота
logging.basicConfig(level=logging.INFO)


TOKEN = "ВАШ_ТЕЛЕГРАМ_ТОКЕН"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Тимчасове збереження даних користувачів (у реальному проєкті тут має бути БД)
user_data = {}

# --- БЛОК БІЗНЕС-ЛОГІКИ (ОБРОБКА ДАНИХ) ---

def parse_and_validate_numbers(text: str) -> list[float]:
    """
    Розумний парсер: знаходить усі числа в тексті (цілі та дробові),
    ігноруючи літери та зайві символи. Захищає від спаму обмеженням кількості.
    """
    # Регулярний вираз для пошуку чисел (наприклад: 12; 4.5; -7)
    numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", text)]
    
    if len(numbers) > 500:  # Захист від перевантаження системи
        raise ValueError("Занадто великий масив даних. Максимум 500 чисел.")
    if not numbers:
        raise ValueError("У повідомленні не знайдено жодного числа. Спробуйте ще раз.")
        
    return numbers

def calculate_analytics(numbers: list[float]) -> dict:
    """
    Обчислення бізнес-метрики та статистичних показників масиву даних.
    """
    arr = np.array(numbers)
    analytics = {
        "count": len(arr),
        "sum": float(np.sum(arr)),
        "mean": float(np.mean(arr)),  # Середній чек / показник
        "max": float(np.max(arr)),
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
    }
    return analytics

def generate_analytics_chart(numbers: list[float]) -> io.BytesIO:
    """
    Генерація графіку динаміки показників для бізнес-звіту.
    """
    plt.figure(figsize=(8, 4))
    plt.plot(numbers, marker='o', color='#0078D4', linestyle='-', linewidth=2, label="Динаміка показників")
    plt.axhline(np.mean(numbers), color='red', linestyle='--', label=f"Середнє ({np.mean(numbers):.2f})")
    
    plt.title("Аналітичний звіт динаміки даних", fontsize=14, fontweight='bold')
    plt.xlabel("Індекс запису (ID)", fontsize=10)
    plt.ylabel("Значення", fontsize=10)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    # Збереження графіку в буфер пам'яті (без створення файлу на диску)
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    return img_buf

# --- БЛОК ІНТЕРФЕЙСУ (AIOGRAM HANDLERS) ---

# Головне меню з кнопками для UX
def get_main_keyboard():
    buttons = [
        [KeyboardButton(text="📊 Отримати аналітичний звіт")],
        [KeyboardButton(text="📈 Згенерувати графік динаміки")],
        [KeyboardButton(text="🧹 Очистити мої дані")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обробка команди /start"""
    await message.answer(
        "👋 Вітаю в **Аналітичному боті**!\n\n"
        "Надішліть мені масив числових даних (наприклад: складські залишки, "
        "фінансові надходження або результати тестування через кому чи пробіл), "
        "і я підготую комерційний звіт.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "📊 Отримати аналітичний звіт")
async def send_report(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id]:
        await message.answer("❌ Спочатку надішліть мені список чисел для аналізу.")
        return
    
    res = calculate_analytics(user_data[user_id])
    report = (
        f"📋 **БІЗНЕС-ЗВІТ ОБРОБКИ ДАНИХ**\n"
        f"-----------------------------------------\n"
        f"🔹 **Кількість записів:** {res['count']} шт.\n"
        f"🔹 **Загальна сума (Обсяг):** {res['sum']:.2f}\n"
        f"🔹 **Середнє значення (Mean):** {res['mean']:.2f}\n"
        f"🔹 **Медіана:** {res['median']:.2f}\n"
        f"🔺 **Максимальний показник:** {res['max']:.2f}\n"
        f"🔻 **Мінімальний показник:** {res['min']:.2f}\n"
        f"-----------------------------------------\n"
        f"💡 *Дані успішно валідовані та структуровані.*"
    )
    await message.answer(report, parse_mode="Markdown")

@dp.message(F.text == "📈 Згенерувати графік динаміки")
async def send_chart(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data or not user_data[user_id]:
        await message.answer("❌ Немає даних для побудови графіку. Надішліть числа.")
        return
    
    await message.answer("🔄 Герується візуалізація звіту, зачекайте секунду...")
    chart_buf = generate_analytics_chart(user_data[user_id])
    input_file = BufferedInputFile(chart_buf.read(), filename="analytics_chart.png")
    
    await message.answer_photo(photo=input_file, caption="📈 Графік розподілу та динаміки ваших показників.")

@dp.message(F.text == "🧹 Очистити мої дані")
async def clear_data(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = []
    await message.answer("🧹 Ваша історія даних успішно очищена.")

@dp.message(F.text)
async def handle_data_input(message: Message):
    """Обробник вхідного тексту з числами"""
    user_id = message.from_user.id
    try:
        # Парсимо числа з будь-якого тексту користувача
        parsed_numbers = parse_and_validate_numbers(message.text)
        user_data[user_id] = parsed_numbers
        
        await message.answer(
            f"✅ Успішно завантажено **{len(parsed_numbers)}** показників.\n"
            f"Скористайтеся меню нижче, щоб отримати звіт або графік.",
            parse_mode="Markdown"
        )
    except ValueError as e:
        await message.answer(f"❌ Помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())