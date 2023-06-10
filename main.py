import sqlite3
import asyncio
import aioschedule
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.apihelper import ApiTelegramException
from orderbook import Orderbook
from util import *
import db


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


# 키보드 비활성화
async def disable_keyboard(prev_message, text):
    # 이전 메시지 ID
    message_id = prev_message.message_id

    # 비활성화된 키보드 업데이트
    disabled_keyboard_markup = InlineKeyboardMarkup()
    disabled_keyboard_markup.add(InlineKeyboardButton(text=text, callback_data="none"))
    await bot.edit_message_reply_markup(chat_id=prev_message.chat.id, message_id=int(message_id), reply_markup=disabled_keyboard_markup)


token = get_token("token.txt")
bot = AsyncTeleBot(token)
DB = db.Database("database.db")


# 고래를 감시하고 알림 메시지 전송
@db.db_handler
async def send_whale_alarm(cur):
    # 알림 규칙으로 등록된 종목만 호가 데이터를 조회
    cur.execute("""SELECT DISTINCT item_id FROM Alarm;""")
    item_id_list = [id[0] for id in cur.fetchall()]
    
    for item_id in item_id_list:
        # 해당 종목 호가 불러오기
        cur.execute("""SELECT * FROM Item WHERE item_id={0};""".format(item_id))
        id, exchange_code, item_code, item_name = cur.fetchall()[0]

        orderbook = Orderbook(exchange_code, item_code)   # 종목 호가 데이터

        # 해당 종목을 알림 설정한 규칙 불러오기
        cur.execute("""SELECT * FROM Alarm WHERE item_id={0} and alarm_enabled=1;""".format(item_id))
        alarm_list = cur.fetchall()
        for alarm in alarm_list:
            alarm_id, chat_id, item_id, order_quantity, alarm_enabled = alarm
            msg_list = orderbook.whale_alarm(order_quantity)  # 고래 알림 메시지 리스트

            # 알림 설정이 켜진 채팅에 알림 메시지 전송
            if db.get_alarm_state(chat_id):
                for msg in msg_list:
                    await bot.send_message(chat_id, msg)


async def ask_exchange(chat_id: int, context=""):
    chat = DB.get_chat(chat_id)

    # 거래소 선택 키보드
    markup = InlineKeyboardMarkup()
    for exchange in DB.get_every_exchange():
        markup.add(InlineKeyboardButton(text=exchange.get_name(), callback_data=f"{context}:{exchange.id}"))
    
    # 취소 버튼
    markup.add(CancelButton())

    await bot.send_message(chat.id, "거래소를 선택해주세요.", reply_markup=markup)


async def ask_item(chat_id: int, exchange_id: int, context=""):
    chat = DB.get_chat(chat_id)
    exchange = DB.get_exchange(exchange_id)

    # 종목 선택 키보드
    markup = InlineKeyboardMarkup()
    for item in exchange.get_items():
        markup.add(InlineKeyboardButton(text=f"{item.get_code()}({item.get_name()})", callback_data=f"{context}:{item.id}"))

    # 취소 버튼
    markup.add(CancelButton())
    
    await bot.send_message(chat.id, "종목을 선택해주세요.", reply_markup=markup)


async def ask_channel(chat_id: int, context=""):
    chat = DB.get_chat(chat_id)

    markup = InlineKeyboardMarkup()
    for channel in chat.get_channels():
        markup.add(InlineKeyboardButton(text=channel.get_name(), callback_data=f"{context}:{channel.id}"))

    # 취소 버튼
    markup.add(CancelButton())

    await bot.send_message(chat.id, "채널을 선택해주세요.", reply_markup=markup)


async def ask_alarm(chat_id: int, context=""):
    chat = DB.get_chat(chat_id)

    markup = InlineKeyboardMarkup()
    for alarm in chat.get_alarms():
        item = alarm.get_item()
        markup.add(InlineKeyboardButton(text=f"{item.get_code()}/{alarm.get_order_quantity()}", callback_data=f"{context}:{alarm.id}"))

    await bot.send_message(chat.id, "알림을 선택해주세요.", reply_markup=markup)


async def ask_channel_alarm(chat_id: int, channel_id: int, context=""):
    chat = DB.get_chat(chat_id)
    channel = DB.get_channel(channel_id)

    markup = InlineKeyboardMarkup()
    for alarm in channel.get_alarms():
        item = alarm.get_item()
        markup.add(InlineKeyboardButton(text=f"{item.get_code()}/{alarm.get_order_quantity()}", callback_data=f"{context}:{alarm.id}"))

    await bot.send_message(chat.id, "알림을 선택해주세요.", reply_markup=markup)


# '/start': 채팅 등록
@bot.message_handler(commands=['start'])
async def start(message):
    chat_id = message.chat.id

    if DB.is_chat_exists(chat_id):
        await bot.send_message(chat_id, "이미 등록된 사용자입니다. '/addalarm'을 입력해 알림을 추가해보세요!")

    else:
        DB.add_chat(chat_id)
        await bot.send_message(chat_id, "반갑습니다! 알림 설정을 받고 싶으시다면 '/addalarm'을 입력해 알림을 추가하고 '/startalarm'을 입력해주세요.")


# '/startalarm': 고래 알림 켜기
@bot.message_handler(commands=['startalarm'])
async def start_alarm(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)

    if chat.get_alarm_option():
        await bot.send_message(chat.id, "이미 고래 알림이 켜져 있어요. '/addalarm'으로 알림을 추가해보세요. '/stopalarm'으로 알림을 끌 수 있어요.")
    
    else:
        chat.set_alarm_option(True)
        await bot.send_message(chat.id, "지금부터 고래 알림을 시작할게요! '/addalarm'으로 알림을 추가해보세요. '/stopalarm'으로 알림을 끌 수 있어요.")


# '/stopalarm': 고래 알림 끄기
@bot.message_handler(commands=['stopalarm'])
async def stop_alarm(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)

    if chat.get_alarm_option():
        await bot.send_message(chat.id, "고래 알림을 끌게요. '/startalarm' 명령어로 언제든지 다시 킬 수 있어요.")
        chat.set_alarm_option(False)

    else:
        await bot.send_message(chat.id, "이미 고래 알림이 꺼져 있어요. '/startalarm' 명령어를 입력해 알림을 킬 수 있어요.")


# '/addchannel': 알림을 보낼 채널 등록
@bot.message_handler(commands=['addchannel'])
async def ask_channel_name(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)

    # 취소 키보드
    markup = InlineKeyboardMarkup()
    markup.add(CancelButton())

    await bot.send_message(chat.id, "등록할 채널을 뭐라고 부를까요?", reply_markup=markup)

    # 유저의 상태를 채널 이름 입력 대기 상태로 변경
    chat.set_status(1)


# 채널 이름 입력 시
@bot.message_handler(func=lambda message: DB.get_chat(message.chat.id).get_status() == 1)
async def set_channel_name(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)

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
@bot.message_handler(regexp='^https:\/\/t.me\/', func=lambda message: DB.get_chat(message.chat.id).get_status() == 2)
async def ask_channel_id(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)

    channel_id = "@" + message.text.replace('https://t.me/', '')
    try:
        res = await bot.send_message(channel_id, "채널을 확인하기 위한 메시지입니다.")
    except ApiTelegramException:
        bot.send_message(chat.id, "존재하지 않거나 봇이 초대되지 않은 채널이에요. 이미 봇을 초대했다면 최소 1개의 아무 메시지나 채널에 전송 후 다시 링크를 보내주세요.")
    else:
        channel_id = res.chat.id

        if DB.is_channel_exists(channel_id):
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
# 알림을 받을 거래소를 선택
@bot.message_handler(commands=['addalarm'])
async def ask_alarm_exchange(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)
    chat.set_buffer("")

    await ask_exchange(message.chat.id, 'addalarm1')


# 알림을 받을 종목 선택
@bot.callback_query_handler(func=lambda call: call.data.startswith("addalarm1:"))
async def ask_alarm_item(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    exchange_id = int(call.data.replace("addalarm1:", ""))
    exchange = DB.get_exchange(exchange_id)
    chat.add_buffer_parameter(ExchangeID=exchange_id)

    await disable_keyboard(prev_message=call.message, text=exchange.get_name())

    await ask_item(chat.id, exchange.id, "addalarm2")


# 알림을 받을 주문량 설정
@bot.callback_query_handler(func=lambda call: call.data.startswith("addalarm2:"))
async def ask_alarm_order_quantity(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    item_id = int(call.data.replace("addalarm2:", ""))
    chat.add_buffer_parameter(ItemID=item_id)

    # 선택한 종목
    item = DB.get_item(item_id)

    # 종목 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=f"{item.get_code()}({item.get_name()})")

    # 주문량 입력 키보드
    calculator = OrderQuantityCalculator("addalarm3", 0)

    # 주문량 입력 요청 메시지와 키보드 전송
    await bot.send_message(chat.id, "알림을 받을 주문량을 알려주세요.", reply_markup=calculator.markup)


# 사용자가 누른 버튼에 따라 키보드 값 변경
@bot.callback_query_handler(func=lambda call: call.data.startswith('addalarm3:'))
async def update_alarm_order_quantity_keyboard(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    # 현재 주문량
    value = int(call.data.replace("addalarm3:", ""))

    # 주문량 입력 키보드
    calculator = OrderQuantityCalculator("addalarm3", value)
    
    # 메시지의 키보드를 수정하여 업데이트
    await bot.edit_message_reply_markup(chat_id=chat.id, message_id=call.message.message_id, reply_markup=calculator.markup)


# 알림 등록
@bot.callback_query_handler(func=lambda call: call.data.startswith('addalarm4:'))
async def register_alarm(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    # 입력한 주문량
    value = int(call.data.replace("addalarm4:", ""))

    # 주문량 입력 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=f"{convert_to_korean_num(value)} 원")

    # 알림 등록
    parameter = chat.parse_buffer()
    chat.add_alarm(parameter["ItemID"], value)
    
    await bot.send_message(chat.id, "알림이 성공적으로 등록되었습니다.")
    chat.set_buffer("")
    chat.set_status(0)


# '/addchannelalarm' 입력 시 채널 알림 등록
# 알림을 받을 거래소를 선택
@bot.message_handler(commands=['addchannelalarm'])
async def ask_channel_for_alarm(message):
    chat_id = message.chat.id
    chat = DB.get_chat(chat_id)
    chat.set_buffer("")

    await ask_channel(chat.id, "addchannelalarm1")


@bot.callback_query_handler(func=lambda call: call.data.startswith("addchannelalarm1:"))
async def ask_channel_alarm_exchange(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)
    chat.set_buffer("")

    # 선택한 채널
    channel_id = int(call.data.replace("addchannelalarm1:", ""))
    chat.add_buffer_parameter(ChannelID=channel_id)

    # 채널 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=DB.get_channel(channel_id).get_name())

    await ask_exchange(chat.id, "addchannelalarm2")


# 알림을 받을 종목 선택
@bot.callback_query_handler(func=lambda call: call.data.startswith("addchannelalarm2:"))
async def ask_channel_alarm_item(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    exchange_id = int(call.data.replace("addchannelalarm2:", ""))
    chat.add_buffer_parameter(ExchangeID=exchange_id)

    # 선택한 거래소
    exchange = DB.get_exchange(exchange_id)
    
    # 거래소 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=exchange.get_name())

    await ask_item(chat.id, exchange.id, "addchannelalarm3")


# 알림을 받을 주문량 설정
@bot.callback_query_handler(func=lambda call: call.data.startswith("addchannelalarm3:"))
async def ask_channel_alarm_order_quantity(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    item_id = int(call.data.replace("addchannelalarm3:", ""))
    chat.add_buffer_parameter(ItemID=item_id)

    # 선택한 종목
    item = DB.get_item(item_id)

    # 종목 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=f"{item.get_code()}({item.get_name()})")

    # 주문량 입력 키보드
    calculator = OrderQuantityCalculator("addchannelalarm4", 0)

    # 주문량 입력 요청 메시지와 키보드 전송
    await bot.send_message(chat.id, "알림을 받을 주문량을 알려주세요.", reply_markup=calculator.markup)


# 사용자가 누른 버튼에 따라 키보드 값 변경
@bot.callback_query_handler(func=lambda call: call.data.startswith('addchannelalarm4:'))
async def update_channel_alarm_order_quantity_keyboard(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    # 현재 주문량
    value = int(call.data.replace("addchannelalarm4:", ""))
    
    # 주문량 입력 키보드
    calculator = OrderQuantityCalculator("addchannelalarm4", value)
    
    # 메시지의 키보드를 수정하여 업데이트
    await bot.edit_message_reply_markup(chat_id=chat.id, message_id=call.message.message_id, reply_markup=calculator.markup)


# 알림 등록
@bot.callback_query_handler(func=lambda call: call.data.startswith('addchannelalarm5:'))
async def register_channel_alarm(call):
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    # 입력한 주문량
    value = int(call.data.replace("addchannelalarm5:", ""))

    # 주문량 입력 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=convert_to_korean_num(value))

    # 알림 등록
    parameter = chat.parse_buffer()
    channel_id = parameter["ChannelID"]
    channel = DB.get_channel(channel_id)

    item_id = parameter["ItemID"]

    channel.add_alarm(item_id, value)
    
    await bot.send_message(chat.id, "채널 알림이 성공적으로 등록되었습니다.")
    chat.set_buffer("")
    chat.set_status(0)


# @bot.message_handler(commands=['editalarm'])
# async def ask_alarm_for_edit(message):



# 대화 중단
@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
async def cancel_dialog(call):
    await disable_keyboard(prev_message=call.message, text="취소됨")
    chat_id = call.message.chat.id
    chat = DB.get_chat(chat_id)

    chat.set_status(0)


"""
aioschedule.every(30).seconds.do(send_whale_alarm)
"""

async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(bot.infinity_polling())


asyncio.run(main())