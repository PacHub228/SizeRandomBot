"""
Утилиты для работы с розыгрышами
"""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
import random
from typing import List, Dict, Any

from database import Database
from keyboards import get_finished_keyboard

db = Database()


async def check_winner_subscriptions(bot: Bot, user_id: int, channels: List[str]) -> bool:
    """
    Проверка подписок победителя на каналы
    Возвращает True если подписан на все каналы
    """
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    
    return True


async def select_winners(bot: Bot, participants: List[Dict[str, Any]], 
                        winners_count: int, required_channels: List[str]) -> List[Dict[str, Any]]:
    """
    Выбор победителей с проверкой подписок
    """
    winners = []
    available_participants = participants.copy()
    
    # Перемешиваем участников для случайности
    random.shuffle(available_participants)
    
    for participant in available_participants:
        if len(winners) >= winners_count:
            break
        
        # Проверяем подписки победителя
        if required_channels:
            is_subscribed = await check_winner_subscriptions(
                bot, participant['user_id'], required_channels
            )
            if not is_subscribed:
                continue  # Пропускаем отписавшихся
        
        winners.append(participant)
    
    return winners


def format_winner_mention(winner: Dict[str, Any], index: int) -> str:
    """
    Форматирование упоминания победителя
    """
    if winner.get('username'):
        return f"{index}. @{winner['username']}"
    else:
        name = winner.get('first_name', 'Пользователь')
        return f'{index}. <a href="tg://user?id={winner["user_id"]}">{name}</a>'


async def finish_giveaway(bot: Bot, giveaway_id: int) -> bool:
    """
    Завершение розыгрыша и выбор победителей
    Возвращает True если розыгрыш успешно завершен
    """
    # Получаем информацию о розыгрыше
    giveaway = await db.get_giveaway(giveaway_id)
    
    if not giveaway or giveaway['status'] != 'active':
        return False
    
    # Получаем список участников
    participants = await db.get_participants(giveaway_id)
    
    if len(participants) < giveaway['winners_count']:
        # Недостаточно участников
        return False
    
    # Выбираем победителей
    winners = await select_winners(
        bot,
        participants,
        giveaway['winners_count'],
        giveaway.get('required_channels', [])
    )
    
    if len(winners) < giveaway['winners_count']:
        # Не удалось выбрать достаточно победителей (все отписались)
        # Выбираем из оставшихся
        if not winners and participants:
            winners = random.sample(
                participants,
                min(giveaway['winners_count'], len(participants))
            )
    
    if not winners:
        return False
    
    # Сохраняем победителей в базу
    await db.add_winners(giveaway_id, winners)
    
    # Формируем текст с победителями
    winners_text = "\n".join([
        format_winner_mention(winner, i + 1)
        for i, winner in enumerate(winners)
    ])
    
    # Обновляем пост в канале
    if giveaway['chat_id'] and giveaway['message_id']:
        try:
            bot_info = await bot.get_me()
            # Получаем текущий текст сообщения
            original_text = giveaway['description']
            
            # Добавляем список победителей
            updated_text = (
                f"{original_text}\n\n"
                f"🏆 <b>Победители розыгрыша:</b>\n"
                f"{winners_text}"
            )
            
            # Обновляем сообщение
            if giveaway.get('media_type') == 'photo':
                await bot.edit_message_caption(
                    chat_id=giveaway['chat_id'],
                    message_id=giveaway['message_id'],
                    caption=updated_text,
                    reply_markup=get_finished_keyboard(),
                    parse_mode="HTML"
                )
            elif giveaway.get('media_type') == 'video':
                await bot.edit_message_caption(
                    chat_id=giveaway['chat_id'],
                    message_id=giveaway['message_id'],
                    caption=updated_text,
                    reply_markup=get_finished_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=giveaway['chat_id'],
                    message_id=giveaway['message_id'],
                    text=updated_text,
                    reply_markup=get_finished_keyboard(),
                    parse_mode="HTML"
                )
        except TelegramBadRequest as e:
            # Если не удалось обновить сообщение, продолжаем
            print(f"Не удалось обновить сообщение розыгрыша {giveaway_id}: {e}")
    
    # Отмечаем розыгрыш как завершенный
    await db.finish_giveaway(giveaway_id)
    
    # Отправляем уведомление создателю
    try:
        notification_text = (
            f"🎉 <b>Розыгрыш завершен!</b>\n\n"
            f"Выбрано победителей: {len(winners)}\n\n"
            f"🏆 <b>Победители:</b>\n"
            f"{winners_text}"
        )
        
        await bot.send_message(
            chat_id=giveaway['creator_id'],
            text=notification_text,
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    # Если есть канал публикации, отправляем туда результаты
    target_chat_id = giveaway.get('target_chat_id')
    if target_chat_id:
        try:
            channel_text = (
                f"🏆 <b>Итоги розыгрыша!</b>\n\n"
                f"Розыгрыш завершен!\n\n"
                f"🎊 <b>Поздравляем победителей:</b>\n"
                f"{winners_text}\n\n"
                f"Спасибо всем участникам!"
            )
            
            await bot.send_message(
                chat_id=target_chat_id,
                text=channel_text,
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    return True
