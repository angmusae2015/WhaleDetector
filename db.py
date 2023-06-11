from databasetypes import *
import time
import sqlite3


class ResultSet:
    def __init__(self, column: list, result_set: list):
        self.column = column
        self.result_set = result_set


    def to_dict(self) -> dict:
        dic = {}
        for row in self.result_set:
            primary_key = row[0]
            dic[primary_key] = {key:val for key, val in zip(self.column, row)}

        return dic


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    
    def execute(self, query: str) -> ResultSet:
        # 디버그용 코드
        # print("================")
        # print(f"Query: {query}")
        
        self.cursor.execute(query)
        self.conn.commit()

        try:
            column = [tu[0] for tu in self.cursor.description]
            result_set = self.cursor.fetchall()

            # 디버그용 코드
            # print(f"Result: {result_set}")
        except TypeError:
            return ResultSet([], [])
        else:
            return ResultSet(column, result_set)

    
    def get_columns(self, table_name: str) -> list:
        result_set = self.execute(f"PRAGMA table_info({table_name});")

        return [row[1] for row in result_set.result_set]


    def select(self, table_name: str, **kwargs) -> ResultSet:
        query = f"SELECT * FROM {table_name}"
    
        # 조건 지정
        condition = []
        for key, value in kwargs.items():
            if type(value) == int or type(value) == float:
                condition.append(f" {key}={value}")
            elif type(value) == str:
                condition.append(f" {key}='{value}'")
        
        if len(condition) > 0:
            query += " WHERE" + ' AND'.join(condition)

        return self.execute(query)
    

    def insert(self, table_name: str, **kwargs) -> int:
        column_list_state = f" ({', '.join(kwargs.keys())})"

        value_list = []
        for value in kwargs.values():
            if type(value) == str:
                value_list.append(f"'{value}'")
            else:
                value_list.append(f"{value}")

        query = f"INSERT INTO {table_name}{column_list_state} VALUES ({', '.join(value_list)});"

        self.execute(query)
        id = self.execute("SELECT last_insert_rowid();").result_set[0][0]
        
        return id

    
    def update(self, table_name: str, id: int, **kwargs):
        assignment_list = []
        for key, val in kwargs.items():
            if type(val) == str:
                assignment_list.append(f"{key}='{val}'")
            else:
                assignment_list.append(f"{key}={val}")

        assignment_state = ', '.join(assignment_list)
        primary_key_column = self.get_columns(table_name)[0]

        query = f"UPDATE {table_name} SET {assignment_state} WHERE {primary_key_column}={id}"

        self.execute(query)

    
    def delete(self, table_name: str, **kwargs):
        query = f"DELETE FROM {table_name}"

        condition_list = []
        for key, value in kwargs.items():
            if type(value) == int or type(value) == float:
                condition_list.append(f" {key}={value}")
            elif type(value) == str:
                condition_list.append(f" {key}='{value}'")

        if len(condition_list) > 0:
            query += " WHERE" + ' AND'.join(condition_list)

        self.execute(query)    


    def get_by_primary_key(self, table_name: str, primary_key: int):
        return self.select(table_name).to_dict()[primary_key]


    def is_exists(self, table_name: str, primary_key: int) -> bool:
        primary_key_column = self.get_columns(table_name)[0]
        query = f"SELECT EXISTS(SELECT * FROM {table_name} WHERE {primary_key_column}={primary_key});"
        result_set = self.execute(query)

        return bool(result_set.result_set[0][0])

    
    def is_chat_exists(self, id: int) -> bool:
        return self.is_exists('Chat', id)

    
    def is_channel_exists(self, id: int) -> bool:
        return self.is_exists('Channel', id)

    
    def is_alarm_exists(self, id: int) -> bool:
        return self.is_exists('Alarm', id)

    
    def is_channel_alarm_exists(self, id: int) -> bool:
        return self.is_exists('ChannelAlarm', id)


    def get_item(self, id: int) -> Item:
        return Item(self, id)

    
    def get_registered_items(self) -> list:
        alarms = self.get_activated_alarms()
        channel_alarms = self.get_activated_channel_alarms()

        item_id_list = []
        for alarm in alarms:
            if alarm.get_item().id not in item_id_list:
                item_id_list.append(alarm.get_item().id)
        
        for alarm in channel_alarms:
            if alarm.get_item().id not in item_id_list:
                item_id_list.append(alarm.get_item().id)

        return [Item(self, id) for id in item_id_list]


    def get_exchange(self, id: int) -> Exchange:
        return Exchange(self, id)

    
    def get_every_exchange(self) -> list:
        exchange_dict = self.select('Exchange').to_dict()
        
        return [Exchange(self, id) for id in exchange_dict.keys()]

    
    def get_chat(self, id: int) -> Chat:
        return Chat(self, id)

    
    def get_every_chat(self) -> list:
        chat_dict = self.select('Chat').to_dict()

        return [Chat(self, id) for id in chat_dict.keys()]
    

    def get_channel(self, id: int) -> Channel:
        return Channel(self, id)
    

    def get_alarm(self, id: int) -> Alarm:
        return Alarm(self, id)

    
    def get_activated_alarms(self) -> list:
        alarm_dict = self.select('Alarm', IsEnabled=True).to_dict()

        return [Alarm(self, id) for id in alarm_dict.keys()]
    

    def get_channel_alarm(self, id: int) -> ChannelAlarm:
        return ChannelAlarm(self, id)

    
    def get_activated_channel_alarms(self) -> list:
        alarm_dict = self.select('ChannelAlarm', IsEnabled=True).to_dict()

        return [ChannelAlarm(self, id) for id in alarm_dict.keys()]

    
    def add_chat(self, id: int, alarm_option=True, status=0, buffer="") -> int:
        return self.insert('Chat', ChatID=id, AlarmOption=alarm_option, ChatStatus=status, ChatBuffer=buffer)

    
    def add_channel(self, id: int, name: str, chat_id: int, alarm_option=True) -> int:
        return self.insert('Channel', ChannelID=id, ChannelName=name, ChatID=chat_id, AlarmOption=alarm_option)


    def add_alarm(self, chat_id: int, item_id: int, order_quantity: int, enabled=True) -> int:
        return self.insert('Alarm', ChatID=chat_id, ItemID=item_id, OrderQuantity=order_quantity, IsEnabled=enabled)


    def add_channel_alarm(self, channel_id: int, item_id: int, order_quantity: int, enabled=True) -> int:
        return self.insert('ChannelAlarm', ChannelID=channel_id, ItemID=item_id, OrderQuantity=order_quantity, IsEnabled=enabled)

    
    def remove_chat(self, id: int):
        self.delete('Chat', ChatID=id)
    

    def remove_channel(self, id: int):
        self.delete('Channel', ChannelID=id)

    
    def remove_alarm(self, id: int):
        self.delete('Alarm', AlarmID=id)

    
    def remove_channel_alarm(self, id: int):
        self.delete('ChannelAlarm', ChannelAlarmID=id)
