"""
Обработчики создания розыгрыша - публикация в канал
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder
from states import CreateGiveaway
from keyboards import (
    get_cancel_keyboard, get_skip_keyboard, get_end_time_keyboard,
    get_participate_keyboard, get_main_menu, get_admin_menu,
    get_captcha_keyboard
)
from config import MAX_WINNERS, MAX_CHANNELS, ADMIN_ID
from database import Database

router = Router()
db = Database()


@router.message(F.text == "🎉 Создать розыгрыш")
async def start_create_giveaway(message: Message, state: FSMContext, bot: Bot):
    """Начало создания розыгрыша - пользователь вводит ID канала"""
    await state.set_state(CreateGiveaway.description)
    
    await message.answer(
        f"📝 <b>Шаг 1/7: Описание розыгрыша</b>\n\n"
        "Отправьте текст описания вашего конкурса. Вы можете использовать HTML-разметку "
        "(<b>жирный</b>, <i>курсив</i>, <code>код</code>).\n\n"
        "Также вы можете прикрепить одно фото или видео к сообщению.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateGiveaway.description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания розыгрыша"""
    description = message.html_text or message.text
    
    media_type = None
    media_file_id = None
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    await state.update_data(
        description=description,
        media_type=media_type,
        media_file_id=media_file_id
    )
    
    await state.set_state(CreateGiveaway.button_text)
    await message.answer(
        "🔘 <b>Шаг 2/6: Текст кнопки</b>\n\n"
        "Введите текст для кнопки участия в розыгрыше.\n"
        "По умолчанию: <code>🎉 Участвовать!</code>\n\n"
        "Вы можете пропустить этот шаг, чтобы использовать текст по умолчанию.",
        parse_mode="HTML",
        reply_markup=get_skip_keyboard()
    )


@router.message(CreateGiveaway.button_text, F.text == "⏭️ Пропустить")
async def skip_button_text(message: Message, state: FSMContext):
    """Пропуск текста кнопки"""
    await state.update_data(button_text="🎉 Участвовать!")
    await state.set_state(CreateGiveaway.winners_count)
    await message.answer(
        f"🏆 <b>Шаг 3/6: Количество победителей</b>\n\n"
        f"Введите количество победителей (от 1 до {MAX_WINNERS}):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateGiveaway.button_text)
async def process_button_text(message: Message, state: FSMContext):
    """Обработка текста кнопки"""
    button_text = message.text.strip()
    
    if len(button_text) > 50:
        await message.answer("❌ Текст кнопки слишком длинный. Максимум 50 символов.")
        return
    
    await state.update_data(button_text=button_text)
    await state.set_state(CreateGiveaway.winners_count)
    await message.answer(
        f"🏆 <b>Шаг 3/6: Количество победителей</b>\n\n"
        f"Введите количество победителей (от 1 до {MAX_WINNERS}):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateGiveaway.winners_count)
async def process_winners_count(message: Message, state: FSMContext):
    """Обработка количества победителей"""
    try:
        winners_count = int(message.text)
        if winners_count < 1 or winners_count > MAX_WINNERS:
            await message.answer(
                f"❌ Количество победителей должно быть от 1 до {MAX_WINNERS}."
            )
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число.")
        return
    
    await state.update_data(winners_count=winners_count)
    await state.set_state(CreateGiveaway.required_channels)
    await message.answer(
        f"📢 <b>Шаг 4/6: Обязательные подписки</b>\n\n"
        f"Отправьте ID или юзернеймы каналов/чатов для обязательной подписки "
        f"(до {MAX_CHANNELS} штук).\n\n"
        f"Формат: @channel1 @channel2 или -100123456789\n"
        f"Можно отправить каждый канал с новой строки.\n\n"
        f"⚠️ <b>Важно:</b> Бот должен быть администратором в этих каналах!\n\n"
        f"Вы можете пропустить этот шаг, если подписки не требуются.",
        parse_mode="HTML",
        reply_markup=get_skip_keyboard()
    )


@router.message(CreateGiveaway.required_channels, F.text == "⏭️ Пропустить")
async def skip_channels(message: Message, state: FSMContext):
    """Пропуск каналов"""
    await state.update_data(required_channels=[])
    await state.set_state(CreateGiveaway.end_time)
    await message.answer(
        "⏰ <b>Шаг 5/6: Время завершения</b>\n\n"
        "Выберите, когда должен завершиться розыгрыш:",
        parse_mode="HTML",
        reply_markup=get_end_time_keyboard()
    )


@router.message(CreateGiveaway.required_channels)
async def process_channels(message: Message, state: FSMContext, bot: Bot):
    """Обработка списка каналов"""
    text = message.text.strip()
    
    channels = []
    usernames = re.findall(r'@(\w+)', text)
    chat_ids = re.findall(r'-?\d{10,}', text)
    
    channels.extend([f"@{username}" for username in usernames])
    channels.extend(chat_ids)
    
    if not channels:
        await message.answer(
            "❌ Не удалось распознать каналы. Используйте формат:\n"
            "@channel1 @channel2 или -100123456789"
        )
        return
    
    if len(channels) > MAX_CHANNELS:
        await message.answer(
            f"❌ Слишком много каналов. Максимум {MAX_CHANNELS}."
        )
        return
    
    warnings = []
    valid_channels = []
    
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, bot.id)
            if member.status in ['administrator', 'creator']:
                valid_channels.append(channel)
            else:
                warnings.append(f"⚠️ Бот не является администратором в {channel}")
        except Exception as e:
            warnings.append(f"⚠️ Не удалось проверить канал {channel}: {str(e)}")
    
    if not valid_channels:
        await message.answer(
            "❌ Бот не является администратором ни в одном из указанных каналов.\n"
            "Пожалуйста, добавьте бота администратором и попробуйте снова."
        )
        return
    
    if warnings:
        warning_text = "\n".join(warnings)
        await message.answer(f"⚠️ <b>Предупреждения:</b>\n{warning_text}", parse_mode="HTML")
    
    await state.update_data(required_channels=valid_channels)
    await state.set_state(CreateGiveaway.end_time)
    await message.answer(
        "⏰ <b>Шаг 5/6: Время завершения</b>\n\n"
        "Выберите, когда должен завершиться розыгрыш:",
        parse_mode="HTML",
        reply_markup=get_end_time_keyboard()
    )


@router.callback_query(CreateGiveaway.end_time, F.data.startswith("endtime_"))
async def process_end_time(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка времени завершения"""
    await callback.answer()
    
    time_option = callback.data.split("_")[1]
    data = await state.get_data()
    
    end_time = None
    manual_end = False
    
    if time_option == "manual":
        manual_end = True
    else:
        time_deltas = {
            "1h": timedelta(hours=1),
            "3h": timedelta(hours=3),
            "6h": timedelta(hours=6),
            "12h": timedelta(hours=12),
            "1d": timedelta(days=1),
            "3d": timedelta(days=3),
            "7d": timedelta(days=7)
        }
        end_time = datetime.now() + time_deltas.get(time_option, timedelta(hours=1))
    
    await state.update_data(end_time=end_time, manual_end=manual_end)
    
    # Шаг 6: Выбор капчи
    await state.set_state(CreateGiveaway.captcha_select)
    await callback.message.answer(
        "🔒 <b>Шаг 6/7: Капча для участников</b>\n\n"
        "Включить капчу для защиты от ботов?\n"
        "Участникам нужно будет ввести слово с картинки для участия.",
        reply_markup=get_captcha_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(CreateGiveaway.captcha_select, F.data.startswith("captcha_"))
async def process_captcha(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка выбора капчи"""
    await callback.answer()
    
    captcha_enabled = callback.data == "captcha_yes"
    await state.update_data(captcha_enabled=captcha_enabled)
    
    # Шаг 7: Ввод ID канала
    await state.set_state(CreateGiveaway.channel_select)
    await callback.message.answer(
        "📢 <b>Шаг 7/7: ID канала для публикации</b>\n\n"
        "Отправьте ID вашего канала или группы, куда бот опубликует розыгрыш.\n\n"
        "📌 <b>Как узнать ID канала:</b>\n"
        "• Перешлите любое сообщение из канала боту @getmyid_bot\n"
        "• ID канала начинается с -100 (например: -1001234567890)\n"
        "• Или используйте юзернейм канала (например: @mychannel)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(CreateGiveaway.channel_select)
async def process_channel_input(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода ID канала"""
    channel_input = message.text.strip()
    
    # Преобразуем @username в username без @
    if channel_input.startswith('@'):
        channel_input = channel_input[1:]
        target_chat_id = f"@{channel_input}"
    else:
        # Пробуем распознать как числовой ID
        try:
            target_chat_id = int(channel_input)
        except ValueError:
            await message.answer(
                "❌ Неверный формат. Введите ID канала (например: -1001234567890) "
                "или юзернейм (например: @mychannel)"
            )
            return
    
    # Проверяем доступ к каналу
    try:
        chat = await bot.get_chat(target_chat_id)
        member = await bot.get_chat_member(chat.id, bot.id)
        
        if member.status not in ['administrator', 'creator']:
            await message.answer(
                "❌ Бот не является администратором в этом канале.\n\n"
                "Добавьте бота как администратора с правами на отправку сообщений."
            )
            return
        
        await state.update_data(target_chat_id=chat.id)
        await create_giveaway_from_message(message, state, bot)
        
    except Exception as e:
        await message.answer(
            f"❌ Не удалось получить доступ к каналу: {str(e)}\n\n"
            "Проверьте правильность ID и убедитесь, что бот добавлен в канал."
        )


async def create_giveaway_from_message(message: Message, state: FSMContext, bot: Bot):
    """Создание розыгрыша и публикация в канале (из сообщения)"""
    data = await state.get_data()
    
    target_chat_id = data.get('target_chat_id')
    end_time = data.get('end_time')
    manual_end = data.get('manual_end', False)
    
    giveaway_id = await db.create_giveaway(
        creator_id=message.from_user.id,
        description=data['description'],
        button_text=data['button_text'],
        winners_count=data['winners_count'],
        required_channels=data.get('required_channels', []),
        end_time=end_time,
        manual_end=manual_end,
        media_type=data.get('media_type'),
        media_file_id=data.get('media_file_id'),
        target_chat_id=target_chat_id,
        captcha_enabled=data.get('captcha_enabled', False)
    )
    
    post_text = data['description']
    me = await bot.get_me()
    keyboard = get_participate_keyboard(giveaway_id, 0, data['button_text'], me.username)
    
    try:
        if data.get('media_type') == 'photo':
            sent_message = await bot.send_photo(
                chat_id=target_chat_id,
                photo=data['media_file_id'],
                caption=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif data.get('media_type') == 'video':
            sent_message = await bot.send_video(
                chat_id=target_chat_id,
                video=data['media_file_id'],
                caption=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            sent_message = await bot.send_message(
                chat_id=target_chat_id,
                text=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        await db.update_giveaway_message(
            giveaway_id=giveaway_id,
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id
        )
        
        # Выбираем клавиатуру в зависимости от прав
        if message.from_user.id == ADMIN_ID:
            main_kb = get_admin_menu()
        else:
            main_kb = get_main_menu()
        
        try:
            chat_info = await bot.get_chat(target_chat_id)
            chat_name = chat_info.title or chat_info.first_name or "канал"
        except Exception:
            chat_name = "канал"
        
        completion_text = f"✅ <b>Розыгрыш создан и опубликован!</b>\n\n"
        completion_text += f"📢 Опубликован в: {chat_name}\n"
        completion_text += f"🆔 ID розыгрыша: {giveaway_id}\n\n"
        
        if manual_end:
            completion_text += "Розыгрыш будет завершен вручную. Используйте кнопку \"📊 Мои конкурсы\" для управления."
        else:
            completion_text += f"⏰ Автоматическое завершение: <code>{end_time.strftime('%d.%m.%Y %H:%M')}</code>"
        
        await message.answer(
            completion_text,
            parse_mode="HTML",
            reply_markup=main_kb
        )
        
    except Exception as e:
        error_text = str(e)
        if 'bot was blocked' in error_text.lower() or 'forbidden' in error_text.lower():
            await message.answer(
                "❌ Не удалось отправить сообщение в канал.\n\n"
                "Убедитесь, что:\n"
                "• Бот добавлен в канал как администратор\n"
                "• У бота есть права на отправку сообщений"
            )
        else:
            await message.answer(
                f"❌ Ошибка при публикации: {error_text}"
            )
    
    await state.clear()


async def create_giveaway(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Создание розыгрыша и публикация в канале (старая функция для совместимости, если где-то используется)"""
    data = await state.get_data()
    
    target_chat_id = data.get('target_chat_id')
    end_time = data.get('end_time')
    manual_end = data.get('manual_end', False)
    
    giveaway_id = await db.create_giveaway(
        creator_id=callback.from_user.id,
        description=data['description'],
        button_text=data['button_text'],
        winners_count=data['winners_count'],
        required_channels=data.get('required_channels', []),
        end_time=end_time,
        manual_end=manual_end,
        media_type=data.get('media_type'),
        media_file_id=data.get('media_file_id'),
        target_chat_id=target_chat_id,
        captcha_enabled=data.get('captcha_enabled', False)
    )
    
    post_text = data['description']
    me = await bot.get_me()
    keyboard = get_participate_keyboard(giveaway_id, 0, data['button_text'], me.username)
    
    try:
        if data.get('media_type') == 'photo':
            sent_message = await bot.send_photo(
                chat_id=target_chat_id,
                photo=data['media_file_id'],
                caption=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif data.get('media_type') == 'video':
            sent_message = await bot.send_video(
                chat_id=target_chat_id,
                video=data['media_file_id'],
                caption=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            sent_message = await bot.send_message(
                chat_id=target_chat_id,
                text=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        await db.update_giveaway_message(
            giveaway_id=giveaway_id,
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id
        )
        
        if callback.from_user.id == ADMIN_ID:
            main_kb = get_admin_menu()
        else:
            main_kb = get_main_menu()
        
        try:
            chat_info = await bot.get_chat(target_chat_id)
            chat_name = chat_info.title or chat_info.first_name or "канал"
        except Exception:
            chat_name = "канал"
        
        completion_text = f"✅ <b>Розыгрыш создан и опубликован!</b>\n\n"
        completion_text += f"📢 Опубликован в: {chat_name}\n"
        completion_text += f"🆔 ID розыгрыша: {giveaway_id}\n\n"
        
        if manual_end:
            completion_text += "Розыгрыш будет завершен вручную. Используйте кнопку \"📊 Мои конкурсы\" для управления."
        else:
            completion_text += f"⏰ Автоматическое завершение: <code>{end_time.strftime('%d.%m.%Y %H:%M')}</code>"
        
        await callback.message.answer(
            completion_text,
            parse_mode="HTML",
            reply_markup=main_kb
        )
        
    except Exception as e:
        error_text = str(e)
        if 'bot was blocked' in error_text.lower() or 'forbidden' in error_text.lower():
            await callback.message.answer(
                "❌ Не удалось отправить сообщение в канал.\n\n"
                "Убедитесь, что:\n"
                "• Бот добавлен в канал как администратор\n"
                "• У бота есть права на отправку сообщений"
            )
        else:
            await callback.message.answer(
                f"❌ Ошибка при публикации: {error_text}"
            )
    
    await state.clear()
