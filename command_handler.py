import sqlite3
import asyncio
import aioschedule
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.apihelper import ApiTelegramException
from util import *
from question import *
import db


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


token = get_token("token.txt")
bot = TeleBot(token)
database = db.Database("database.db")


# 키보드 비활성화
def disable_keyboard(prev_message, text):
    # 이전 메시지 ID
    message_id = prev_message.message_id

    # 비활성화된 키보드 업데이트
    disabled_keyboard_markup = InlineKeyboardMarkup()
    disabled_keyboard_markup.add(InlineKeyboardButton(text=text, callback_data="none"))
    bot.edit_message_reply_markup(chat_id=prev_message.chat.id, message_id=int(message_id), reply_markup=disabled_keyboard_markup)


# '/start': 채팅 등록
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    if database.is_chat_exists(chat_id):
        bot.send_message(chat_id, "이미 등록된 사용자입니다. '/addalarm'을 입력해 알림을 추가해보세요!")

    else:
        database.add_chat(chat_id)
        bot.send_message(chat_id, "반갑습니다! 알림 설정을 받고 싶으시다면 '/addalarm'을 입력해 알림을 추가하고 '/startalarm'을 입력해주세요.")


# '/startalarm': 고래 알림 켜기
@bot.message_handler(commands=['startalarm'])
def start_alarm(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    if chat.get_alarm_option():
        bot.send_message(chat.id, "이미 알림이 켜져 있어요. '/addalarm'으로 알림을 추가해보세요. '/stopalarm'으로 알림을 끌 수 있어요.")
    
    else:
        chat.set_alarm_option(True)
        bot.send_message(chat.id, "지금부터 알림을 시작할게요! '/addalarm'으로 알림을 추가해보세요. '/stopalarm'으로 알림을 끌 수 있어요.")


# '/stopalarm': 고래 알림 끄기
@bot.message_handler(commands=['stopalarm'])
def stop_alarm(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    if chat.get_alarm_option():
        bot.send_message(chat.id, "알림을 끌게요. '/startalarm' 명령어로 언제든지 다시 킬 수 있어요.")
        chat.set_alarm_option(False)

    else:
        bot.send_message(chat.id, "이미 알림이 꺼져 있어요. '/startalarm' 명령어를 입력해 알림을 킬 수 있어요.")


# '/addchannel': 알림을 보낼 채널 등록
@bot.message_handler(commands=['addchannel'])
def ask_channel_name(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    # 취소 키보드
    markup = InlineKeyboardMarkup()
    markup.add(CancelButton())

    bot.send_message(chat.id, "등록할 채널을 뭐라고 부를까요?", reply_markup=markup)

    # 유저의 상태를 채널 이름 입력 대기 상태로 변경
    chat.set_status(1)


# 채널 이름 입력 시
@bot.message_handler(func=lambda message: database.get_chat(message.chat.id).get_status() == 1)
def set_channel_name(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    chat.set_buffer("")
    chat.add_buffer_parameter(ChannelName=message.text)

    bot.send_message(chat.id, f"이 채널의 이름을 '{message.text}'(으)로 설정할게요.")

    guide_msg = """제가 알림을 보내드릴 채널을 등록하시려면 채널의 아이디가 필요해요!
    1. 채널에 저를 초대해주세요.
    채널 우상단의 프로필 선택 > 편집 > 관리자 > 관리자 추가 > '고래잡이배' 검색 후 완료
    2. 채널 유형 '공개'로 설정
    채널 우상단의 프로필 선택 > 편집 > 채널 유형 > '공개' 선택
    3. 원하는 공개 링크로 설정해주세요.
    4. 공개 링크를 저에게 보내주세요. 예) https://t.me/..."""

    # 취소 키보드
    markup = InlineKeyboardMarkup()
    markup.add(CancelButton())
    
    bot.send_message(chat.id, guide_msg, reply_markup=markup)

    chat.set_status(2)


# 유저의 상태가 채널 ID 입력 대기 상태일 때 채널 ID 입력 시
@bot.message_handler(regexp='^https:\/\/t.me\/', func=lambda message: database.get_chat(message.chat.id).get_status() == 2)
def ask_channel_id(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = "@" + message.text.replace('https://t.me/', '')
    try:
        res = bot.send_message(channel_id, "채널을 확인하기 위한 메시지입니다.")
    except ApiTelegramException:
        bot.send_message(chat.id, "존재하지 않거나 봇이 초대되지 않은 채널이에요. 이미 봇을 초대했다면 최소 1개의 아무 메시지나 채널에 전송 후 다시 링크를 보내주세요.")
    else:
        channel_id = res.chat.id

        if database.is_channel_exists(channel_id):
            # 취소 키보드
            markup = InlineKeyboardMarkup()
            markup.add(CancelButton())

            bot.send_message(chat.id, "이미 등록된 채널입니다. 다른 채널을 입력해주세요.", reply_markup=markup)
        
        else:
            channel_name = chat.parse_buffer()['ChannelName']
            chat.add_channel(channel_id, channel_name)
            bot.send_message(chat.id, "채널을 등록했어요! '/addalarm'을 입력해 알림을 설정하세요.")
            
            chat.set_buffer("")

            # 유저의 상태를 일반 상태로 변경
            chat.set_status(0)


# '/addalarm' 입력 시 알림 등록
# 설정할 알림 채팅 유형 질문
@bot.message_handler(commands=['addalarm'])
def ask_adding_alarm_type(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")

    question = AlarmChatTypeQuestion(
        bot, chat.id, 
        "ask_exchange_for_alarm",
        "ask_channel_to_add_alarm"
    )
    question.ask()


# 알림을 설정할 채널 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_channel_to_add_alarm"))
def ask_channel_to_add_alarm(call):
    chat_id = call.message.chat.id

    disable_keyboard(prev_message=call.message, text="채널 알림")

    question = ChannelQuestion(bot, database, chat_id, "ask_exchange_for_alarm")
    question.ask()


# 알림을 받을 거래소 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_exchange_for_alarm"))
def ask_exchange_for_alarm(call):
    chat_id = call.message.chat.id

    if ':' in call.data:    # 채널 알림을 선택했을 시
        channel_id = int(call.data.split(':')[1])
        channel = database.get_channel(channel_id)
        chat = database.get_chat(chat_id)
        chat.add_buffer_parameter(ChatID=channel_id)

        disable_keyboard(prev_message=call.message, text=channel.get_name())

    else:   # 개인 채팅 알림을 선택했을 시
        disable_keyboard(prev_message=call.message, text="개인 채팅 알림")

    question = ExchangeQuestion(bot, database, chat_id, "ask_item_for_alarm")
    question.ask()


# 알림을 받을 종목 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_item_for_alarm"))
def ask_adding_alarm_item(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    exchange_id = int(call.data.split(':')[1])
    exchange = database.get_exchange(exchange_id)
    chat.add_buffer_parameter(ExchangeID=exchange_id)

    disable_keyboard(prev_message=call.message, text=exchange.get_name())

    question = ItemQuestion(bot, database, chat_id, exchange_id, "ask_alarm_type_to_add")
    question.ask()


# 알림 유형 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_alarm_type"))
def ask_alarm_type(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    item_id = int(call.data.split(':')[1])
    chat.add_buffer_parameter(ItemID=item_id)

    # 선택한 종목
    item = database.get_item(item_id)

    # 종목 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text=f"{item.get_code()}({item.get_name()})")

    question = AlarmTypeQuestion(bot, chat_id, "ask_quantity_to_add", "ask_quantity_to_add")
    question.ask()


# 알림을 받을 기준 물량 설정
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_quantity_to_add"))
def ask_quantity_to_add(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    alarm_type = call.data.split(':')[1]
    chat.add_buffer_parameter(AlarmType=alarm_type)

    # 선택한 종목
    item_id = chat.parse_buffer()['ItemID']
    item = database.get_item(item_id)

    # 알림 유형 선택 키보드 비활성화 및 키보드 생성
    if alarm_type == "WhaleAlarm":
        disable_keyboard(prev_message=call.message, text="고래 알림")
        calculator = QuantityCalculator("register_alarm", '0', item.get_currency_unit())

    elif alarm_type == "TickAlarm":
        disable_keyboard(prev_message=call.message, text="체결량 알림")
        calculator = QuantityCalculator("register_alarm", '0', item.get_unit())

    # 기준 물량 입력 요청 메시지와 키보드 전송
    bot.send_message(chat.id, "알림을 받을 기준량을 알려주세요.", reply_markup=calculator.markup)


# 알림 등록
@bot.callback_query_handler(func=lambda call: call.data.startswith('register_alarm'))
def register_alarm(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    # 입력한 기준 물량 및 단위
    value = call.data.split(':')[1]
    unit = call.data.split(':')[2]

    # 기준 물량 입력 키보드 비활성화
    disable_keyboard(prev_message=call.message, text=f"{convert_to_korean_num(value, True)} {unit}")

    # 알림 등록
    parameter = chat.parse_buffer()
    adding_chat_id = None
    if "ChatID" in parameter.keys():
        adding_chat_id = parameter["ChatID"]
    else:
        adding_chat_id = chat_id

    database.add_alarm(
        parameter["AlarmType"],
        adding_chat_id,
        parameter["ItemID"],
        float(value)
    )
    
    bot.send_message(chat.id, "알림이 성공적으로 등록되었습니다.")
    chat.set_buffer("")
    chat.set_status(0)


# '/editalarm' 입력 시 알림 편집
# 편집할 알림 유형 질문
@bot.message_handler(commands=['editalarm'])
def ask_editing_alarm_type(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")

    question = AlarmChatTypeQuestion(
        bot, chat.id, 
        "ask_alarm_to_edit",
        "ask_channel_to_edit_alarm"
    )
    question.ask()


# 편집할 채널 알림의 채널 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_channel_to_edit_alarm'))
def ask_channel_to_edit_alarm(call):
    chat_id = call.message.chat.id

    # 전 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="채널 알림")

    question = ChannelQuestion(bot, database, chat_id, "ask_alarm_to_edit")
    question.ask()


# 편집할 알림 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_alarm_to_edit'))
def ask_editing_alarm(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    if ':' in call.data:    # 채널 ID가 주어졌을 경우
        channel_id = int(call.data.split(':')[1])
        channel = database.get_channel(channel_id)
        chat.add_buffer_parameter(ChatID=channel_id)

        disable_keyboard(prev_message=call.message, text=channel.get_name())
        question = AlarmQuestion(
            bot, database, chat_id, "ask_alarm_edit_menu", channel_id
        )   # 채널의 알림 중 선택

    else:   # 개인 채팅 알림을 선택했을 경우
        disable_keyboard(prev_message=call.message, text="개인 채팅 알림")
        question = AlarmQuestion(
            bot, database, chat_id, "ask_alarm_edit_menu"
        )   # 현재 채팅의 알림 중 선택

    question.ask()


# 알림 편집 메뉴 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_alarm_edit_menu'))
def ask_alarm_edit_menu(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    alarm_id = int(call.data.split(':')[1])
    chat.add_buffer_parameter(AlarmID=alarm_id)

    # 알림 선택 키보드 비활성화
    alarm = database.get_alarm(alarm_id)
    item = alarm.get_item()
    disable_keyboard(
        prev_message=call.message,
        text=f"{item.get_code()}/{convert_to_korean_num(str(alarm.get_quantity()), True)} "
            + f"{item.get_unit() if alarm.get_type() == 'TickAlarm' else item.get_currency_unit()}"
    )

    menu_list = [("끄기", "turn_alarm_off") if alarm.is_enabled() else ("켜기", "turn_alarm_on"), ("기준 물량 편집", "edit_quantity"), ("삭제", "delete_alarm")]

    question = Question(bot, chat_id, "메뉴를 선택해주세요.", menu_list)
    question.ask()


# 선택한 알림 끄기
@bot.callback_query_handler(func=lambda call: call.data.startswith('turn_alarm_off'))
def turn_alarm_off(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()
    alarm = database.get_alarm(parameter["AlarmID"])

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="끄기")
    
    alarm.set_enabled(False)
    chat.set_buffer("")
    bot.send_message(chat.id, "해당 알림을 일시 중지했어요.")


# 선택한 알림 켜기
@bot.callback_query_handler(func=lambda call: call.data.startswith('turn_alarm_on'))
def turn_alarm_on(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()
    alarm = database.get_alarm(parameter["AlarmID"])

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="켜기")
    
    alarm.set_enabled(True)
    chat.set_buffer("")
    bot.send_message(chat.id, "해당 알림을 다시 시작할게요.")


# 선택한 알림 기준 물량 편집
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_quantity'))
def edit_quantity(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()
    alarm = database.get_alarm(parameter["AlarmID"])

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="기준 물량 편집")
    
    value = str(alarm.get_quantity())
    item = alarm.get_item()

    # 기준 물량 입력 키보드
    if alarm.get_type() == "WhaleAlarm":
        unit = item.get_currency_unit()
    elif alarm.get_type() == "TickAlarm":
        unit = item.get_unit()
    calculator = QuantityCalculator("apply_quantity", value, unit)

    # 기준 물량 입력 요청 메시지와 키보드 전송
    bot.send_message(chat.id, "알림을 받을 기준 물량을 입력해주세요.", reply_markup=calculator.markup)


# 변경한 기준 물량 입력
@bot.callback_query_handler(func=lambda call: call.data.startswith('apply_quantity'))
def apply_quantity(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()
    alarm = database.get_alarm(parameter["AlarmID"])
    
    # 입력한 기준 물량
    value = call.data.split(':')[1]
    unit = call.data.split(':')[2]

    # 기준 물량 입력 키보드 비활성화
    disable_keyboard(prev_message=call.message, text=f"{convert_to_korean_num(value)} {unit}")

    alarm.set_quantity(float(value))
    chat.set_buffer("")
    bot.send_message(chat.id, f"알림의 기준 물량을 {convert_to_korean_num(value)} {unit}으로 변경했어요.")


# 선택한 알림 삭제
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_alarm'))
def delete_alarm(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()
    database.remove_alarm(parameter["AlarmID"])

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="삭제")

    chat.set_buffer("")
    bot.send_message(chat.id, f"알림을 삭제했어요.")


# '/editchannel' 입력 시 알림 편집
# 편집할 알림 유형 질문
@bot.message_handler(commands=['editchannel'])
def ask_channel_to_edit(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")

    question = ChannelQuestion(bot, database, chat.id, "ask_channel_edit_menu")
    question.ask()


# 채널 편집 메뉴 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_channel_edit_menu"))
def ask_channel_edit_menu(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = int(call.data.split(':')[1])
    channel = database.get_channel(channel_id)
    chat.add_buffer_parameter(ChannelID=channel_id)

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text=channel.get_name())

    menu_list = [
        ("채널 확인하기", "check_channel"),
        ("알림 끄기", "turn_channel_alarm_off") if channel.get_alarm_option() else ("알림 켜기", "turn_channel_alarm_on"),
        ("이름 변경", "ask_channel_name"),
        ("삭제", "delete_channel")
    ]

    question = Question(bot, chat.id, "메뉴를 선택해주세요.", menu_list)
    question.ask()


@bot.callback_query_handler(func=lambda call: call.data.startswith("check_channel"))
def check_channel(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = chat.parse_buffer()["ChannelID"]
    
    bot.send_message(channel_id, "현재 선택한 채널입니다.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("turn_channel_alarm_off"))
def turn_channel_alarm_off(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = chat.parse_buffer()["ChannelID"]
    channel = database.get_channel(channel_id)

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="알림 끄기")

    channel.set_alarm_option(False)
    bot.send_message(chat.id, "해당 채널의 알림을 중단했어요.")

    chat.set_buffer("")


@bot.callback_query_handler(func=lambda call: call.data.startswith("turn_channel_alarm_on"))
def turn_channel_alarm_on(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = chat.parse_buffer()["ChannelID"]
    channel = database.get_channel(channel_id)

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="알림 켜기")

    channel.set_alarm_option(True)
    bot.send_message(chat.id, "해당 채널의 알림을 다시 시작했어요.")

    chat.set_buffer("")


@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_channel_name"))
def ask_channel_name(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="이름 변경")

    bot.send_message(chat.id, "변경할 이름을 입력해주세요.")
    chat.set_status(3)


@bot.message_handler(func=lambda message: database.get_chat(message.chat.id).get_status() == 3)
def change_channel_name(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = chat.parse_buffer()["ChannelID"]
    channel = database.get_channel(channel_id)
    
    channel.set_name(message.text)

    bot.send_message(chat.id, f"채널 이름을 {message.text}(으)로 변경했어요.")
    chat.set_status(0)
    chat.set_buffer("")


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_channel"))
def delete_channel(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = chat.parse_buffer()["ChannelID"]
    database.remove_channel(channel_id)

    # 메뉴 선택 키보드 비활성화
    disable_keyboard(prev_message=call.message, text="삭제")

    bot.send_message(chat.id, "해당 채널을 삭제했어요.")
    chat.set_buffer("")


# 사용자가 누른 버튼에 따라 키보드 값 변경
@bot.callback_query_handler(func=lambda call: call.data.startswith("update_keyboard"))
def update_keyboard(call):
    chat_id = call.message.chat.id

    trigger, value, unit, next_trigger, display_type = call.data.split(':')
    calculator = QuantityCalculator(next_trigger, value, unit, display_type)
    
    # 메시지의 키보드를 수정하여 업데이트
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=calculator.markup)


# 종목 질문 키보드 페이지 이동
@bot.callback_query_handler(func=lambda call: call.data.startswith("move_item_page_to"))
def move_page_to(call):
    chat_id = call.message.chat.id

    trigger, exchange_id, next_trigger, current_page = call.data.split(':')
    question = ItemQuestion(bot, database, chat_id, int(exchange_id), next_trigger, int(current_page))
    
    # 메시지의 키보드를 수정하여 업데이트
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=question.markup)


# 대화 중단
@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_dialog(call):
    disable_keyboard(prev_message=call.message, text="취소됨")
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")
    chat.set_status(0)


bot.infinity_polling()
