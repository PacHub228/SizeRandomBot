"""
FSM состояния для создания розыгрыша
"""
from aiogram.fsm.state import State, StatesGroup


class CreateGiveaway(StatesGroup):
    """Состояния для создания розыгрыша"""
    description = State()  # Ожидание описания и медиа
    button_text = State()  # Ожидание текста кнопки
    winners_count = State()  # Ожидание количества победителей
    required_channels = State()  # Ожидание списка каналов
    end_time = State()  # Ожидание времени завершения
    captcha_select = State()  # Выбор капчи
    channel_select = State()  # Выбор канала для публикации


class AdminBroadcast(StatesGroup):
    """Состояния для рассылки от администратора"""
    message = State()  # Ожидание сообщения для рассылки
