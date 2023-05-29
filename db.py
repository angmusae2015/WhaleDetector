import sqlite3

def db_handler(func):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        return func(cur, conn, *args, **kwargs)

    return wrapper


# 데이터베이스에서 등록된 채팅 ID인지 확인
@db_handler
def check_user(cur, conn, chat_id):
    cur.execute("""SELECT * FROM User WHERE chat_id={0};""".format(chat_id))

    return (len(cur.fetchall()) > 0)


# 데이터베이스에 채팅 추가
@db_handler
def add_user(cur, conn, chat_id):
    cur.execute("""INSERT INTO User VALUES ({0}, {1});""".format(chat_id, 0))
    conn.commit()


# 채팅 고래 알림 설정 확인
@db_handler
def get_alarm_state(cur, conn, chat_id):
    cur.execute("""SELECT option FROM User WHERE chat_id={0};""".format(chat_id))
    return cur.fetchall()[0][0]


# 채팅 고래 알림 설정 변경
@db_handler
def change_alarm_state(cur, conn, chat_id):
    cur.execute("""SELECT option FROM User WHERE chat_id={0};""".format(chat_id))
    state = cur.fetchall()[0][0]

    cur.execute("""UPDATE User SET option={0} WHERE chat_id={1};""".format(not state, chat_id))
    conn.commit()


# 종목 ID 불러오기
@db_handler
def get_market_id(cur, conn, exchange_code, market_code):
    cur.execute("""SELECT market_id FROM Market WHERE exchange_code='{0}' and market_code='{1}';""".format(exchange_code, market_code))
    
    try:
        return cur.fetchall()[0][0]
    except IndexError:
        return None


# 채팅 알림 규칙 ID 불러오기
@db_handler
def get_rule_id(cur, conn, chat_id, exchange_code, market_code, threshold):
    market_id = get_market_id(exchange_code, market_code)
    cur.execute("""SELECT rule_id FROM Rules WHERE chat_id={0} and market_id={1} and threshold={2};""".format(chat_id, market_id, threshold))
    
    try:
        return cur.fetchall()[0][0]
    except IndexError:
        return None


# 채팅 알림 규칙 등록
@db_handler
def add_rule(cur, conn, chat_id, exchange_code, market_code, threshold):
    if get_rule_id(chat_id, exchange_code, market_code, threshold) is None:
        market_id = get_market_id(exchange_code, market_code)
        cur.execute("""INSERT INTO Rules (chat_id, market_id, threshold) VALUES ({0}, {1}, {2});""".format(chat_id, market_id, threshold))
        conn.commit()