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
    cur.execute("""CREATE TABLE Exchange (exchange_code TEXT PRIMARY KEY, exchange_name TEXT NOT NULL)""")
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
        threshold INTEGER NOT NULL,

        FOREIGN KEY (chat_id) REFERENCES User(chat_id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES Item(item_id) ON DELETE CASCADE
        );""")

    # 채널 정보 테이블
    cur.execute("""CREATE TABLE Channel (
        channel_id INTEGER PRIMARY KEY,
        channel_name TEXT,
        user_id INTEGER NOT NULL,

        FOREIGN KEY (user_id) REFERENCES User(chat_id) ON DELETE CASCADE
    )
    """)

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


# 종목 ID 불러오기
@db_handler
def get_item_id(cur, exchange_code, item_code):
    cur.execute("""SELECT item_id FROM Item WHERE exchange_code='{0}' and item_code='{1}';""".format(exchange_code, item_code))
    
    try:
        return cur.fetchall()[0][0]
    except IndexError:
        return None


@db_handler # 종목 목록 불러오기
def get_item_dic(cur, exchange_code=None, item_code=None, item_name=None):  # 조건으로 거래소 코드, 종목 코드, 종목 이름 지정 가능
    command = """SELECT * FROM Item"""  # sql 명령문
    if exchange_code != None or item_code != None or item_name != None:
        command += " WHERE"
        condition = []
        if exchange_code != None:
            condition.append(""" exchange_code='{0}'""".format(exchange_code))
        
        if item_code != None:
            condition.append(""" item_code='{0}'""".format(item_code))

        if item_name != None:
            condition.append(""" item_name='{0}'""".format(item_name))
        
        command += 'and'.join(condition)
            
    cur.execute(command)

    return {item[0]:{'exchange_code': item[1], 'item_code': item[2], 'item_name': item[3]} for item in cur.fetchall()}


# 채팅 알림 규칙 ID 불러오기
@db_handler
def get_alarm_id(cur, chat_id, exchange_code, item_code, threshold):
    item_id = get_item_id(exchange_code, item_code)
    cur.execute("""SELECT alarm_id FROM Alarm WHERE chat_id={0} and item_id={1} and threshold={2};""".format(chat_id, item_id, threshold))
    
    try:
        return cur.fetchall()[0][0]
    except IndexError:
        return None


# 채팅 알림 규칙 등록
@db_handler
def add_alarm(cur, chat_id, exchange_code, item_code, threshold):
    if get_alarm_id(chat_id, exchange_code, item_code, threshold) is None:
        item_id = get_item_id(exchange_code, item_code)
        cur.execute("""INSERT INTO Alarm (chat_id, item_id, threshold) VALUES ({0}, {1}, {2});""".format(chat_id, item_id, threshold))


@db_handler # 거래소 목록 불러오기
def get_exchange_dic(cur):
    cur.execute("""SELECT * FROM Exchange""")

    return {exchange[0]:exchange[1] for exchange in cur.fetchall()}


# 거래소 이름 불러오기
@db_handler
def get_exchange_name(cur, exchange_code=None):
    if exchange_code is None:
        cur.execute("""SELECT exchange_name FROM Exchange""")   # 매개변수 exchange_code가 None일 경우 모든 거래소 이름 반환

        return [name[0] for name in cur.fetchall()]
    else:
        cur.execute("""SELECT exchange_name FROM Exchange WHERE exchange_code='{0}'""".format(exchange_code)) # 값이 있을 경우 해당 거래소 이름 반환

        try:
            return cur.fetchall()[0][0]
        except IndexError:
            return None


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
