class ExchangeNotFoundError(Exception):
    def __init__(self):
        super().__init__('Could not find Exchange with given ID in database.')


class ItemNotFoundError(Exception):
    def __init__(self):
        super().__init__('Could not find Item with given ID in database.')


class ChatNotFoundError(Exception):
    def __init__(self):
        super().__init__('Could not find Chat with given ID in database.')


class ChannelNotFoundError(Exception):
    def __init__(self):
        super().__init__('Could not find Channel with given ID in database.')


class AlarmNotFoundError(Exception):
    def __init__(self):
        super().__init__('Could not find Alarm with given ID in database.')


class ChannelAlarmNotFoundError(Exception):
    def __init__(self):
        super().__init__('Could not find ChannelAlarm with given ID in database.')


class Exchange:
    def __init__(self, db, id: int):
        self.db = db
        self.id = id
        self.table_name = 'Exchange'

        if not self.is_exists():
            raise ExchangeNotFoundError
    

    def is_exists(self) -> bool:
        return self.db.is_exists(self.table_name, self.id)

    
    def get_name(self) -> str:
        return self.db.get_by_primary_key(self.table_name, self.id)['ExchangeName']

    
    def get_items(self) -> list:
        item_dict = self.db.select('Item', ExchangeID=self.id).to_dict()
        item_list = [Item(self.db, item['ItemID']) for item in item_dict.values()]

        return item_list


class Item:
    def __init__(self, db, id: int):
        self.db = db
        self.id = id
        self.table_name = 'Item'

        if not self.is_exists():
            raise ItemNotFoundError


    def is_exists(self) -> bool:
        return self.db.is_exists(self.table_name, self.id)

    
    def get_code(self) -> str:
        return self.db.get_by_primary_key(self.table_name, self.id)['ItemCode']

    
    def get_name(self) -> str:
        return self.db.get_by_primary_key(self.table_name, self.id)['ItemName']

    
    def get_exchange(self) -> Exchange:
        exchange_id = self.db.get_by_primary_key(self.table_name, self.id)['ExchangeID']
        
        return Exchange(self.db, exchange_id)

    
    def get_alarms(self) -> list:
        alarm_dict = self.db.select('Alarm', ItemID=self.id).to_dict()
        
        return [Alarm(self.db, alarm_id) for alarm_id in alarm_dict.keys()]

    
    def get_channel_alarms(self) -> list:
        alarm_dict = self.db.select('ChannelAlarm', ItemID=self.id).to_dict()
        
        return [ChannelAlarm(self.db, alarm_id) for alarm_id in alarm_dict.keys()]


class Chat:
    def __init__(self, db, id: int):
        self.db = db
        self.id = id
        self.table_name = 'Chat'

        if not self.is_exists():
            raise ChatNotFoundError
    

    def is_exists(self) -> bool:
        return self.db.is_exists(self.table_name, self.id)

    
    def get_alarm_option(self) -> bool:
        return self.db.get_by_primary_key(self.table_name, self.id)['AlarmOption']


    def get_status(self) -> int:
        return self.db.get_by_primary_key(self.table_name, self.id)['ChatStatus']


    def get_buffer(self) -> str:
        return self.db.get_by_primary_key(self.table_name, self.id)['ChatBuffer']
        
    
    def get_alarms(self) -> list:
        alarm_dict = self.db.select('Alarm', ChatID=self.id).to_dict()
        alarm_list = [Alarm(self.db, alarm['AlarmID']) for alarm in alarm_dict.values()]

        return alarm_list

    
    def get_channels(self) -> list:
        channel_dict = self.db.select('Channel', ChatID=self.id).to_dict()
        channel_list = [Channel(self.db, channel['ChannelID']) for channel in channel_dict.values()]

        return channel_list

    
    def set_alarm_option(self, option: bool):
        self.db.update(self.table_name, self.id, AlarmOption=option)

    
    def set_status(self, status: int):
        self.db.update(self.table_name, self.id, ChatStatus=status)

    
    def set_buffer(self, buffer: str):
        self.db.update(self.table_name, self.id, ChatBuffer=buffer)

    
    def add_alarm(self, item_id: int, order_quantity: int, enabled=True):
        alarm_id = self.db.add_alarm(self.id, item_id, order_quantity, enabled)

        return Alarm(self.db, alarm_id)

    
    def add_channel(self, id: int, name: str, alarm_option=True):
        channel_id = self.db.add_channel(id, name, self.id, alarm_option)

        return Channel(self.db, channel_id)

    
    def add_buffer_parameter(self, **kwargs):
        parameter_list = []
        for key, val in kwargs.items():
            if type(val) == str:
                parameter_list.append(f"{key}=\"{val}")
            else:
                parameter_list.append(f"{key}={val}")

        if self.get_buffer() == '':
            statement = '?'.join(parameter_list)
        else:
            statement = f"{self.get_buffer()}?{'?'.join(parameter_list)}"
        self.set_buffer(statement)

    
    def remove_alarm(self, id: int):
        self.db.remove_alarm(id)

    
    def remove_channel(self, id: int):
        self.db.remove_channel(id)


    def parse_buffer(self):
        if self.get_buffer() == "":
            return {}
        
        parameter_list = self.get_buffer().split('?')
        parameter_dict = {}
        for parameter in parameter_list:
            key, val = parameter.split('=')
            if val.startswith('"'):
                parameter_dict[key] = val[1:]
            else:
                parameter_dict[key] = int(val)

        return parameter_dict


class Channel:
    def __init__(self, db, id: int):
        self.db = db
        self.id = id
        self.table_name = 'Channel'

        if not self.is_exists():
            raise ChannelNotFoundError


    def is_exists(self) -> bool:
        return self.db.is_exists(self.table_name, self.id)
    

    def get_name(self) -> str:
        return self.db.get_by_primary_key(self.table_name, self.id)['ChannelName']

    
    def get_chat(self) -> Chat:
        chat_id = self.db.get_by_primary_key(self.table_name, self.id)['ChatID']

        return Chat(self.db, chat_id)

    
    def get_alarm_option(self) -> bool:
        return self.db.get_by_primary_key(self.table_name, self.id)['AlarmOption']

    
    def get_alarms(self) -> list:
        alarm_dict = self.db.select('ChannelAlarm', ChannelID=self.id).to_dict()
        alarm_list = [ChannelAlarm(self.db, alarm['ChannelAlarmID']) for alarm in alarm_dict.values()]

        return alarm_list

    
    def set_name(self, name: str):
        self.db.update(self.table_name, self.id, ChannelName=name)
    

    def set_alarm_option(self, option: bool):
        self.db.update(self.table_name, self.id, AlarmOption=option)

    
    def add_alarm(self, item_id: int, order_quantity: int, enabled=True):
        channel_alarm_id = self.db.add_channel_alarm(self.id, item_id, order_quantity, enabled)

        return ChannelAlarm(self.db, channel_alarm_id)


    def remove_alarm(self, id):
        self.db.remove_channel_alarm(id)


class Alarm:
    def __init__(self, db, id: int):
        self.db = db
        self.id = id
        self.table_name = 'Alarm'

        if not self.is_exists():
            raise AlarmNotFoundError


    def is_exists(self) -> bool:
        return self.db.is_exists(self.table_name, self.id)

    
    def get_chat(self) -> Chat:
        chat_id = self.db.get_by_primary_key(self.table_name, self.id)['ChatID']

        return Chat(self.db, chat_id)

    
    def get_item(self) -> Item:
        item_id = self.db.get_by_primary_key(self.table_name, self.id)['ItemID']
        
        return Item(self.db, item_id)


    def get_order_quantity(self) -> int:
        return self.db.get_by_primary_key(self.table_name, self.id)['OrderQuantity']

    
    def is_enabled(self) -> bool:
        return self.db.get_by_primary_key(self.table_name, self.id)['IsEnabled']

    
    def set_order_quantity(self, order_quantity: int):
        self.db.update(self.table_name, self.id, OrderQuantity=order_quantity)

    
    def set_enabled(self, enabled: bool):
        self.db.update(self.table_name, self.id, IsEnabled=enabled)


class ChannelAlarm:
    def __init__(self, db, id: int):
        self.db = db
        self.id = id
        self.table_name = 'ChannelAlarm'

        if not self.is_exists():
            raise ChannelAlarmNotFoundError


    def is_exists(self) -> bool:
        return self.db.is_exists(self.table_name, self.id)

    
    def get_channel(self) -> Channel:
        channel_id = self.db.get_by_primary_key(self.table_name, self.id)['ChannelID']

        return Channel(self.db, channel_id)

    
    def get_item(self) -> Item:
        item_id = self.db.get_by_primary_key(self.table_name, self.id)['ItemID']
        
        return Item(self.db, item_id)


    def get_order_quantity(self) -> int:
        return self.db.get_by_primary_key(self.table_name, self.id)['OrderQuantity']

    
    def is_enabled(self) -> bool:
        return self.db.get_by_primary_key(self.table_name, self.id)['IsEnabled']
    

    def set_order_quantity(self, order_quantity: int):
        self.db.update(self.table_name, self.id, OrderQuantity=order_quantity)

    
    def set_enabled(self, enabled: bool):
        self.db.update(self.table_name, self.id, IsEnabled=enabled)