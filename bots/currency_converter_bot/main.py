import logging
import requests
import datetime
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv

from database.session import DatabaseSession
from database.models import User, History

load_dotenv()

TOKEN = os.getenv('TOKEN')
API_URL = os.getenv('API_URL')
 
logging.basicConfig(level=logging.INFO)
 
def start(update: Update, context: CallbackContext) -> None:
    logging.info('Кто-то запускает бота')
    chat_id = update.message.chat_id

    with DatabaseSession() as session:
        user = session.query(User).filter_by(chat_id=chat_id).first()
        if not user:
            user = User(chat_id=chat_id)
            session.add(user)
            session.commit()

    send_keyboard(chat_id, 'Выберите действие:', context)

def get_rate(): 
    response = requests.get(API_URL)  
    rate = response.json()['rub'] 
    return rate 
 
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    query.answer()

    with DatabaseSession() as session:
        if query.data == 'current_rate':
            logging.info('Пользователь получает текущий курс')
            rate = get_rate()
            user = session.query(User).filter_by(chat_id=chat_id).first()
            if not user:
                user = User(chat_id=chat_id)
                session.add(user)
                session.commit()
            history = History(user_id=user.id, rate=rate)
            session.add(history)
            session.commit()
            send_keyboard(chat_id, f'Текущий курс доллара: {rate} RUB', context)

        elif query.data == 'history':
            logging.info('Пользователь запрашивает историю')
            user = session.query(User).filter_by(chat_id=chat_id).first()
            if not user:
                send_keyboard(chat_id, 'История пуста.', context)
                return
            rates = session.query(History).filter_by(user_id=user.id).order_by(History.date.desc()).limit(10).all()
            message = ''
            for rate in rates:
                message += f"{rate.date.strftime('%Y-%m-%d %H:%M:%S')} - {rate.rate} RUB\n"
            send_keyboard(chat_id, message, context)

        elif query.data == 'subscribe':
            logging.info('Пользователь подписывается на обновления')
            user = session.query(User).filter_by(chat_id=chat_id).first()
            user.subscribed = True
            session.commit()
            send_keyboard(chat_id, 'Вы успешно подписались на обновления', context)

        elif query.data == 'unsubscribe':
            logging.info('Пользователь отписывается от обновлений')
            user = session.query(User).filter_by(chat_id=chat_id).first()
            user.subscribed = False
            session.commit()
            send_keyboard(chat_id, 'Вы отписались от обновлений.', context)

def send_keyboard(chat_id, message_text, context):  
    with DatabaseSession() as session:
        user = session.query(User).filter_by(chat_id=chat_id).first()  
        if user.subscribed:  
            keyboard_action = 'unsubscribe'  
            button_text = 'Отписаться от обновлений'  
        else:  
            keyboard_action = 'subscribe'  
            button_text = 'Подписаться на обновления'  
  
        keyboard = [  
            [InlineKeyboardButton('Текущий курс', callback_data='current_rate'),  
             InlineKeyboardButton('История (последние 10 запросов)', callback_data='history')],  
            [InlineKeyboardButton(button_text, callback_data=keyboard_action)]  
        ]  
  
        reply_markup = InlineKeyboardMarkup(keyboard)  
        context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)  
  
def send_daily_update(context: CallbackContext):  
    with DatabaseSession() as session:
        users = session.query(User).filter_by(subscribed=True).all()  
        rate = get_rate()  
          
        for user in users:  
            chat_id = user.chat_id  
            context.bot.send_message(chat_id, f'Ежедневное обновление: текущий курс доллара - {rate} RUB')
 
def main(): 
    updater = Updater(TOKEN) 
    dp = updater.dispatcher 
    updater.job_queue.run_daily(send_daily_update, time=datetime.time(hour=6)) 
    dp.add_handler(CommandHandler('start', start)) 
    dp.add_handler(CallbackQueryHandler(button)) 
    updater.start_polling() 
    updater.idle()
