import sqlite3
import asyncio
import aioschedule
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from orderbook import Orderbook
import db


def get_token(file_path):
    with open(file_path, 'r') as file:
        token = file.read().strip()
    return token


# 콜백 데이터로 전송된 문자열을 파싱하여 딕셔너리로 반환
# 콜백 데이터는 '변수명1'='값'?'변수명2'='값'?... 형식으로 이루어짐
def parse_callback(callback_data):
    parameter = callback_data.split('?')
    parameter = {p.split('=')[0]:p.split('=')[1].replace("\"", '') if p.split('=')[1].startswith("\"") else int(p.split('=')[1]) for p in parameter}

    return parameter


# '변수명': '값' 형식의 딕셔너리를 콜백 데이터로 전송할 문자열로 변환
def write_callback(dic):
    callback_data = "?".join(["{0}=\"{1}".format(key, val) if type(val) == str else "{0}={1}".format(key, val) for key, val in dic.items()])
    return callback_data

# 키보드 비활성화
async def disable_keyboard(prev_message, text):
    # 이전 메시지 ID
    message_id = prev_message.message_id

    # 비활성화된 키보드 업데이트
    disabled_keyboard_markup = InlineKeyboardMarkup()
    disabled_keyboard_markup.add(InlineKeyboardButton(text=text, callback_data="context=\"none"))
    await bot.edit_message_reply_markup(chat_id=prev_message.chat.id, message_id=int(message_id), reply_markup=disabled_keyboard_markup)


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
        cur.execute("""SELECT * FROM Alarm WHERE item_id={0} and alarm_enabled=1;""".format(item_id))
        alarm_list = cur.fetchall()
        for alarm in alarm_list:
            alarm_id, chat_id, item_id, order_quantity, alarm_enabled = alarm
            msg_list = orderbook.whale_alarm(order_quantity)  # 고래 알림 메시지 리스트

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


# '/addchannelalarm' 입력 시 알림 등록
# 알림을 받을 채널 선택
@bot.message_handler(commands=['addchannelalarm'])
async def ask_channel(message):
    callback_id = db.register_callback_data(message.chat.id)

    # 유저 소유의 채널 목록
    channel_dic = db.get_table_dic('channel', user_id=message.chat.id)

    # 채널 선택 키보드
    markup = InlineKeyboardMarkup()

    for channel_id in channel_dic.keys():
        callback_dic = {
            'context': 'addalarm0',
            'id': callback_id,
            'channel_id': channel_id
        }

        channel_name = channel_dic[channel_id]['channel_name']
        markup.add(InlineKeyboardButton(text=channel_name, callback_data=write_callback(callback_dic)))
    
    # 취소 버튼
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))

    await bot.send_message(message.chat.id, "알람을 보낼 채널을 선택해주세요.", reply_markup=markup)


# 'addalarm0' 콜백 수신 시 알림 등록
# 알림을 받을 거래소를 선택
@bot.callback_query_handler(func=lambda call: parse_callback(call.data)['context'] == 'addalarm0')
async def ask_exchange_by_callback(call):
    parameter = parse_callback(call.data)
    callback_id = parameter['id']
    db.update_callback_data(callback_id, channel_id=parameter['channel_id'])

    channel_id = int(parameter['channel_id'])
    channel_name = db.get_row_by_key('channel', channel_id)['channel_name']

    # 채널 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=channel_name)

    # 저장된 전체 거래소 목록
    exchange_dic = db.get_table_dic('exchange')

    # 거래소 선택 키보드
    markup = InlineKeyboardMarkup()

    for exchange_code in exchange_dic.keys():
        callback_dic = {
            'context': 'addalarm1',
            'id': callback_id,
            'exchange_code': exchange_code
        }
        exchange_name = db.get_row_by_key('exchange', exchange_code)['exchange_name']
        #############################
        markup.add(InlineKeyboardButton(text=exchange_name, callback_data=write_callback(callback_dic)))
    
    # 취소 버튼
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))

    await bot.send_message(call.message.chat.id, "거래소를 선택해주세요.", reply_markup=markup)


# '/addalarm' 입력 시 알림 등록
# 알림을 받을 거래소를 선택
@bot.message_handler(commands=['addalarm'])
async def ask_exchange_by_command(message):
    callback_id = db.register_callback_data(call.message.chat.id)

    exchange_dic = db.get_table_dic('exchange')

    # 거래소 선택 키보드
    markup = InlineKeyboardMarkup()

    for exchange_code in exchange_dic.keys():
        callback_dic = {
            'context': 'addalarm1',
            'id': callback_id,
            'exchange': exchange_code
        }

        exchange_name = db.get_row_by_key('exchange', exchange_code)['exchange_name']
        markup.add(InlineKeyboardButton(text=exchange_name, callback_data=write_callback(callback_dic)))
    
    # 취소 버튼
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))

    await bot.send_message(message.chat.id, "거래소를 선택해주세요.", reply_markup=markup)


# 알림을 받을 종목 선택
@bot.callback_query_handler(func=lambda call: parse_callback(call.data)['context'] == 'addalarm1')
async def ask_item(call):
    parameter = parse_callback(call.data)
    callback_id = parameter['id']
    db.update_callback_data(callback_id, exchange_code=parameter['exchange_code'])

    # 선택한 거래소 코드와 이름
    exchange_code = parameter['exchange_code']
    exchange_name = db.get_row_by_key('exchange', exchange_code)['exchange_name']

    # 거래소 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text=exchange_name)

    # 선택한 거래소에 속한 모든 종목 정보
    item_dic = db.get_table_dic('item', exchange_code=exchange_code)

    # 종목 선택 키보드
    markup = InlineKeyboardMarkup()

    for item_id in item_dic.keys():
        callback_dic = {
            'context': 'addalarm2',
            'id': callback_id,
            'item_id': item_id
        }
        markup.add(InlineKeyboardButton(text="{0}({1})".format(item_dic[item_id]['item_code'], item_dic[item_id]['item_name']), callback_data=write_callback(callback_dic)))
    
    # 취소 버튼
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))
    
    await bot.send_message(call.message.chat.id, "종목을 선택해주세요.", reply_markup=markup)


# 알림을 받을 주문량 설정
@bot.callback_query_handler(func=lambda call: parse_callback(call.data)['context'] == 'addalarm2')
async def ask_order_quantity(call):
    parameter = parse_callback(call.data)
    callback_id = parameter['id']
    db.update_callback_data(callback_id, item_id=parameter['item_id'])

    # 선택한 종목 정보
    item_id = int(parameter['item_id'])
    item_code = db.get_table_dic('item', item_id=item_id)[item_id]['item_code']
    item_name = db.get_table_dic('item', item_id=item_id)[item_id]['item_name']

    # 종목 선택 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="{0}({1})".format(item_code, item_name))

    # 주문량 입력 키보드
    markup = InlineKeyboardMarkup()

    callback_dic = {
        'context': 'addalarm3',
        'id': callback_id
    }

    callback_data = write_callback(callback_dic)

    # 주문량 증가 버튼
    add_10k_button = InlineKeyboardButton(text="+1만", callback_data=callback_data + "?val={0}".format(10 ** 4))
    add_100k_button = InlineKeyboardButton(text="+10만", callback_data=callback_data + "?val={0}".format(10 ** 5))
    add_1m_button = InlineKeyboardButton(text="+100만", callback_data=callback_data + "?val={0}".format(10 ** 6))
    add_10m_button = InlineKeyboardButton(text="+1000만", callback_data=callback_data + "?val={0}".format(10 ** 7))
    add_100m_button = InlineKeyboardButton(text="+1억", callback_data=callback_data + "?val={0}".format(10 ** 8))
    add_1b_button = InlineKeyboardButton(text="+10억", callback_data=callback_data + "?val={0}".format(10 ** 9))

    # 현재 주문량 표시 버튼
    number_button = InlineKeyboardButton(text="0만원", callback_data="context=\"none\"")

    # 주문량 감소 버튼
    sub_10k_button = InlineKeyboardButton(text="-1만", callback_data=callback_data + "?val={0}".format(0))
    sub_100k_button = InlineKeyboardButton(text="-10만", callback_data=callback_data + "?val={0}".format(0))
    sub_1m_button = InlineKeyboardButton(text="-100만", callback_data=callback_data + "?val={0}".format(0))
    sub_10m_button = InlineKeyboardButton(text="-1000만", callback_data=callback_data + "?val={0}".format(0))
    sub_100m_button = InlineKeyboardButton(text="-1억", callback_data=callback_data + "?val={0}".format(0))
    sub_1b_button = InlineKeyboardButton(text="-10억", callback_data=callback_data + "?val={0}".format(0))

    # 키보드에 버튼 추가
    markup.add(add_10k_button, add_100k_button, add_1m_button, row_width=3)
    markup.add(add_10m_button, add_100m_button, add_1b_button, row_width=3)
    markup.add(number_button, row_width=3)
    markup.add(sub_10k_button, sub_100k_button, sub_1m_button, row_width=3)
    markup.add(sub_10m_button, sub_100m_button, sub_1b_button, row_width=3)

    # 취소 버튼
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))

    # 주문량 입력 요청 메시지와 키보드 전송
    await bot.send_message(call.message.chat.id, "알림을 받을 주문량을 알려주세요. (100억 미만)", reply_markup=markup)


# 사용자가 누른 버튼에 따라 키보드 값 변경
@bot.callback_query_handler(func=lambda call: parse_callback(call.data)['context'] == 'addalarm3')
async def update_order_quantity_keyboard(call):
    parameter = parse_callback(call.data)
    callback_id = parameter['id']

    # 현재 주문량
    current_val = int(parameter['val'])
    
    # 주문량 입력 키보드
    markup = InlineKeyboardMarkup()

    callback_dic = {
        'context': 'addalarm3',
        'id': callback_id
    }

    callback_data = write_callback(callback_dic)

    # 주문량 증가 버튼
    add_10k_button = InlineKeyboardButton(text="+1만", callback_data=callback_data + "?val={0}".format(current_val + 10 ** 4))
    add_100k_button = InlineKeyboardButton(text="+10만", callback_data=callback_data + "?val={0}".format(current_val + 10 ** 5))
    add_1m_button = InlineKeyboardButton(text="+100만", callback_data=callback_data + "?val={0}".format(current_val + 10 ** 6))
    add_10m_button = InlineKeyboardButton(text="+1000만", callback_data=callback_data + "?val={0}".format(current_val + 10 ** 7))
    add_100m_button = InlineKeyboardButton(text="+1억", callback_data=callback_data + "?val={0}".format(current_val + 10 ** 8))
    add_1b_button = InlineKeyboardButton(text="+10억", callback_data=callback_data + "?val={0}".format(current_val + 10 ** 9))

    # 현재 주문량 표시 버튼
    number_button = InlineKeyboardButton(text=format(int(current_val / 10000), ',') + "만원", callback_data="context=\"none")

    # 주문량 감소 버튼
    conditional_sub = lambda val, sub: val - sub if val > sub else 0
    sub_10k_button = InlineKeyboardButton(text="-1만", callback_data=callback_data + "?val={0}".format(conditional_sub(current_val, 10 ** 4)))
    sub_100k_button = InlineKeyboardButton(text="-10만", callback_data=callback_data + "?val={0}".format(conditional_sub(current_val, 10 ** 5)))
    sub_1m_button = InlineKeyboardButton(text="-100만", callback_data=callback_data + "?val={0}".format(conditional_sub(current_val, 10 ** 6)))
    sub_10m_button = InlineKeyboardButton(text="-1000만", callback_data=callback_data + "?val={0}".format(conditional_sub(current_val, 10 ** 7)))
    sub_100m_button = InlineKeyboardButton(text="-1억", callback_data=callback_data + "?val={0}".format(conditional_sub(current_val, 10 ** 8)))
    sub_1b_button = InlineKeyboardButton(text="-10억", callback_data=callback_data + "?val={0}".format(conditional_sub(current_val, 10 ** 9)))

    # 최종 입력 버튼
    submit_parameter = callback_dic.copy()
    submit_parameter['context'] = 'addalarm4'
    submit_parameter['val'] = current_val
    submit_button = InlineKeyboardButton(text="입력", callback_data=write_callback(submit_parameter))

    # 키보드에 버튼 추가
    markup.add(add_10k_button, add_100k_button, add_1m_button, row_width=3)
    markup.add(add_10m_button, add_100m_button, add_1b_button, row_width=3)
    markup.add(number_button, row_width=3)
    markup.add(sub_10k_button, sub_100k_button, sub_1m_button, row_width=3)
    markup.add(sub_10m_button, sub_100m_button, sub_1b_button, row_width=3)

    # 입력한 값이 0이 아닐 경우에만 입력 버튼 추가
    if current_val != 0:
        markup.add(submit_button, row_width=3)
    
    # 취소 버튼
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))
    
    # 메시지의 키보드를 수정하여 업데이트
    await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=int(call.message.message_id), reply_markup=markup)


# 알림 등록
@bot.callback_query_handler(func=lambda call: parse_callback(call.data)['context'] == 'addalarm4')
async def register_alarm(call):
    parameter = parse_callback(call.data)

    # 콜백 데이터 업데이트 (입력한 주문량 기록)
    callback_id = parameter['id']
    val = parameter['val']
    db.update_callback_data(callback_id, val=val)

    # 주문량 입력 키보드 비활성화
    await disable_keyboard(prev_message=call.message, text="{0}만원".format(int(val / 10000)))

    # 알림 등록
    callback_data = db.get_row_by_key('callback', callback_id)['callback_data']
    parameter = parse_callback(callback_data)
    chat_id = 0

    if 'channel_id' in parameter.keys():
        chat_id = parameter['channel_id']
    else:
        chat_id = call.message.chat.id

    db.add_alarm(chat_id=chat_id, item_id=parameter['item_id'], order_quantity=parameter['val'])
    
    await bot.send_message(call.message.chat.id, "알림이 성공적으로 등록되었습니다.")


# '/addchannel': 알림을 보낼 채널 등록
@bot.message_handler(commands=['addchannel'])
async def add_to_channel(message):
    # 취소 키보드
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="취소", callback_data="context=\"cancel"))

    guide_msg = """제가 알림을 보내드릴 채널을 등록하시려면 채널의 아이디가 필요해요!
    1. 채널에 저를 초대해주세요.
    채널 우상단의 프로필 선택 > 편집 > 관리자 > 관리자 추가 > '고래잡이배' 검색 후 완료
    2. 채널 유형 '공개'로 설정
    채널 우상단의 프로필 선택 > 편집 > 채널 유형 > '공개' 선택
    3. 원하는 공개 링크로 설정해주세요.
    4. 공개 링크를 저에게 보내주세요."""
    
    await bot.send_message(message.chat.id, guide_msg, reply_markup=markup)

    # 유저의 상태를 채널 ID 입력 대기 상태로 변경
    db.set_user_status(message.chat.id, 1)


# 유저의 상태가 채널 ID 입력 대기 상태일 때 채널 ID 입력 시
@bot.message_handler(regexp='^https:\/\/t.me\/', func=lambda message: db.get_user_status(message.chat.id) == 1)
async def get_channel_id(message):
    channel_id = "@" + message.text.replace('https://t.me/', '')
    res = await bot.send_message(channel_id, "이 채널로 알림을 보내드릴게요! 채널은 다시 비공개로 변경하셔도 좋아요.")

    # 채널 등록
    db.add_channel(res.chat.id, message.chat.id)

    await bot.send_message(message.chat.id, "이 채널의 이름을 알려주세요!")

    # 유저의 상태를 채널 이름 입력 대기 상태로 변경
    db.set_user_status(message.chat.id, 2)


# 채널 이름 입력 시
@bot.message_handler(func=lambda message: db.get_user_status(message.chat.id) == 2)
async def set_channel_name(message):
    db.set_channel_name(message.text, message.chat.id)

    await bot.send_message(message.chat.id, "이 채널의 이름을 '{0}'으로 설정했어요!".format(message.text))
    db.set_user_status(message.chat.id, 0)  # 유저의 상태를 일반 상태로 변경


# 대화 중단
@bot.callback_query_handler(func=lambda call: parse_callback(call.data)['context'] == 'cancel')
async def cancel_dialog(call):
    await disable_keyboard(prev_message=call.message, text="취소됨")
    db.set_user_status(call.message.chat.id, 0)


aioschedule.every(30).seconds.do(send_whale_alarm)


async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(bot.infinity_polling(), scheduler())


asyncio.run(main())