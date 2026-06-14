"""
Общие обработчики команд
"""
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import WELCOME_MESSAGE, ADMIN_ID
from keyboards import get_main_menu, get_admin_menu
from database import Database

router = Router()
db = Database()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Обработчик команды /start"""
    args = message.text.split()
    
    # Обработка диплинков
    if len(args) > 1:
        payload = args[1]
        if payload.startswith("participate_"):
            giveaway_id = payload.split("_")[1]
            from handlers.participate import start_participation
            await start_participation(message, int(giveaway_id), state, bot)
            return

    await state.clear()
    
    # Добавляем пользователя в базу
    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # Выбираем клавиатуру в зависимости от прав
    if message.from_user.id == ADMIN_ID:
        keyboard = get_admin_menu()
    else:
        keyboard = get_main_menu()
    
    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=keyboard
    )


@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    """Обработчик кнопки помощи"""
    help_text = """
<b>📖 Справка по использованию SizeRandomBot</b>

<b>Как создать розыгрыш:</b>
1. Нажмите кнопку "🎉 Создать розыгрыш"
2. Следуйте инструкциям бота:
   • Отправьте описание конкурса (можно с фото/видео)
   • Укажите текст кнопки участия
   • Укажите количество победителей (1-100)
   • Добавьте каналы для обязательной подписки (до 5)
   • Выберите время завершения или завершение вручную

3. Бот сгенерирует пост - отправьте его в свой канал
4. Участники будут нажимать кнопку для участия
5. В указанное время бот автоматически выберет победителей

<b>Важно:</b>
• Бот должен быть администратором в каналах-спонсорах
• Проверка подписок происходит автоматически
• Победители выбираются случайным образом
• Отписавшиеся участники исключаются из розыгрыша

<b>Управление конкурсами:</b>
Используйте кнопку "📊 Мои конкурсы" для просмотра и управления вашими розыгрышами.
"""
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отменить")
async def cmd_cancel(message: Message, state: FSMContext):
    """Обработчик отмены действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return
    
    await state.clear()
    
    # Выбираем клавиатуру в зависимости от прав
    if message.from_user.id == ADMIN_ID:
        keyboard = get_admin_menu()
    else:
        keyboard = get_main_menu()
    
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=keyboard
    )
