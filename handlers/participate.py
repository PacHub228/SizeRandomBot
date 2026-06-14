"""
Обработчики участия в розыгрыше с числовой капчей
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from io import BytesIO

from keyboards import get_participate_keyboard, get_check_subscription_keyboard
from database import Database
from captcha_generator import CaptchaGenerator

router = Router()
db = Database()
captcha_gen = CaptchaGenerator()


class CaptchaState(StatesGroup):
    """Состояние для ввода капчи"""
    waiting_for_answer = State()


async def check_user_subscriptions(bot: Bot, user_id: int, channels: list) -> tuple[bool, list]:
    """
    Проверка подписок пользователя на каналы
    Возвращает (подписан_на_все, список_неподписанных_каналов)
    """
    not_subscribed = []
    
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception:
            # Если не удалось проверить, считаем что не подписан
            not_subscribed.append(channel)
    
    return len(not_subscribed) == 0, not_subscribed


async def start_participation(message: Message, giveaway_id: int, state: FSMContext, bot: Bot):
    """Функция начала участия (через диплинк)"""
    giveaway = await db.get_giveaway(giveaway_id)
    
    if not giveaway:
        await message.answer("❌ Розыгрыш не найден.")
        return
    
    if giveaway['status'] != 'active':
        await message.answer("❌ Розыгрыш уже завершен.")
        return
    
    is_participant = await db.is_participant(giveaway_id, message.from_user.id)
    
    if is_participant:
        await message.answer("✅ Вы уже участвуете в этом розыгрыше!")
        return
    
    required_channels = giveaway.get('required_channels', [])
    
    if required_channels:
        is_subscribed, not_subscribed = await check_user_subscriptions(
            bot, message.from_user.id, required_channels
        )
        
        if not is_subscribed:
            channels_text = "\n".join([f"• {channel}" for channel in not_subscribed])
            
            await message.answer(
                "📢 <b>Для участия в розыгрыше подпишитесь на следующие каналы:</b>\n\n"
                f"{channels_text}\n\n"
                "После подписки снова нажмите кнопку участия в канале.",
                reply_markup=get_check_subscription_keyboard(not_subscribed),
                parse_mode="HTML"
            )
            return

    # Если капча включена
    if giveaway.get('captcha_enabled'):
        captcha_bytes, answer = captcha_gen.generate_captcha_bytes()
        
        await state.update_data(
            giveaway_id=giveaway_id,
            captcha_answer=answer
        )
        await state.set_state(CaptchaState.waiting_for_answer)
        
        await message.answer(
            "ℹ️ Перед тем, как вы станете участником конкурса, мы должны убедиться, что вы не бот.",
            parse_mode="HTML"
        )
        
        await bot.send_photo(
            chat_id=message.from_user.id,
            photo=BufferedInputFile(captcha_bytes, filename="captcha.jpg"),
            caption="▶️ Какие числа вы видите на картинке? Отправьте боту ответ\n\n"
                    "Для отказа от участия в конкурсе нажмите /cancel",
            parse_mode="HTML"
        )
    else:
        # Сразу регистрируем если капчи нет
        await register_participant(message, giveaway_id, giveaway, bot)


@router.message(CaptchaState.waiting_for_answer)
async def process_captcha_answer(message: Message, state: FSMContext, bot: Bot):
    """Обработка ответа на капчу"""
    data = await state.get_data()
    correct_answer = data.get('captcha_answer', '')
    giveaway_id = data.get('giveaway_id')
    
    user_answer = message.text.strip()
    
    if user_answer == correct_answer:
        # Капча пройдена
        await state.clear()
        
        giveaway = await db.get_giveaway(giveaway_id)
        if giveaway and giveaway['status'] == 'active':
            await register_participant(message, giveaway_id, giveaway, bot)
        else:
            await message.answer("❌ Розыгрыш уже завершен или не найден.")
    else:
        # Капча не пройдена - генерируем новую
        captcha_bytes, new_answer = captcha_gen.generate_captcha_bytes()
        await state.update_data(captcha_answer=new_answer)
        
        await message.answer_photo(
            photo=BufferedInputFile(captcha_bytes, filename="captcha.jpg"),
            caption=f"❌ Неверно! Попробуйте ещё раз.\n\n"
                    f"▶️ Какие числа вы видите на картинке? Отправьте боту ответ",
            parse_mode="HTML"
        )


async def register_participant(source, giveaway_id: int, giveaway: dict, bot: Bot):
    """Регистрация участника в розыгрыше"""
    user_id = source.from_user.id
    username = source.from_user.username
    first_name = source.from_user.first_name
    
    added = await db.add_participant(
        giveaway_id=giveaway_id,
        user_id=user_id,
        username=username,
        first_name=first_name
    )
    
    if added:
        participants_count = await db.get_participants_count(giveaway_id)
        
        # Обновляем счетчик в канале
        if giveaway.get('chat_id') and giveaway.get('message_id'):
            try:
                bot_info = await bot.get_me()
                kb = get_participate_keyboard(
                    giveaway_id,
                    participants_count,
                    giveaway['button_text'],
                    bot_info.username
                )
                await bot.edit_message_reply_markup(
                    chat_id=giveaway['chat_id'],
                    message_id=giveaway['message_id'],
                    reply_markup=kb
                )
            except TelegramBadRequest:
                pass
        
        await bot.send_message(
            chat_id=user_id,
            text="🎉 Вы успешно зарегистрированы в розыгрыше!",
        )
        
        await db.add_user(
            user_id=user_id,
            username=username,
            first_name=first_name
        )
    else:
        await bot.send_message(
            chat_id=user_id,
            text="✅ Вы уже участвуете в этом розыгрыше!"
        )


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    """Повторная проверка подписки"""
    await callback.answer("🔄 Проверка выполнена. Нажмите кнопку участия в канале ещё раз.", show_alert=True)
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "finished")
async def finished_giveaway(callback: CallbackQuery):
    """Обработка нажатия на кнопку завершенного розыгрыша"""
    await callback.answer("✅ Розыгрыш завершен. Итоги подведены.", show_alert=True)
