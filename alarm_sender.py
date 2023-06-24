import sqlite3
import asyncio
import aioschedule
from telebot.async_telebot import AsyncTeleBot
from upbit import Upbit
import db


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


token = get_token("token.txt")
bot = AsyncTeleBot(token)
database = db.Database("database.db")
upbit = Upbit()


whale_alarm_interval = 30
tick_alarm_interval = 5


# 고래 알림 메시지 전송
async def send_whale_alarm():
    # 활성화된 알림의 종목에 대해서만 정보를 조회
    alarm_list = database.get_alarm(IsEnabled=True, AlarmType="WhaleAlarm")
    item_id_set = set([alarm.get_item().id for alarm in alarm_list])
    for item_id in item_id_set:
        item = database.get_item(item_id)
        alarm_list = item.get_alarms(IsEnabled=True, AlarmType="WhaleAlarm")
        
        for alarm in alarm_list:
            chat = alarm.get_chat()
            whale_list = upbit.find_whale(item.get_code(), alarm.get_quantity())

            for whale in whale_list:
                if chat.get_alarm_option():
                    await bot.send_message(chat.id, whale.write_whale_msg())

    
# 체결량 알림 메시지 전송
async def send_tick_alarm():
    # 활성화된 알림의 종목에 대해서만 정보를 조회
    alarm_list = database.get_alarm(IsEnabled=True, AlarmType="TickAlarm")
    item_id_set = set([alarm.get_item().id for alarm in alarm_list])
    for item_id in item_id_set:
        item = database.get_item(item_id)
        alarm_list = item.get_alarms(IsEnabled=True, AlarmType="TickAlarm")

        ticks = upbit.get_ticks(item.get_code(), 10, count=30)  # 10초 전까지의 체결 기록을 최대 30개까지 조회
        for tick in ticks:
            for alarm in alarm_list:
                chat = alarm.get_chat()
                if chat.get_alarm_option() and tick.volume >= alarm.get_quantity():
                    await bot.send_message(chat.id, tick.write_tick_msg())


async def send_alarm():
    aioschedule.every(whale_alarm_interval).seconds.do(send_whale_alarm)
    aioschedule.every(tick_alarm_interval).seconds.do(send_tick_alarm)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    task = asyncio.create_task(send_alarm())

    await asyncio.gather(task)


asyncio.run(main())