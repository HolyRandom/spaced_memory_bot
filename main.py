import os
import telebot
from telebot import types
import sqlite3
from dotenv import load_dotenv
import datetime
import threading

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    f = open('.env', 'w')
    f.write("API_KEY = 'place API here'")
    f.close()
    raise Exception('Add your API KEY in environment file .env')

API_KEY = os.environ.get("API_KEY")


bot = telebot.TeleBot(API_KEY)
main_markup = types.ReplyKeyboardMarkup()
main_markup.row('Добавить', 'Список')


def connection():
    """Connect to BD"""
    sql = sqlite3.connect('database.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    return sql


def create_table():
    """Create table for work"""
    sql = connection()
    c = sql.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks(
                user                 INTEGER,
                task_id              INTEGER PRIMARY KEY AUTOINCREMENT,
                task                 TEXT,
                notification_lvl     INTEGER,
                notification_time timestamp
                )''')
    sql.commit()


def current_lvl(task_id):
    """Get current level of notification for task"""
    sql = connection()
    c = sql.cursor()
    c.execute('''SELECT * FROM tasks  WHERE task_id=?''', (task_id,))
    return c.fetchone()[3]


def update_time(task_id, up=None):
    """Update time of notification"""
    lvl = current_lvl(task_id)
    print(lvl)
    notification = get_notification_lvl()
    if up:
        print(notification[lvl+1])
        notification_time = datetime.datetime.now() + datetime.timedelta(seconds=notification[lvl+1])
        query = '''UPDATE tasks SET notification_time=?, notification_lvl=?  WHERE task_id=?'''
        sql = connection()
        c = sql.cursor()
        c.execute(query, (notification_time, lvl+1, task_id,))
        sql.commit()
    else:
        notification_time = datetime.datetime.now() + datetime.timedelta(seconds=notification[lvl])
        query = '''UPDATE tasks SET notification_time=? WHERE task_id=?'''
        sql = connection()
        c = sql.cursor()
        c.execute(query, (notification_time,task_id,))
        sql.commit()


def send_notification():
    """Send notification about task to user"""
    threading.Timer(20.0, send_notification).start()
    query = '''SELECT * FROM tasks'''
    sql = connection()
    c = sql.cursor()
    c.execute(query)
    result = c.fetchall()
    if result:
        time = datetime.datetime.now()
        for item in result:
            if item[4] < time:
                inline_markup = types.InlineKeyboardMarkup()
                inline_button = types.InlineKeyboardButton("Сделано", callback_data=item[1])
                inline_markup.add(inline_button)
                update_time(item[1])
                bot.send_message(item[0], f'Напоминаю о задаче\n{item[2]}', reply_markup=inline_markup)


def get_notification_lvl():
    notification = {1: 1200,
                    2: 36000,
                    3: 86400,
                    4: 345600}
    return notification


def add_new_task(user_id, msg, time):
    """SQL query for add new task"""
    sql = connection()
    c = sql.cursor()
    c.execute('''INSERT INTO tasks(user, task, notification_lvl, notification_time)VALUES (?,?, 1,?)''',
              (user_id, msg, time,))
    sql.commit()
    return True


def receive_list_tasks(user_id):
    """Get list of tasks for user"""
    sql = connection()
    c = sql.cursor()
    c.execute('''SELECT * FROM tasks WHERE user=?''',
              (user_id,))
    return c.fetchall()


@bot.callback_query_handler(func=lambda call:True)
def callback_inline(call):
    """handling inline keyboard data"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    callback = int(call.data)
    update_time(callback, True)
    bot.send_message(call.message.chat.id, 'Эта задача сделана! Молодец!')


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Приветствую, я разработан для того, чтобы помочь тебе запомнить информацию. ',
                     reply_markup=main_markup)


@bot.message_handler(content_types=['text'])
def answer(message):
    if message.text == 'Добавить':
        msg = bot.send_message(message.chat.id, 'Какую задачу вы хотите добавить?')
        bot.register_next_step_handler(msg, add_task)
    elif message.text == 'Список':
        list_tasks = receive_list_tasks(message.chat.id)
        if list_tasks:
            list_done = ""
            for i in list_tasks:
                list_done += i[2] + '\n'

            bot.send_message(message.chat.id, 'Список текущих напоминаний:\n'+list_done)


def add_task(message):
    """Create new task for user"""
    notification = get_notification_lvl()
    user_id = message.chat.id
    msg = message.text
    notification_time = datetime.datetime.now() + datetime.timedelta(seconds=notification[1])
    add_status = add_new_task(user_id, msg, notification_time)
    if add_status:
        bot.send_message(user_id, f'Добавлена новая задача: \n{msg} ')


create_table()
send_notification()
bot.polling()
