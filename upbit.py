from datetime import datetime
import requests
import db


database = db.Database("database.db")


class Tick:
    def __init__(self, item_code: str, trade_time: str, trade_type: bool, price: int, volume: float):
        self.item = database.get_item_by_code(1, item_code)
        self.trade_time = datetime.strptime(trade_time, '%Y-%m-%d %I:%M:%S')
        self.trade_type = trade_type    # 매도: 0, 매수: 1
        self.price = price
        self.volume = volume


class OrderbookUnit:
    def __init__(self, item_code: str, order_type: bool, price: int, volume: float):
        self.item = database.get_item_by_code(1, item_code)
        self.request_time = datetime.today()
        self.strftime = self.request_time.strftime('%Y-%m-%d %H:%M:%S')
        self.order_type = order_type    # 매도: 0, 매수: 1
        self.price = price
        self.volume = volume


    def write_whale_msg(self):
        msg = f"""업비트 {self.item.get_code()} 고래 발견!

일시: {self.strftime}
{'매수' if self.order_type else '매도'}벽 {self.volume:.2f}@{self.price:,}
KRW {self.volume * self.price:,.2f}
"""

        return msg


class Upbit:
    def get_ticks(self, item_code: str, count=10) -> list:
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
        ]

        return tick_list

    
    def get_orderbook(self, item_code: str) -> list:
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

    
    def find_whale(self, item_code: str, order_quantity: int):
        whale_list = [
            unit for unit in self.get_orderbook(item_code) if (unit.price * unit.volume) >= order_quantity
        ]

        return whale_list