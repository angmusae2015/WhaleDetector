from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from util import *
import db


class Question:
    bot = None
    database = None
    chat = None
    text = ""
    button_options = []

    
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, text: str, button_options: list):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = text
        self.button_options = button_options


    def ask(self):
        markup = InlineKeyboardMarkup()
        
        for option in self.button_options:
            markup.add(InlineKeyboardButton(text=option[0], callback_data=option[1]))

        markup.add(CancelButton())

        self.bot.send_message(chat_id=self.chat.id, text=self.text, reply_markup=markup)


class ExchangeQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, next_trigger: str):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = "거래소를 선택해주세요."

        exchanges = self.database.get_exchange()
        self.button_options = [
            (
                exchange.get_name(),
                f"{next_trigger}:{exchange.id}"
            ) for exchange in exchanges
        ]


class ItemQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, exchange_id, next_trigger: str):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = "종목을 선택해주세요."

        exchange = self.database.get_exchange(exchange_id)
        items = exchange.get_items()
        self.button_options = [
            (
                f"{item.get_code()}({item.get_name()})",
                f"{next_trigger}:{item.id}"
            ) for item in items
        ]


class ChannelQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, next_trigger: str):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = "채널을 선택해주세요."

        channels = self.chat.get_channels()
        self.button_options = [
            (
                channel.get_name(),
                f"{next_trigger}:{channel.id}"
            ) for channel in channels
        ]


class AlarmTypeQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, whale_alarm_next_trigger: str, tick_alarm_next_trigger: str):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = "알림 유형을 선택해주세요."
        
        self.button_options = [
            ("고래 알림", f"{whale_alarm_next_trigger}:WhaleAlarm"),
            ("체결량 알림", f"{tick_alarm_next_trigger}:TickAlarm")
        ]


class AlarmChatTypeQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, alarm_next_trigger: str, channel_alarm_next_trigger: str):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = "알림 채팅 유형을 선택해주세요."
        self.button_options = [
            ("개인 채팅 알림", alarm_next_trigger),
            ("채널 알림", channel_alarm_next_trigger)
        ]


class AlarmQuestion(Question):
    def __init__(self, bot: TeleBot, database: db.Database, chat_id: int, next_trigger: str, channel_id=None):
        self.bot = bot
        self.database = database
        self.chat = self.database.get_chat(chat_id)
        self.text = "알림을 선택해주세요."

        alarms = []
        if channel_id == None:
            alarms = self.database.get_alarm(ChatID=chat_id)

        else:
            alarms = self.database.get_alarm(ChatID=channel_id)

        self.button_options = [
            (
                f"{alarm.get_item().get_code()}/{convert_to_korean_num(str(alarm.get_quantity()), True)} "
                    + f"{alarm.get_item().get_unit() if alarm.get_type() == 'TickAlarm' else alarm.get_item().get_currency_unit()} "
                    + f"({'켜짐' if alarm.is_enabled() else '꺼짐'})",
                f"{next_trigger}:{alarm.id}"
            ) for alarm in alarms
        ]
