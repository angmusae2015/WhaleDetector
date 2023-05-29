import sqlite3
import asyncio
import aioschedule
from telebot.async_telebot import AsyncTeleBot
from orderbook import Orderbook
from db import *


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


token = get_token("token.txt")
bot = AsyncTeleBot(token)


# 고래를 감시하고 알림 메시지 전송
@db_handler
async def send_whale_alarm(cur, conn):
    # 알림 규칙으로 등록된 종목만 호가 데이터를 조회
    cur.execute("""SELECT DISTINCT market_id FROM Rules;""")
    market_id_list = [id[0] for id in cur.fetchall()]
    
    for market_id in market_id_list:
        # 해당 종목 호가 불러오기
        cur.execute("""SELECT * FROM Market WHERE market_id={0};""".format(market_id))
        id, exchange_code, market_code, market_name = cur.fetchall()[0]

        orderbook = Orderbook(exchange_code, market_code)   # 종목 호가 데이터

        # 해당 종목을 알림 설정한 규칙 불러오기
        cur.execute("""SELECT * FROM Rules WHERE market_id={0};""".format(market_id))
        rule_list = cur.fetchall()
        for rule in rule_list:
            rule_id, chat_id, market_id, threshold = rule
            msg_list = orderbook.whale_alarm(threshold)  # 고래 알림 메시지 리스트

            # 알림 설정이 켜진 채팅에 알림 메시지 전송
            if get_alarm_state(chat_id):
                for msg in msg_list:
                    await bot.send_message(chat_id, msg)


# '/start' 입력 시 등록된 채팅이라면 고래 알림 시작
@bot.message_handler(commands=['start'])
async def start(message):
    chat_id = message.chat.id

    if not check_user(chat_id): # 등록이 안된 채팅이라면 데이터베이스에 채팅 ID 추가
        await bot.send_message(chat_id, "반갑습니다! 알림 설정을 받고 싶으시다면 '/startalarm'을 입력해주세요.")
        add_user(chat_id)


# '/startalarm' 입력 시 해당 채팅에 대해서 알림 수신 희망으로 설정
@bot.message_handler(commands=['startalarm'])
async def start_alarm(message):
    chat_id = message.chat.id

    if not get_alarm_state(chat_id):
        await bot.send_message(chat_id, "지금부터 설정하신 거래소와 종목에 대해서 고래 알림을 시작할게요! '/stopalarm'으로 알림을 끌 수 있어요.")
        change_alarm_state(chat_id)

        # 테스트를 위한 임의의 채팅 알림 규칙
        add_rule(chat_id, "upbit", "KRW-BTC", 2000000000)

    else:
        await bot.send_message(chat_id, "이미 고래 알림이 켜져 있어요. 고래 알림을 받을 거래소와 종목을 알려주시면 알림을 보내드려요! '/stopalarm'으로 알림을 끌 수 있어요.")


# '/endalarm' 입력 시 해당 채팅에 대해서 알림 수신 거부로 설정
@bot.message_handler(commands=['stopalarm'])
async def end_alarm(message):
    chat_id = message.chat.id

    if get_alarm_state(chat_id):
        await bot.send_message(chat_id, "고래 알림을 끌게요. '/startalarm' 명령어로 언제든지 다시 킬 수 있어요.")
        change_alarm_state(chat_id)

    else:
        await bot.send_message(chat_id, "이미 고래 알림이 꺼져 있어요. '/startalarm' 명령어를 입력해 알림을 킬 수 있어요.")


aioschedule.every(30).seconds.do(send_whale_alarm)


async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(bot.infinity_polling(), scheduler())


asyncio.run(main())