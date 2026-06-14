"""
Обработчики управления розыгрышами
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from keyboards import get_my_giveaways_keyboard, get_giveaway_manage_keyboard
from database import Database
from handlers.participate import check_user_subscriptions
import random

router = Router()
db = Database()


@router.message(F.text == "📊 Мои конкурсы")
async def my_giveaways(message: Message):
    """Показать список розыгрышей пользователя"""
    giveaways = await db.get_user_giveaways(message.from_user.id)
    
    if not giveaways:
        await message.answer(
            "У вас пока нет созданных розыгрышей.\n"
            "Нажмите кнопку \"🎉 Создать розыгрыш\" чтобы создать первый конкурс!"
        )
        return
    
    await message.answer(
        f"📊 <b>Ваши розыгрыши ({len(giveaways)}):</b>\n\n"
        "Выберите розыгрыш для просмотра деталей:",
        reply_markup=get_my_giveaways_keyboard(giveaways),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("giveaway_info_"))
async def giveaway_info(callback: CallbackQuery):
    """Показать информацию о розыгрыше"""
    giveaway_id = int(callback.data.split("_")[2])
    
    giveaway = await db.get_giveaway(giveaway_id)
    
    if not giveaway:
        await callback.answer("❌ Розыгрыш не найден.", show_alert=True)
        return
    
    # Проверяем, что пользователь - создатель розыгрыша
    if giveaway['creator_id'] != callback.from_user.id:
        await callback.answer("❌ Это не ваш розыгрыш.", show_alert=True)
        return
    
    participants_count = await db.get_participants_count(giveaway_id)
    
    status_text = "🟢 Активен" if giveaway['status'] == 'active' else "🔴 Завершен"
    
    info_text = f"""
<b>📊 Информация о розыгрыше</b>

<b>Статус:</b> {status_text}
<b>Описание:</b> {giveaway['description'][:100]}...
<b>Количество победителей:</b> {giveaway['winners_count']}
<b>Участников:</b> {participants_count}
<b>Создан:</b> {giveaway['created_at']}
"""
    
    if giveaway['end_time'] and not giveaway['manual_end']:
        info_text += f"\n<b>Завершится:</b> {giveaway['end_time']}"
    elif giveaway['manual_end']:
        info_text += "\n<b>Завершение:</b> Вручную"
    
    if giveaway['required_channels']:
        channels_text = "\n".join([f"• {ch}" for ch in giveaway['required_channels']])
        info_text += f"\n\n<b>Обязательные подписки:</b>\n{channels_text}"
    
    await callback.message.edit_text(
        info_text,
        reply_markup=get_giveaway_manage_keyboard(giveaway_id, giveaway['status']),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    """Вернуться к списку розыгрышей"""
    giveaways = await db.get_user_giveaways(callback.from_user.id)
    
    await callback.message.edit_text(
        f"📊 <b>Ваши розыгрыши ({len(giveaways)}):</b>\n\n"
        "Выберите розыгрыш для просмотра деталей:",
        reply_markup=get_my_giveaways_keyboard(giveaways),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("finish_"))
async def finish_giveaway_manual(callback: CallbackQuery, bot: Bot):
    """Ручное завершение розыгрыша"""
    giveaway_id = int(callback.data.split("_")[1])
    
    giveaway = await db.get_giveaway(giveaway_id)
    
    if not giveaway:
        await callback.answer("❌ Розыгрыш не найден.", show_alert=True)
        return
    
    # Проверяем, что пользователь - создатель розыгрыша
    if giveaway['creator_id'] != callback.from_user.id:
        await callback.answer("❌ Это не ваш розыгрыш.", show_alert=True)
        return
    
    if giveaway['status'] != 'active':
        await callback.answer("❌ Розыгрыш уже завершен.", show_alert=True)
        return
    
    await callback.answer("🔄 Подводим итоги...", show_alert=False)
    
    # Импортируем функцию завершения розыгрыша
    from utils import finish_giveaway
    
    success = await finish_giveaway(bot, giveaway_id)
    
    if success:
        await callback.message.answer("✅ Розыгрыш успешно завершен! Победители выбраны.")
        
        # Обновляем информацию
        giveaway = await db.get_giveaway(giveaway_id)
        participants_count = await db.get_participants_count(giveaway_id)
        
        status_text = "🔴 Завершен"
        
        info_text = f"""
<b>📊 Информация о розыгрыше</b>

<b>Статус:</b> {status_text}
<b>Описание:</b> {giveaway['description'][:100]}...
<b>Количество победителей:</b> {giveaway['winners_count']}
<b>Участников:</b> {participants_count}
<b>Создан:</b> {giveaway['created_at']}
"""
        
        await callback.message.edit_text(
            info_text,
            reply_markup=get_giveaway_manage_keyboard(giveaway_id, giveaway['status']),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("❌ Не удалось завершить розыгрыш. Возможно, недостаточно участников.")


@router.callback_query(F.data.startswith("delete_"))
async def delete_giveaway_handler(callback: CallbackQuery):
    """Удаление розыгрыша"""
    giveaway_id = int(callback.data.split("_")[1])
    
    giveaway = await db.get_giveaway(giveaway_id)
    
    if not giveaway:
        await callback.answer("❌ Розыгрыш не найден.", show_alert=True)
        return
    
    # Проверяем, что пользователь - создатель розыгрыша
    if giveaway['creator_id'] != callback.from_user.id:
        await callback.answer("❌ Это не ваш розыгрыш.", show_alert=True)
        return
    
    await db.delete_giveaway(giveaway_id)
    await callback.answer("🗑️ Розыгрыш успешно удален!", show_alert=True)
    
    # Возвращаемся к списку
    await back_to_list(callback)
