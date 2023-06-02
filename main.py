import sqlite3
import asyncio
import aioschedule
from telebot.async_telebot import AsyncTeleBot
from orderbook import Orderbook
import db


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


token = get_token("token.txt")
bot = AsyncTeleBot(token)


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
        cur.execute("""SELECT * FROM Alarm WHERE item_id={0};""".format(item_id))
        alarm_list = cur.fetchall()
        for alarm in alarm_list:
            alarm_id, chat_id, item_id, threshold = alarm
            msg_list = orderbook.whale_alarm(threshold)  # 고래 알림 메시지 리스트

            # 알림 설정이 켜진 채팅에 알림 메시지 전송
            if db.get_alarm_state(chat_id):
                for msg in msg_list:
                    await bot.send_message(chat_id, msg)


# '/start': 등록된 채팅이라면 고래 알림 시작
@bot.message_handler(commands=['start'])
async def start(message):
    await bot.send_message(message.chat.id, "반갑습니다! 알림 설정을 받고 싶으시다면 '/startalarm'을 입력해주세요.")


# '/startalarm': 해당 채팅에 대해서 알림 수신 희망으로 설정
@bot.message_handler(commands=['startalarm'])
async def start_alarm(message):
    if not db.check_user(message.chat.id):
        db.add_user(message.chat.id)

    if not db.get_alarm_state(message.chat.id):
        await bot.send_message(message.chat.id, "지금부터 설정하신 거래소와 종목에 대해서 고래 알림을 시작할게요! '/stopalarm'으로 알림을 끌 수 있어요.")
        db.change_alarm_state(message.chat.id)

        # 테스트를 위한 임의의 채팅 알림 규칙
        db.add_alarm(message.chat.id, "upbit", "KRW-BTC", 2000000000)

    else:
        await bot.send_message(message.chat.id, "이미 고래 알림이 켜져 있어요. 고래 알림을 받을 거래소와 종목을 알려주시면 알림을 보내드려요! '/stopalarm'으로 알림을 끌 수 있어요.")


# '/stopalarm': 해당 채팅에 대해서 알림 수신 거부로 설정
@bot.message_handler(commands=['stopalarm'])
async def end_alarm(message):
    if db.get_alarm_state(message.chat.id):
        await bot.send_message(message.chat.id, "고래 알림을 끌게요. '/startalarm' 명령어로 언제든지 다시 킬 수 있어요.")
        db.change_alarm_state(message.chat.id)

    else:
        await bot.send_message(message.chat.id, "이미 고래 알림이 꺼져 있어요. '/startalarm' 명령어를 입력해 알림을 킬 수 있어요.")


"""
# '/addalarm' 입력 시 규칙 등록
@bot.message_handler(commands=['addalarm'])
async def add_alarm(message):
    exchange_name_list = db.get_exchange_name() # 저장된 전체 거래소 목록

    markup_dic = {}
    for exchange_name in exchange_name_list:
        markup_dic[exchange_name] = {'callback_data': exchange_name}

    markup = quick_markup(markup_dic, row_width=3)  # InlineKeyboard 마크업

    await bot.send_message(message.chat.id, "어떤 거래소에서 볼까요?", reply_markup=markup)
"""


# 알림을 보낼 채널 등록
@bot.message_handler(commands=['addtochannel'])
async def add_to_channel(message):
    guide_msg = """제가 알림을 보내드릴 채널을 등록하시려면 채널의 아이디가 필요해요!
    1. 채널에 저를 초대해주세요.
    채널 우상단의 프로필 선택 > 편집 > 관리자 > 관리자 추가 > '고래잡이배' 검색 후 완료
    2. 채널 유형 '공개'로 설정
    채널 우상단의 프로필 선택 > 편집 > 채널 유형 > '공개' 선택
    3. 원하는 공개 링크로 설정해주세요.
    4. 공개 링크를 저에게 보내주세요."""
    
    await bot.send_message(message.chat.id, guide_msg)

    db.set_user_status(message.chat.id, 1)  # 유저의 상태를 채널 ID 입력 대기 상태로 변경


# 유저의 상태가 채널 ID 입력 대기 상태일 때 채널 ID 입력 시
@bot.message_handler(regexp='^https:\/\/t.me\/', func=lambda message: db.get_user_status(message.chat.id) == 1)
async def get_channel_id(message):
    channel_id = "@" + message.text.replace('https://t.me/', '')
    res = await bot.send_message(channel_id, "이 채널로 알림을 보내드릴게요! 채널은 다시 비공개로 변경하셔도 좋아요.")

    db.add_channel(res.chat.id, message.chat.id)   # 채널 등록

    await bot.send_message(message.chat.id, "이 채널의 이름을 알려주세요!")        
    db.set_user_status(message.chat.id, 2)  # 유저의 상태를 채널 이름 입력 대기 상태로 변경



# 채널 이름 입력 시
@bot.message_handler(func=lambda message: db.get_user_status(message.chat.id) == 2)
async def set_channel_name(message):
    db.set_channel_name(message.text, message.chat.id)

    await bot.send_message(message.chat.id, "이 채널의 이름을 '{0}'으로 설정했어요!".format(message.text))
    db.set_user_status(message.chat.id, 0)  # 유저의 상태를 일반 상태로 변경


aioschedule.every(30).seconds.do(send_whale_alarm)


async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(bot.infinity_polling(), scheduler())


asyncio.run(main())