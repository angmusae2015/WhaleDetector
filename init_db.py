import sqlite3


conn = sqlite3.connect('database.db')
cur = conn.cursor()

# 거래소 정보 테이블
cur.execute("""CREATE TABLE Exchange (
    ExchangeID INTEGER PRIMARY KEY AUTOINCREMENT,
    ExchangeName TEXT NOT NULL
    );""")
cur.execute("""INSERT INTO Exchange (ExchangeName) VALUES ("업비트");""")
cur.execute("""INSERT INTO Exchange (ExchangeName) VALUES ("바이낸스");""")

# 종목 정보 테이블
cur.execute("""CREATE TABLE Item (
    ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemCode TEXT NOT NULL,
    ItemName TEXT NOT NULL,
    ExchangeID INTEGER NOT NULL,

    FOREIGN KEY (ExchangeID) REFERENCES Exchange(ExchangeID) ON DELETE CASCADE
    );""")
cur.execute("""INSERT INTO Item (ItemCode, ItemName, ExchangeID) VALUES ("KRW-BTC", "비트코인", 1);""")

# 채팅 설정 테이블
cur.execute("""CREATE TABLE Chat (
    ChatID INTEGER PRIMARY KEY,
    AlarmOption BOOLEAN NOT NULL DEFAULT 1,
    ChatStatus INTEGER DEFAULT 0,
    ChatBuffer TEXT DEFAULT ''
    );""")
    
# 알림 설정 규칙 테이블
cur.execute("""CREATE TABLE Alarm (
    AlarmID INTEGER PRIMARY KEY AUTOINCREMENT,
    ChatID INTEGER NOT NULL,
    ItemID INTEGER NOT NULL,
    OrderQuantity INTEGER NOT NULL,
    IsEnabled BOOLEAN NOT NULL DEFAULT 1,

    FOREIGN KEY (ChatID) REFERENCES Chat(ChatID) ON DELETE CASCADE,
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID) ON DELETE CASCADE
    );""")

# 채널 정보 테이블
cur.execute("""CREATE TABLE Channel (
    ChannelID INTEGER PRIMARY KEY,
    ChannelName TEXT NOT NULL,
    ChatID INTEGER NOT NULL,
    AlarmOption BOOLEAN NOT NULL DEFAULT 1,

    FOREIGN KEY (ChatID) REFERENCES Chat(ChatID) ON DELETE CASCADE
);""")

# 채널 알림 설정 규칙 테이블
cur.execute("""CREATE TABLE ChannelAlarm (
    ChannelAlarmID INTEGER PRIMARY KEY AUTOINCREMENT,
    ChannelID INTEGER NOT NULL,
    ItemID INTEGER NOT NULL,
    OrderQuantity INTEGER NOT NULL,
    IsEnabled BOOLEAN NOT NULL DEFAULT 1,

    FOREIGN KEY (ChannelID) REFERENCES Channel(ChannelID) ON DELETE CASCADE,
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID) ON DELETE CASCADE
    );""")

conn.commit()

print("Database file created!")