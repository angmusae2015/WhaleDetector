import time
import sqlite3


def db_handler(func):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        f = func(cur, *args, **kwargs)
        conn.commit()

        return f

    return wrapper


# 데이터베이스 초기화
@db_handler
def init_db(cur):
    status_code = ["none", "waiting_for_channel_id", "waiting_for_channel_name"]    # 채팅 상태 코드 리스트

    # 거래소 정보 테이블
    cur.execute("""CREATE TABLE Exchange (
        exchange_code TEXT PRIMARY KEY,
        exchange_name TEXT NOT NULL
        );""")
    cur.execute("""INSERT INTO Exchange VALUES ("upbit", "업비트");""")
    cur.execute("""INSERT INTO Exchange VALUES ("binance", "바이낸스");""")

    # 종목 정보 테이블
    cur.execute("""CREATE TABLE Item (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        exchange_code TEXT NOT NULL,
        item_code TEXT NOT NULL,
        item_name TEXT NOT NULL,

        FOREIGN KEY (exchange_code) REFERENCES Exchange(exchange_code) ON DELETE CASCADE
        );""")
    cur.execute("""INSERT INTO Item (exchange_code, item_code, item_name) VALUES ("upbit", "KRW-BTC", "비트코인");""")

    # 채팅 상태 테이블
    cur.execute("""CREATE TABLE Status (
        status_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status_code TEXT
        );""")

    # 채팅 상태 코드 입력
    for code in status_code:
        cur.execute("""INSERT INTO Status VALUES ({0}, "{1}");""".format(status_code.index(code), code))

    # 유저(채팅) 설정 테이블
    cur.execute("""CREATE TABLE User (
        chat_id INTEGER PRIMARY KEY,
        option BOOLEAN NOT NULL,
        status_id INTEGER DEFAULT 0,

        FOREIGN KEY (status_id) REFERENCES Status(status_id) ON DELETE CASCADE
        );""")
    
    # 알림 설정 규칙 테이블
    cur.execute("""CREATE TABLE Alarm (
        alarm_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        order_quantity INTEGER NOT NULL,
        alarm_enabled BOOLEAN NOT NULL DEFAULT 1,

        FOREIGN KEY (chat_id) REFERENCES User(chat_id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES Item(item_id) ON DELETE CASCADE
        );""")

    # 채널 정보 테이블
    cur.execute("""CREATE TABLE Channel (
        channel_id INTEGER PRIMARY KEY,
        channel_name TEXT,
        user_id INTEGER NOT NULL,

        FOREIGN KEY (user_id) REFERENCES User(chat_id) ON DELETE CASCADE
    );""")

    # 콜백 데이터 저장 테이블
    cur.execute("""CREATE TABLE Callback (
        callback_id TEXT PRIMARY KEY,
        chat_id INTEGER NOT NULL,
        callback_data TEXT,

        FOREIGN KEY (chat_id) REFERENCES User(chat_id) ON DELETE CASCADE
    );""")


# 데이터베이스에서 테이블 딕셔너리로 반환
# table_name: 테이블 이름, kwargs: 조건
@db_handler
def get_table_dic(cur, table_name, **kwargs):
    # 컬럼 조회 기능 추가 예정
    # column = ', '.join(args)
    # command = "SELECT {0} FROM {1}".format(column, table_name)

    command = "SELECT * FROM {0}".format(table_name)
    
    # 조건 지정
    condition = []
    for key, value in kwargs.items():
        if type(value) == int or type(value) == float:
            condition.append(" {0}={1}".format(key, value))
        elif type(value) == str:
            condition.append(" {0}='{1}'".format(key, value))
    
    if len(condition) > 0:
        command += " WHERE" + ' and'.join(condition)
    
    # 명령문 실행
    cur.execute(command)

    # 딕셔너리로 변환
    dic = {}
    for row in cur.fetchall():
        dic[row[0]] = {}
        for column in cur.description[1:]:
            dic[row[0]][column[0]] = row[cur.description.index(column)]
    
    return dic


# 기본 키로 데이터 검색
def get_row_by_key(table_name, primary_key):
    return get_table_dic(table_name)[primary_key]


# 콜백 데이터 등록
@db_handler
def register_callback_data(chat_id, callback_data):
    callback_id = "{0}-{1}".format(time.time(), chat_id)

    cur.execute("""INSERT INTO Callback VALUES ('{0}', {1}, '{2}');""".format(callback_id, chat_id, callback_data))

    # 등록된 콜백 데이터의 id 반환
    return callback_id


# 콜백 데이터 수정
@db_handler
def update_callback_data(callback_id, callback_data):
    cur.execute("""UPDATE Callback SET callback_data='{0}' WHERE callback_id={1}""".format(callback_data, callback_id))


# 데이터베이스에서 등록된 채팅 ID인지 확인
@db_handler
def check_user(cur, chat_id):
    cur.execute("""SELECT * FROM User WHERE chat_id={0};""".format(chat_id))

    return (len(cur.fetchall()) > 0)


# 데이터베이스에 채팅 ID 추가
@db_handler
def add_user(cur, chat_id):
    cur.execute("""INSERT INTO User VALUES ({0}, {1}, {1});""".format(chat_id, 0))


# 유저 상태 불러오기
@db_handler
def get_user_status(cur, chat_id):
    cur.execute("""SELECT status_id FROM User WHERE chat_id={0}""".format(chat_id))
    
    return cur.fetchall()[0][0]


# 유저 상태 변경
@db_handler
def set_user_status(cur, chat_id, status_id):
    cur.execute("""UPDATE User SET status_id={0} WHERE chat_id={1}""".format(status_id, chat_id))


# 채팅 고래 알림 설정 확인
@db_handler
def get_alarm_state(cur, chat_id):
    cur.execute("""SELECT option FROM User WHERE chat_id={0};""".format(chat_id))
    return cur.fetchall()[0][0]


# 채팅 고래 알림 설정 변경
@db_handler
def change_alarm_state(cur, chat_id):
    cur.execute("""SELECT option FROM User WHERE chat_id={0};""".format(chat_id))
    state = cur.fetchall()[0][0]

    cur.execute("""UPDATE User SET option={0} WHERE chat_id={1};""".format(not state, chat_id))


# 채팅 알림 규칙 ID 불러오기
@db_handler
def get_alarm_id(cur, chat_id, item_id, order_quantity):
    cur.execute("""SELECT alarm_id FROM Alarm WHERE chat_id={0} and item_id={1} and order_quantity={2};""".format(chat_id, item_id, order_quantity))
    
    try:
        return cur.fetchall()[0][0]
    except IndexError:
        return None


# 채팅 알림 규칙 등록
@db_handler
def add_alarm(cur, chat_id, item_id, order_quantity, alarm_enabled=1):
    if get_alarm_id(chat_id=chat_id, item_id=item_id, order_quantity=order_quantity) is None:
        cur.execute("""INSERT INTO Alarm (chat_id, item_id, order_quantity, alarm_enabled) VALUES ({0}, {1}, {2}, {3});""".format(chat_id, item_id, order_quantity, alarm_enabled))


# 채널 추가
@db_handler
def add_channel(cur, channel_id, chat_id):
    cur.execute("""INSERT INTO channel VALUES ({0}, '{1}', {1})""".format(channel_id, chat_id))  # channel_name은 임시로 유저의 chat_id로 설정


# 채널 이름 설정
@db_handler
def set_channel_name(cur, channel_name, chat_id):
    cur.execute("""UPDATE channel SET channel_name='{0}' WHERE channel_name='{1}'""".format(channel_name, chat_id))


# 유저의 채널 불러오기
@db_handler
def get_channels_by_user(cur, chat_id: int):
    cur.execute("""SELECT channel_id, channel_name FROM channel WHERE user_id={0}""".format(chat_id))

    return cur.fetchall()
