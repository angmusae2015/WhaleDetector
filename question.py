from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from util import *
import math
import db


class Question:
    bot = None
    chat_id = None
    text = ""
    button_options = []

    
    def __init__(self, bot: TeleBot, chat_id: int, text: str, button_options: list):
        self.bot = bot
        self.chat_id = chat_id
        self.text = text
        self.button_options = button_options
        self.markup = InlineKeyboardMarkup()
        
        self.add_button_options()
        self.add_cancel_button()

    
    def add_button_options(self):   
        for option in self.button_options:
            self.markup.add(InlineKeyboardButton(text=option[0], callback_data=option[1]))


    def add_cancel_button(self):
        self.markup.add(CancelButton())


    def ask(self):
        self.bot.send_message(chat_id=self.chat_id, text=self.text, reply_markup=self.markup)


class ExchangeQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, next_trigger: str):
        self.bot = bot
        self.chat_id = chat_id
        self.text = "거래소를 선택해주세요."

        exchanges = database.get_exchange()
        self.button_options = [
            (
                exchange.get_name(),
                f"{next_trigger}:{exchange.id}"
            ) for exchange in exchanges
        ]

        self.markup = InlineKeyboardMarkup()
        self.add_button_options()
        self.add_cancel_button()


class ItemQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, exchange_id: int, next_trigger: str, current_page=1):
        self.bot = bot
        self.chat_id = chat_id
        self.text = "종목을 선택해주세요."

        exchange = database.get_exchange(exchange_id)
        items = exchange.get_items()
        total_page = math.ceil(len(items) / 5)

        self.button_options = [
            (
                f"{item.get_code()}({item.get_name()})",
                f"{next_trigger}:{item.id}"
            ) for item in items[(current_page - 1) * 5 : (current_page) * 5]
        ]

        self.markup = InlineKeyboardMarkup()
        self.add_button_options()

        if total_page > 1:
            self.markup.add(
                InlineKeyboardButton(
                    text='<',
                    callback_data=f'move_item_page_to:{exchange_id}:{next_trigger}:{current_page - 1 if current_page > 1 else total_page}'
                ),
                InlineKeyboardButton(text=f'{current_page}/{total_page}', callback_data='none'),
                InlineKeyboardButton(
                    text='>',
                    callback_data=f'move_item_page_to:{exchange_id}:{next_trigger}:{current_page + 1 if current_page < total_page else 1}'
                )
            )

        self.add_cancel_button()
        

class ChannelQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, next_trigger: str):
        self.bot = bot
        self.chat_id = chat_id
        self.text = "채널을 선택해주세요."

        channels = database.get_chat(self.chat_id).get_channels()
        self.button_options = [
            (
                channel.get_name(),
                f"{next_trigger}:{channel.id}"
            ) for channel in channels
        ]

        self.markup = InlineKeyboardMarkup()
        self.add_button_options()
        self.add_cancel_button()


class AlarmTypeQuestion(Question):
    def __init__(self, bot: TeleBot, chat_id: int, whale_alarm_next_trigger: str, tick_alarm_next_trigger: str):
        self.bot = bot
        self.chat_id = chat_id
        self.text = "알림 유형을 선택해주세요."
        
        self.button_options = [
            ("고래 알림", f"{whale_alarm_next_trigger}:WhaleAlarm"),
            ("체결량 알림", f"{tick_alarm_next_trigger}:TickAlarm")
        ]

        self.markup = InlineKeyboardMarkup()
        self.add_button_options()
        self.add_cancel_button()


class AlarmChatTypeQuestion(Question):
    def __init__(self, bot: TeleBot, chat_id: int, alarm_next_trigger: str, channel_alarm_next_trigger: str):
        self.bot = bot
        self.chat_id = chat_id
        self.text = "알림 채팅 유형을 선택해주세요."
        self.button_options = [
            ("개인 채팅 알림", alarm_next_trigger),
            ("채널 알림", channel_alarm_next_trigger)
        ]

        self.markup = InlineKeyboardMarkup()
        self.add_button_options()
        self.add_cancel_button()


class AlarmQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, next_trigger: str, channel_id=None):
        self.bot = bot
        self.chat_id = chat_id
        self.text = "알림을 선택해주세요."

        alarms = []
        if channel_id == None:
            alarms = database.get_alarm(ChatID=self.chat_id)

        else:
            alarms = database.get_alarm(ChatID=channel_id)

        self.button_options = [
            (
                f"{alarm.get_item().get_code()}/{convert_to_korean_num(str(alarm.get_quantity()), True)} "
                    + f"{alarm.get_item().get_unit() if alarm.get_type() == 'TickAlarm' else alarm.get_item().get_currency_unit()} "
                    + f"({'켜짐' if alarm.is_enabled() else '꺼짐'})",
                f"{next_trigger}:{alarm.id}"
            ) for alarm in alarms
        ]

        self.markup = InlineKeyboardMarkup()
        self.add_button_options()
        self.add_cancel_button()
