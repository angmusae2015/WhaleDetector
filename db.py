from databasetypes import *
from typing import Union, List
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

        self.cursor.execute("PRAGMA foreign_keys = ON;")

    
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
            elif type(value) == bool:
                condition.append(f" {key}={int(value)}")
        
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

    def is_channel(self, chat_id: int) -> bool:
        if self.is_chat_exists(chat_id):
            return False
        
        elif self.is_channel_exists(chat_id):
            return True


    def get_item(self, id=None, **kwargs) -> Union[Item, List[Item]]:
        if id != None:
            return Item(self, id)

        else:
            item_dict = self.select('Item', **kwargs).to_dict()
            return [Item(self, item_id) for item_id in item_dict.keys()]


    def get_exchange(self, id=None, **kwargs) -> Union[Exchange, List[Exchange]]:
        if id != None:
            return Exchange(self, id)

        else:
            exchange_dict = self.select('Exchange', **kwargs).to_dict()
            return [Exchange(self, exchange_id) for exchange_id in exchange_dict.keys()]

    
    def get_chat(self, id=None, **kwargs) -> Union[Chat, List[Chat]]:
        if id != None:
            return Chat(self, id)

        else:
            chat_dict = self.select('Chat').to_dict()
            return [Chat(self, id) for id in chat_dict.keys()]
    

    def get_channel(self, id=None, **kwargs) -> Union[Channel, List[Channel]]:
        if id != None:
            return Channel(self, id)

        else:
            channel_dict = self.select('Channel', **kwargs).to_dict()
            return [Channel(self, channel_id) for channel_id in channel_dict.keys()]
    

    def get_alarm(self, id=None, **kwargs) -> Union[Alarm, List[Alarm]]:
        if id != None:
            return Alarm(self, id)
        else:
            alarm_dict = self.select('Alarm', **kwargs).to_dict()
            
            return [Alarm(self, alarm_id) for alarm_id in alarm_dict.keys()]

    
    def add_chat(self, id: int, alarm_option=True, status=0, buffer="") -> int:
        return self.insert('Chat', ChatID=id, AlarmOption=alarm_option, ChatStatus=status, ChatBuffer=buffer)

    
    def add_channel(self, id: int, name: str, admin_chat_id: int, alarm_option=True) -> int:
        return self.insert('Channel', ChannelID=id, ChannelName=name, AdminChatID=admin_chat_id, AlarmOption=alarm_option)


    def add_alarm(self, alarm_type: str, chat_id: int, item_id: int, quantity: int, is_enabled=True) -> int:
        return self.insert('Alarm', AlarmType=alarm_type, ChatID=chat_id, ItemID=item_id, Quantity=quantity, IsEnabled=is_enabled)

    
    def remove_chat(self, id: int):
        self.delete('Chat', ChatID=id)
    

    def remove_channel(self, id: int):
        self.delete('Channel', ChannelID=id)

    
    def remove_alarm(self, id: int):
        self.delete('Alarm', AlarmID=id)
