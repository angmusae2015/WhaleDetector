import sqlite3
import asyncio
import aioschedule
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.apihelper import ApiTelegramException
from orderbook import Orderbook
from util import *
from question import *
import db


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


token = get_token("token.txt")
bot = AsyncTeleBot(token)
database = db.Database("database.db")


# 고래를 감시하고 알림 메시지 전송
async def send_whale_alarm():
    # 알림 규칙으로 등록된 종목만 호가 데이터를 조회
    item_list = database.get_registered_items()

    for item in item_list:
        orderbook = Orderbook(item)

        alarm_list = item.get_alarms()
        channel_alarm_list = item.get_channel_alarms()
        
        for alarm in alarm_list:
            if alarm.is_enabled() and alarm.get_chat().get_alarm_option():
                chat = alarm.get_chat()
                for msg in orderbook.whale_alarm(alarm.get_order_quantity()):
                    await bot.send_message(chat.id, msg)

        for alarm in channel_alarm_list:
            if alarm.is_enabled() and alarm.get_channel().get_alarm_option():
                channel = alarm.get_channel()
                for msg in orderbook.whale_alarm(alarm.get_order_quantity()):
                    await bot.send_message(channel.id, msg)


# 키보드 비활성화
async def disable_keyboard(prev_message, text):
    # 이전 메시지 ID
    message_id = prev_message.message_id

    # 비활성화된 키보드 업데이트
    disabled_keyboard_markup = InlineKeyboardMarkup()
    disabled_keyboard_markup.add(InlineKeyboardButton(text=text, callback_data="none"))
    await bot.edit_message_reply_markup(chat_id=prev_message.chat.id, message_id=int(message_id), reply_markup=disabled_keyboard_markup)



# '/start': 채팅 등록
@bot.message_handler(commands=['start'])
async def start(message):
    chat_id = message.chat.id

    if database.is_chat_exists(chat_id):
        await bot.send_message(chat_id, "이미 등록된 사용자입니다. '/addalarm'을 입력해 알림을 추가해보세요!")

    else:
        database.add_chat(chat_id)
        await bot.send_message(chat_id, "반갑습니다! 알림 설정을 받고 싶으시다면 '/addalarm'을 입력해 알림을 추가하고 '/startalarm'을 입력해주세요.")


# '/startalarm': 고래 알림 켜기
@bot.message_handler(commands=['startalarm'])
async def start_alarm(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    if chat.get_alarm_option():
        await bot.send_message(chat.id, "이미 고래 알림이 켜져 있어요. '/addalarm'으로 알림을 추가해보세요. '/stopalarm'으로 알림을 끌 수 있어요.")
    
    else:
        chat.set_alarm_option(True)
        await bot.send_message(chat.id, "지금부터 고래 알림을 시작할게요! '/addalarm'으로 알림을 추가해보세요. '/stopalarm'으로 알림을 끌 수 있어요.")


# '/stopalarm': 고래 알림 끄기
@bot.message_handler(commands=['stopalarm'])
async def stop_alarm(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    if chat.get_alarm_option():
        await bot.send_message(chat.id, "고래 알림을 끌게요. '/startalarm' 명령어로 언제든지 다시 킬 수 있어요.")
        chat.set_alarm_option(False)

    else:
        await bot.send_message(chat.id, "이미 고래 알림이 꺼져 있어요. '/startalarm' 명령어를 입력해 알림을 킬 수 있어요.")


# '/addchannel': 알림을 보낼 채널 등록
@bot.message_handler(commands=['addchannel'])
async def ask_channel_name(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    # 취소 키보드
    markup = InlineKeyboardMarkup()
    markup.add(CancelButton())

    await bot.send_message(chat.id, "등록할 채널을 뭐라고 부를까요?", reply_markup=markup)

    # 유저의 상태를 채널 이름 입력 대기 상태로 변경
    chat.set_status(1)


# 채널 이름 입력 시
@bot.message_handler(func=lambda message: database.get_chat(message.chat.id).get_status() == 1)
async def set_channel_name(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    chat.set_buffer("")
    chat.add_buffer_parameter(ChannelName=message.text)

    await bot.send_message(chat.id, f"이 채널의 이름을 '{message.text}'(으)로 설정할게요.")

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
    
    await bot.send_message(chat.id, guide_msg, reply_markup=markup)

    chat.set_status(2)


# 유저의 상태가 채널 ID 입력 대기 상태일 때 채널 ID 입력 시
@bot.message_handler(regexp='^https:\/\/t.me\/', func=lambda message: database.get_chat(message.chat.id).get_status() == 2)
async def ask_channel_id(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = "@" + message.text.replace('https://t.me/', '')
    try:
        res = await bot.send_message(channel_id, "채널을 확인하기 위한 메시지입니다.")
    except ApiTelegramException:
        bot.send_message(chat.id, "존재하지 않거나 봇이 초대되지 않은 채널이에요. 이미 봇을 초대했다면 최소 1개의 아무 메시지나 채널에 전송 후 다시 링크를 보내주세요.")
    else:
        channel_id = res.chat.id

        if database.is_channel_exists(channel_id):
            # 취소 키보드
            markup = InlineKeyboardMarkup()
            markup.add(CancelButton())

            await bot.send_message(chat.id, "이미 등록된 채널입니다. 다른 채널을 입력해주세요.", reply_markup=markup)
        
        else:
            channel_name = chat.parse_buffer()['ChannelName']
            chat.add_channel(channel_id, channel_name)
            await bot.send_message(chat.id, "채널을 등록했어요! '/addchannelalarm'을 입력해 채널 알림을 설정하세요.")
            
            chat.set_buffer("")

            # 유저의 상태를 일반 상태로 변경
            chat.set_status(0)


# '/addalarm' 입력 시 알림 등록
# 설정할 알림 유형 질문
@bot.message_handler(commands=['addalarm'])
async def ask_adding_alarm_type(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")

    question = AlarmTypeQuestion(
        bot, database, chat.id, 
        "ask_exchange_for_alarm",
        "ask_channel_to_add_alarm"
    )
    await question.ask()


# 알림을 설정할 채널 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_channel_to_add_alarm"))
async def ask_channel_to_add_alarm(call):
    chat_id = call.message.chat.id

    await disable_keyboard(prev_message=call.message, text="채널 알림")

    question = ChannelQuestion(bot, database, chat_id, "ask_exchange_for_alarm")
    await question.ask()


# 알림을 받을 거래소 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_exchange_for_alarm"))
async def ask_exchange_for_alarm(call):
    chat_id = call.message.chat.id

    if ':' in call.data:
        channel_id = int(call.data.split(':')[1])
        chat = database.get_chat(chat_id)
        chat.add_buffer_parameter(ChannelID=channel_id)

    await disable_keyboard(prev_message=call.message, text="개인 채팅 알림")

    question = ExchangeQuestion(bot, database, chat_id, "ask_item_for_alarm")
    await question.ask()


# 알림을 받을 종목 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_item_for_alarm"))
async def ask_adding_alarm_item(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    exchange_id = int(call.data.split(':')[1])
    exchange = database.get_exchange(exchange_id)
    chat.add_buffer_parameter(ExchangeID=exchange_id)

    await disable_keyboard(prev_message=call.message, text=exchange.get_name())

    question = ItemQuestion(bot, database, chat_id, exchange_id, "ask_quantity_to_add")
    await question.ask()


# 알림을 받을 기준 물량 설정
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_quantity_to_add"))
async def ask_adding_alarm_order_quantity(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    item_id = int(call.data.split(':')[1])
    chat.add_buffer_parameter(ItemID=item_id)

    # 선택한 종목
    item = database.get_item(item_id)

    # 종목 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=f"{item.get_code()}({item.get_name()})")

    # 기준 물량 입력 키보드
    calculator = OrderQuantityCalculator("register_alarm", 0)

    # 기준 물량 입력 요청 메시지와 키보드 전송
    await bot.send_message(chat.id, "알림을 받을 기준 물량을 알려주세요.", reply_markup=calculator.markup)


# 알림 등록
@bot.callback_query_handler(func=lambda call: call.data.startswith('register_alarm'))
async def register_alarm(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    # 입력한 기준 물량
    value = int(call.data.split(':')[1])

    # 기준 물량 입력 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=f"{convert_to_korean_num(value)} 원")

    # 알림 등록
    parameter = chat.parse_buffer()
    if "ChannelID" in parameter.keys():
        channel = database.get_channel(parameter["ChannelID"])
        channel.add_alarm(parameter["ItemID"], value)
    else:
        chat.add_alarm(parameter["ItemID"], value)
    
    await bot.send_message(chat.id, "알림이 성공적으로 등록되었습니다.")
    chat.set_buffer("")
    chat.set_status(0)


# 알림 설정 편집
@bot.message_handler(commands=['editalarm'])
async def ask_editing_alarm_type(message):
    chat_id = message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")

    question = AlarmTypeQuestion(
        bot, database, chat.id, 
        "ask_alarm_to_edit",
        "ask_channel_to_edit_alarm"
    )
    await question.ask()


# 편집할 알림 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_alarm_to_edit'))
async def ask_editing_alarm(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    # 전 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="개인 채팅 알림")

    question = AlarmQuestion(
        bot, database, chat.id, "ask_alarm_edit_menu"
    )
    await question.ask()


# 편집할 채널 알림의 채널 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_channel_to_edit_alarm'))
async def ask_channel_to_edit_alarm(call):
    chat_id = call.message.chat.id

    # 전 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="채널 알림")

    question = ChannelQuestion(bot, database, chat_id, "ask_channel_alarm_to_edit")
    await question.ask()


# 편집할 채널 알림 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_channel_alarm_to_edit'))
async def ask_channel_alarm_to_edit(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    channel_id = int(call.data.split(':')[1])
    channel = database.get_channel(channel_id)
    chat.add_buffer_parameter(ChannelID=channel_id)

    # 전 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=channel.get_name())

    question = ChannelAlarmQuestion(bot, database, chat_id, channel_id, "ask_alarm_edit_menu")
    await question.ask()


# 알림 편집 메뉴 질문
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_alarm_edit_menu'))
async def ask_alarm_edit_menu(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    alarm_id = int(call.data.split(':')[1])

    parameter = chat.parse_buffer()

    if "ChannelID" in parameter.keys():
        alarm = database.get_channel_alarm(alarm_id)
        chat.add_buffer_parameter(ChannelAlarmID=alarm_id)
    else:
        alarm = database.get_alarm(alarm_id)
        chat.add_buffer_parameter(AlarmID=alarm_id)

    # 알림 선택 키보드 비활성화
    item = alarm.get_item()
    await disable_keyboard(prev_message=call.message, text=f"{item.get_code()}/{convert_to_korean_num(alarm.get_order_quantity())} 원")

    menu_list = [("끄기", "turn_alarm_off") if alarm.is_enabled() else ("켜기", "turn_alarm_on"), ("기준 물량 편집", "edit_order_quantity"), ("삭제", "delete_alarm")]

    # 메뉴 선택 키보드
    markup = InlineKeyboardMarkup()
    for menu in menu_list:
        markup.add(InlineKeyboardButton(text=f"{menu[0]}", callback_data=f"{menu[1]}_alarm"))

    # 취소 버튼
    markup.add(CancelButton())
    
    await bot.send_message(chat.id, "메뉴를 선택해주세요.", reply_markup=markup)


# 선택한 알림 끄기
@bot.callback_query_handler(func=lambda call: call.data.startswith('turn_alarm_off'))
async def turn_alarm_off(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()

    if "ChannelAlarmID" in parameter.keys():
        alarm_id = parameter['ChannelAlarmID']
        alarm = database.get_channel_alarm(alarm_id)
    elif "AlarmID" in parameter.keys():
        alarm_id = parameter['AlarmID']
        alarm = database.get_alarm(alarm_id)

    # 메뉴 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="끄기")
    
    alarm.set_enabled(False)
    chat.set_buffer("")
    await bot.send_message(chat.id, "해당 알림을 일시 중지했어요.")


# 선택한 알림 켜기
@bot.callback_query_handler(func=lambda call: call.data.startswith('turn_alarm_on'))
async def turn_alarm_on(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()

    if "ChannelAlarmID" in parameter.keys():
        alarm_id = parameter['ChannelAlarmID']
        alarm = database.get_channel_alarm(alarm_id)
    elif "AlarmID" in parameter.keys():
        alarm_id = parameter['AlarmID']
        alarm = database.get_alarm(alarm_id)

    # 메뉴 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="켜기")
    
    alarm.set_enabled(True)
    chat.set_buffer("")
    await bot.send_message(chat.id, "해당 알림을 다시 시작할게요.")


# 선택한 알림 기준 물량 편집
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_order_quantity'))
async def edit_order_quantity(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()

    if "ChannelAlarmID" in parameter.keys():
        alarm_id = parameter['ChannelAlarmID']
        alarm = database.get_channel_alarm(alarm_id)
    elif "AlarmID" in parameter.keys():
        alarm_id = parameter['AlarmID']
        alarm = database.get_alarm(alarm_id)

    # 메뉴 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="기준 물량 편집")
    
    value = alarm.get_order_quantity()

    # 기준 물량 입력 키보드
    calculator = OrderQuantityCalculator("apply_quantity", value)

    # 기준 물량 입력 요청 메시지와 키보드 전송
    await bot.send_message(chat.id, "알림을 받을 기준 물량을 입력해주세요.", reply_markup=calculator.markup)


# 변경한 기준 물량 입력
@bot.callback_query_handler(func=lambda call: call.data.startswith('apply_quantity'))
async def apply_order_quantity(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()

    if "ChannelAlarmID" in parameter.keys():
        alarm_id = parameter['ChannelAlarmID']
        alarm = database.get_channel_alarm(alarm_id)
    elif "AlarmID" in parameter.keys():
        alarm_id = parameter['AlarmID']
        alarm = database.get_alarm(alarm_id)
    
    # 입력한 기준 물량
    value = int(call.data.split(':')[1])

    # 기준 물량 입력 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=f"{convert_to_korean_num(value)} 원")

    alarm.set_order_quantity(value)
    chat.set_buffer("")
    await bot.send_message(chat.id, f"알림의 기준 물량을 {convert_to_korean_num(value)} 원으로 변경했어요.")


# 선택한 알림 삭제
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_alarm'))
async def delete_alarm(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    parameter = chat.parse_buffer()

    if "ChannelAlarmID" in parameter.keys():
        alarm_id = parameter['ChannelAlarmID']
        database.remove_channel_alarm(alarm_id)
    elif "AlarmID" in parameter.keys():
        alarm_id = parameter['AlarmID']
        database.remove_alarm(alarm_id)

    # 메뉴 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="삭제")

    chat.set_buffer("")
    await bot.send_message(chat.id, f"알림을 삭제했어요.")


# 사용자가 누른 버튼에 따라 키보드 값 변경
@bot.callback_query_handler(func=lambda call: call.data.startswith("update_keyboard"))
async def update_adding_alarm_order_quantity_keyboard(call):
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)

    # 현재 기준 물량
    value = int(call.data.split(':')[1])

    # 기준 물량 입력 키보드
    next_trigger = call.data.split(':')[2]
    calculator = OrderQuantityCalculator(next_trigger, value)
    
    # 메시지의 키보드를 수정하여 업데이트
    await bot.edit_message_reply_markup(chat_id=chat.id, message_id=call.message.message_id, reply_markup=calculator.markup)


# 대화 중단
@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
async def cancel_dialog(call):
    await disable_keyboard(prev_message=call.message, text="취소됨")
    chat_id = call.message.chat.id
    chat = database.get_chat(chat_id)
    chat.set_buffer("")
    chat.set_status(0)


aioschedule.every(30).seconds.do(send_whale_alarm)


async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(bot.infinity_polling(), scheduler())


asyncio.run(main())