from datetime import datetime, timedelta
from typing import Union, List
import requests
import json
import db


database = db.Database("database.db")


class Tick:
    def __init__(self, item_code: str, trade_time: str, trade_type: bool, price: int, volume: float):
        self.item = database.get_item(ExchangeID=1, ItemCode=item_code)[0]
        self.strptime = datetime.strptime(trade_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=9)
        self.trade_time = self.strptime.strftime('%Y-%m-%d %H:%M:%S')
        self.trade_type = trade_type    # 매도: 0, 매수: 1
        self.price = price
        self.volume = volume

    
    def write_tick_msg(self):
        msg = f"업비트 {self.item.get_code()}({self.item.get_name()}) 체결 발생!\n\n일시: {self.trade_time}\n체결량: {self.volume:,.2f} {self.item.get_unit()}@{self.price:,} {self.item.get_currency_unit()}\n총 거래량: {self.volume * self.price:,.2f} {self.item.get_currency_unit()}"

        return msg


class OrderbookUnit:
    def __init__(self, item_code: str, order_type: bool, price: int, volume: float):
        self.item = database.get_item(ExchangeID=1, ItemCode=item_code)[0]
        self.request_time = datetime.today() + timedelta(hours=9)
        self.strftime = self.request_time.strftime('%Y-%m-%d %H:%M:%S')
        self.order_type = order_type    # 매도: 0, 매수: 1
        self.price = price
        self.volume = volume


    def write_whale_msg(self):
        msg = f"업비트 {self.item.get_code()}({self.item.get_name()}) 고래 발견!\n\n일시: {self.strftime}\n{'매수' if self.order_type else '매도'}벽 {self.volume:.2f} {self.item.get_unit()}@{self.price:,} {self.item.get_currency_unit()}\n{self.volume * self.price:,.2f} {self.item.get_currency_unit()}"

        return msg


class Upbit:
    def get_every_items(self, currency_unit="KRW"):
        url = "https://api.upbit.com/v1/market/all"
        headers = {"accept": "application/json"}

        response = requests.get(url, headers=headers)
        return [item for item in response.json() if item["market"].split('-')[0] == currency_unit]  # 지정한 단위 종목만 불러옴


    def get_ticks(self, item_code: str, interval: int, count=10) -> List[Tick]:
        url = f"https://api.upbit.com/v1/trades/ticks?market={item_code}&count={count}"
        headers = {"accept": "application/json"}

        tick_list = [
            Tick(
                item_code = tick['market'],
                trade_time = f"{tick['trade_date_utc']} {tick['trade_time_utc']}",
                trade_type = False if tick['ask_bid'] == "ASK" else  True,   # 매도: 0, 매수: 1
                price = tick['trade_price'],
                volume = tick['trade_volume']
            ) for tick in requests.get(url, headers=headers).json()
            # 이미 조회했던 체결 계약은 제외
            # 마지막으로 조회했던 시점 이후부터의 체결 계약만 리스트에 추가
            if datetime.strptime(f"{tick['trade_date_utc']} {tick['trade_time_utc']}", '%Y-%m-%d %H:%M:%S') > datetime.now().replace(microsecond=0) + timedelta(seconds=-interval)
        ]

        return tick_list

    
    def get_orderbook(self, item_code: str) -> List[OrderbookUnit]:
        url = f"https://api.upbit.com/v1/orderbook?markets={item_code}"
        headers = {"accept": "application/json"}

        data = requests.get(url, headers=headers).json()[0]['orderbook_units']

        orderbook = [
            OrderbookUnit(
                item_code = item_code,
                order_type = 0 if order_type == 'ask' else 1,   # 매도: 0, 매수: 1
                price = unit[f'{order_type}_price'],
                volume = unit[f'{order_type}_size']
            ) for unit in data for order_type in ['ask', 'bid']
        ]

        return orderbook

    
    def find_whale(self, item_code: str, quantity: int):
        whale_list = [
            unit for unit in self.get_orderbook(item_code) if (unit.price * unit.volume) >= quantity
        ]

        return whale_list