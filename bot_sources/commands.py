from telebot.types import Message

from GoogleSheetsAPI import GoogleSync
from models import User, Group, Links, Equipment, Movement
from settings import CHANNEL_ID
from . import bot, logger, user_info, get_unauthorized_user_start_message, get_new_unauthorized_user_message, \
    get_admin_help_message, keyboard_to_chose_users_groups, groups_keyboard, get_start_keyboard, is_person


@bot.message_handler(commands=['start'])
def get_start(message: Message):
    if not is_person(message.chat):
        return
    try:
        user = User.get(telegram_id=str(message.chat.id))
        if user in User.select(User).join(Links).join(Group).where(Group.group_name == 'Unauthorized'):
            raise Exception("Unauthorized user")
    except Exception:
        logger.info('Unauthorized user')
        user, created = User.get_or_create(telegram_id=message.chat.id,
                                           first_name=message.from_user.first_name,
                                           last_name=message.from_user.last_name,
                                           status='waiting for access')
        unauth_group, created = Group.get_or_create(group_name='Unauthorized')
        Links.create(user=user, group=unauth_group)

        bot.send_message(text=get_unauthorized_user_start_message(), chat_id=message.chat.id)
        for admin in User.select(User).join(Links).join(Group).where(Group.group_name == 'Admins'):
            bot.send_message(text=get_new_unauthorized_user_message(user),
                             chat_id=admin.telegram_id,
                             reply_markup=keyboard_to_chose_users_groups(user))
        return
    bot.send_message(text=f'С возвращением, {user.first_name} {user.last_name}',
                     chat_id=message.chat.id,
                     reply_markup=get_start_keyboard(user))


@bot.message_handler(commands=['help'])
def get_help(message: Message):
    if not is_person(message.chat):
        return
    logger.info('ask for help!')
    try:
        user = User.get(telegram_id=str(message.chat.id))
        if user in User.select(User).join(Links).join(Group).where(Group.group_name == 'Unauthorized'):
            raise Exception("Unauthorized user")
    except Exception:
        bot.send_message(text=f"""Возникли вопросы? 
Напиши администратору бота (@DzenBots)""",
                         chat_id=message.chat.id)
        return
    if user in User.select(User).join(Links).join(Group).where(Group.group_name == 'Admins'):
        bot.send_message(text=get_admin_help_message(), chat_id=message.chat.id)
        return
    else:
        bot.send_message(text='Для Вас пока нет доступных команд', chat_id=message.chat.id)


@bot.message_handler(commands=['groups'])
def groups_functions(message: Message):
    if not is_person(message.chat):
        return
    try:
        user = User.get(telegram_id=message.chat.id)
        if user not in User.select(User).join(Links).join(Group).where(Group.group_name == 'Admins'):
            raise Exception("Unauthorized user")
    except Exception:
        bot.send_message(text=get_unauthorized_user_start_message(), chat_id=message.chat.id)
        return
    bot.send_message(text='Выберите действие', chat_id=message.chat.id, reply_markup=groups_keyboard)


@bot.message_handler(commands=['all_users_info'])
def show_all_users(message: Message):
    if not is_person(message.chat):
        return
    try:
        user = User.get(telegram_id=message.chat.id)
        if user not in User.select(User).join(Links).join(Group).where(Group.group_name == 'Admins'):
            raise Exception("Unauthorized user")
    except Exception:
        bot.send_message(text=get_unauthorized_user_start_message(), chat_id=message.chat.id)
        return
    for user in User.select():
        bot.send_message(text=user_info(user),
                         chat_id=message.chat.id,
                         reply_markup=keyboard_to_chose_users_groups(user))


@bot.message_handler(commands=['google_update'])
def google_update(message: Message):
    if not is_person(message.chat):
        return
    try:
        user = User.get(telegram_id=message.chat.id)
        if user not in User.select(User).join(Links).join(Group).where(Group.group_name == 'Admins'):
            raise Exception("Unauthorized user")
    except Exception:
        bot.send_message(text=get_unauthorized_user_start_message(), chat_id=message.chat.id)
        return
    cur_equipments = Equipment.select()
    cur_movement = Movement.select()
    gs = GoogleSync()
    equipments_from_google = gs.read_range(list_name='Список оборудования',
                                           range_in_list=f'A{cur_equipments.count() + 2}:G')
    movements_from_google = gs.read_range(list_name='Перемещение оборудования',
                                          range_in_list=f'A{cur_movement.count() + 2}:C')
    if equipments_from_google is not None:
        if len(equipments_from_google) > 0:
            for item in equipments_from_google:
                if len(item) < 7:
                    for j in range(len(item), 7):
                        item.append('')
                Equipment.create(it_id=item[0],
                                 pos_in_buh=item[1],
                                 invent_num=item[2],
                                 type=item[3],
                                 mark=item[4],
                                 model=item[5],
                                 serial_num=item[6])
    if movements_from_google is not None:
        if len(movements_from_google) > 0:
            for item in movements_from_google:
                if len(item) < 7:
                    for j in range(len(item), 7):
                        item.append('')
                if item[0] == '':
                    continue
                Movement.create(equipment=Equipment.get(it_id=item[0]),
                                campus=item[1],
                                room=item[2])
    bot.send_message(chat_id=user.telegram_id,
                     text='Данные получены')
    # if cur_equipments.count() <
