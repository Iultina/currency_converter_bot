import datetime
import logging
import os

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import (BadRequest, NetworkError,
                            TelegramError, TimedOut)
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Updater)
from telegram_bot_pagination import InlineKeyboardPaginator

from database.models import History, User
from database.session import DatabaseSession

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv('TOKEN')
API_URL = 'https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/usd/rub.json' 


class TelegramBot:
    def __init__(self, token: str):
        self.updater = Updater(token)
        self.dp = self.updater.dispatcher
        self.dp.add_handler(CommandHandler('start', self._start_command))
        self.dp.add_handler(CallbackQueryHandler(self._button))
        self.updater.job_queue.run_daily(self._send_daily_update, time=datetime.time(hour=6))

    def _send_keyboard(self, chat_id: int, message_text: str, context: CallbackContext) -> None:
        """
        Отправляет клавиатуру с кнопками в чат.

        :param chat_id: Идентификатор чата, куда отправляется клавиатура.
        :param message_text: Текст сообщения, сопровождающего клавиатуру.
        :param context: Объект CallbackContext для работы с контекстом бота.
        """ 
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
                InlineKeyboardButton('История', callback_data='history')],  
                [InlineKeyboardButton(button_text, callback_data=keyboard_action)]  
            ]  
    
            reply_markup = InlineKeyboardMarkup(keyboard)  
            context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup) 

    def _start_command(self, update: Update, context: CallbackContext) -> None:
        """
        Обработчик команды /start для запуска бота.

        :param update: Объект Update, содержащий информацию о сообщении от пользователя.
        :param context: Объект CallbackContext для работы с контекстом бота.
        """
        logging.info('Кто-то запускает бота')
        chat_id = update.message.chat_id

        with DatabaseSession() as session:
            user = session.query(User).filter_by(chat_id=chat_id).first()
            if not user:
                user = User(chat_id=chat_id)
                session.add(user)
                session.commit()

        self._send_keyboard(chat_id, 'Выберите действие:', context)

    def _button(self, update: Update, context: CallbackContext) -> None:
        """
        Обработчик нажатий на кнопки в чате.

        :param update: Объект Update, содержащий информацию о событии нажатия кнопки.
        :param context: Объект CallbackContext для работы с контекстом бота.
        """
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
                self._send_keyboard(chat_id, f'Текущий курс доллара: {rate} RUB', context)

            elif query.data == 'history': 
                logging.info('Пользователь запрашивает историю') 
                user = session.query(User).filter_by(chat_id=chat_id).first() 

                page = int(query.data.split('_')[1]) if '_' in query.data else 1 
                items_per_page = 5
                offset = (page - 1) * items_per_page 
                rates = session.query(History).filter_by(user_id=user.id).order_by(History.date.desc()).offset(offset).limit(items_per_page).all() 
                    
                if not user or not rates: 
                    context.bot.send_message(chat_id=chat_id, text='История пуста.') 
                    return 

                message = '' 
                for rate in rates: 
                    message += f"{rate.date.strftime('%Y-%m-%d %H:%M:%S')} - {rate.rate} RUB\n" 
                    
                total_rates = session.query(History).filter_by(user_id=user.id).count() 
                paginator = InlineKeyboardPaginator( 
                    total_rates,  
                    current_page=page, 
                    data_pattern='history_{page}' 
                ) 
                paginator.add_after(InlineKeyboardButton('Назад', callback_data='back_to_main'))   
                context.bot.send_message(chat_id=chat_id, text=message, reply_markup=paginator.markup) 

            elif query.data == 'back_to_main': 
                self._send_keyboard(chat_id, 'Выберите действие:', context)

            elif query.data == 'subscribe':
                logging.info('Пользователь подписывается на обновления')
                user = session.query(User).filter_by(chat_id=chat_id).first()
                user.subscribed = True
                session.commit()
                self._send_keyboard(chat_id, 'Вы успешно подписались на обновления', context)

            elif query.data == 'unsubscribe':
                logging.info('Пользователь отписывается от обновлений')
                user = session.query(User).filter_by(chat_id=chat_id).first()
                user.subscribed = False
                session.commit()
                self._send_keyboard(chat_id, 'Вы отписались от обновлений.', context)

    def _send_daily_update(self, context: CallbackContext) -> None:
        """
        Отправляет ежедневное обновление курса доллара подписанным пользователям.

        :param context: Объект CallbackContext для работы с контекстом бота.
        """
        with DatabaseSession() as session:
            users = session.query(User).filter_by(subscribed=True).all()  
            rate = get_rate()  
            
            for user in users:  
                chat_id = user.chat_id  
                context.bot.send_message(chat_id, f'Ежедневное обновление: текущий курс доллара - {rate} RUB')

    def run(self):
        try:
            self.updater.start_polling()
        except (TelegramError, NetworkError, TimedOut, BadRequest) as e:
            logging.error('Произошла ошибка при работе с Telegram API:', e)
        self.updater.idle()

def get_rate() -> float:
    """
    Получает текущий курс доллара из внешнего источника.

    :return: Текущий курс доллара в RUB (рублях).
    """ 
    response = requests.get(API_URL)  
    rate = response.json()['rub'] 
    return rate

def main():      
    bot = TelegramBot(TOKEN)
    bot.run()
