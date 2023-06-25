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
    ItemUnit TEXT NOT NULL,
    CurrencyUnit TEXT NOT NULL,

    FOREIGN KEY (ExchangeID) REFERENCES Exchange(ExchangeID) ON DELETE CASCADE
);""")

# 채팅 설정 테이블
cur.execute("""CREATE TABLE Chat (
    ChatID INTEGER PRIMARY KEY,
    AlarmOption BOOLEAN NOT NULL DEFAULT 1,
    ChatStatus INTEGER DEFAULT 0,
    ChatBuffer TEXT DEFAULT ''
);""")

# 채널 정보 테이블
cur.execute("""CREATE TABLE Channel (
    ChannelID INTEGER PRIMARY KEY,
    ChannelName TEXT NOT NULL,
    AdminChatID INTEGER NOT NULL,
    AlarmOption BOOLEAN NOT NULL DEFAULT 1
);""")
    
# 알림 설정 규칙 테이블
cur.execute("""CREATE TABLE Alarm (
    AlarmID INTEGER PRIMARY KEY AUTOINCREMENT,
    AlarmType TEXT NOT NULL,
    ChatID INTEGER NOT NULL,
    ItemID INTEGER NOT NULL,
    Quantity REAL NOT NULL,
    IsEnabled BOOLEAN NOT NULL DEFAULT 1,

    FOREIGN KEY (ItemID) REFERENCES Item(ItemID) ON DELETE CASCADE
);""")

conn.commit()

print("Database file created!")