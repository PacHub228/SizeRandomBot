"""
Клавиатуры для бота
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎉 Создать розыгрыш")
    )
    builder.row(
        KeyboardButton(text="📊 Мои конкурсы"),
        KeyboardButton(text="ℹ️ Помощь")
    )
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu() -> ReplyKeyboardMarkup:
    """Меню администратора"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎉 Создать розыгрыш")
    )
    builder.row(
        KeyboardButton(text="📊 Мои конкурсы"),
        KeyboardButton(text="ℹ️ Помощь")
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопками пропуска и отмены"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⏭️ Пропустить"))
    builder.row(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)


def get_end_time_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора времени завершения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 час", callback_data="endtime_1h"),
        InlineKeyboardButton(text="3 часа", callback_data="endtime_3h")
    )
    builder.row(
        InlineKeyboardButton(text="6 часов", callback_data="endtime_6h"),
        InlineKeyboardButton(text="12 часов", callback_data="endtime_12h")
    )
    builder.row(
        InlineKeyboardButton(text="1 день", callback_data="endtime_1d"),
        InlineKeyboardButton(text="3 дня", callback_data="endtime_3d")
    )
    builder.row(
        InlineKeyboardButton(text="7 дней", callback_data="endtime_7d")
    )
    builder.row(
        InlineKeyboardButton(text="✋ Завершить вручную", callback_data="endtime_manual")
    )
    return builder.as_markup()


def get_participate_keyboard(giveaway_id: int, participants_count: int, button_text: str, bot_username: str) -> InlineKeyboardMarkup:
    """Клавиатура для участия в розыгрыше (кнопка-ссылка в бота)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"{button_text} ({participants_count})",
            url=f"https://t.me/{bot_username}?start=participate_{giveaway_id}"
        )
    )
    return builder.as_markup()


def get_finished_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для завершенного розыгрыша"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Итоги подведены", callback_data="finished")
    )
    return builder.as_markup()


def get_check_subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Клавиатура с каналами для подписки"""
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        # Убираем @ если есть
        channel_name = channel.lstrip('@')
        builder.row(
            InlineKeyboardButton(
                text=f"📢 {channel_name}",
                url=f"https://t.me/{channel_name}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")
    )
    return builder.as_markup()


def get_my_giveaways_keyboard(giveaways: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком розыгрышей пользователя"""
    builder = InlineKeyboardBuilder()
    
    for giveaway in giveaways[:10]:  # Показываем максимум 10 последних
        status_emoji = "🟢" if giveaway['status'] == 'active' else "🔴"
        # Обрезаем описание до 30 символов
        description = giveaway['description'][:30] + "..." if len(giveaway['description']) > 30 else giveaway['description']
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {description} ({giveaway['participants_count']} уч.)",
                callback_data=f"giveaway_info_{giveaway['id']}"
            )
        )
    
    return builder.as_markup()


def get_giveaway_manage_keyboard(giveaway_id: int, status: str) -> InlineKeyboardMarkup:
    """Клавиатура управления розыгрышем"""
    builder = InlineKeyboardBuilder()
    
    if status == 'active':
        builder.row(
            InlineKeyboardButton(text="🏁 Завершить розыгрыш", callback_data=f"finish_{giveaway_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить розыгрыш", callback_data=f"delete_{giveaway_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_list")
    )
    
    return builder.as_markup()


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
    )
    return builder.as_markup()


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")
    )
    return builder.as_markup()


def get_channel_select_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора канала публикации"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 Выбрать канал", callback_data="channel_select")
    )
    return builder.as_markup()


def get_captcha_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора капчи"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔒 Включить капчу", callback_data="captcha_yes"),
        InlineKeyboardButton(text="🔓 Без капчи", callback_data="captcha_no")
    )
    return builder.as_markup()
