"""
Обработчики админ-панели
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from config import ADMIN_ID
from keyboards import get_admin_panel_keyboard, get_broadcast_confirm_keyboard, get_admin_menu
from database import Database
from states import AdminBroadcast

router = Router()
db = Database()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == ADMIN_ID


@router.message(F.text == "👑 Админ-панель")
async def admin_panel(message: Message):
    """Открыть админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Показать статистику бота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return
    
    stats = await db.get_stats()
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Всего пользователей:</b> {stats['users_count']}
🎉 <b>Всего розыгрышей:</b> {stats['giveaways_count']}
🟢 <b>Активных розыгрышей:</b> {stats['active_giveaways']}
"""
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return
    
    await state.set_state(AdminBroadcast.message)
    await callback.message.answer(
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям бота.\n"
        "Вы можете отправить текст, фото или видео с подписью.\n\n"
        "Для отмены используйте команду /cancel",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminBroadcast.message)
async def admin_broadcast_message(message: Message, state: FSMContext):
    """Получить сообщение для рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return
    
    # Сохраняем данные сообщения
    broadcast_data = {
        'text': message.html_text or message.text or message.caption,
        'photo': None,
        'video': None
    }
    
    if message.photo:
        broadcast_data['photo'] = message.photo[-1].file_id
    elif message.video:
        broadcast_data['video'] = message.video.file_id
    
    await state.update_data(broadcast_data=broadcast_data)
    
    # Показываем превью
    preview_text = "📢 <b>Предпросмотр рассылки:</b>\n\n"
    
    if broadcast_data['photo']:
        await message.answer_photo(
            photo=broadcast_data['photo'],
            caption=preview_text + (broadcast_data['text'] or ""),
            parse_mode="HTML"
        )
    elif broadcast_data['video']:
        await message.answer_video(
            video=broadcast_data['video'],
            caption=preview_text + (broadcast_data['text'] or ""),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            preview_text + broadcast_data['text'],
            parse_mode="HTML"
        )
    
    users_count = len(await db.get_all_users())
    
    await message.answer(
        f"Сообщение будет отправлено <b>{users_count}</b> пользователям.\n\n"
        "Подтвердите отправку:",
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "broadcast_confirm")
async def admin_broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтвердить рассылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return
    
    data = await state.get_data()
    broadcast_data = data.get('broadcast_data')
    
    if not broadcast_data:
        await callback.answer("❌ Данные рассылки не найдены.", show_alert=True)
        await state.clear()
        return
    
    await callback.answer("🔄 Начинаю рассылку...", show_alert=False)
    await callback.message.edit_text("🔄 Рассылка началась...")
    
    users = await db.get_all_users()
    success_count = 0
    failed_count = 0
    
    for user_id in users:
        try:
            if broadcast_data['photo']:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=broadcast_data['photo'],
                    caption=broadcast_data['text'],
                    parse_mode="HTML"
                )
            elif broadcast_data['video']:
                await bot.send_video(
                    chat_id=user_id,
                    video=broadcast_data['video'],
                    caption=broadcast_data['text'],
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=broadcast_data['text'],
                    parse_mode="HTML"
                )
            success_count += 1
        except Exception:
            failed_count += 1
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: {success_count}\n"
        f"❌ Ошибок: {failed_count}",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )
    
    await state.clear()


@router.callback_query(F.data == "broadcast_cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменить рассылку"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()
