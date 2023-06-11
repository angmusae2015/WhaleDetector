from datetime import datetime
import databasetypes
import db
import requests

class Orderbook:
    def __init__(self, item: databasetypes.Item):
        self.item = item
        self.request_time = datetime.today()    # 요청 일시
        self.orderbook_data = self.get_orderbook_data()   # 호가 데이터
        self.ask, self.bid = self.parse_orderbook_data()   # 매도/매수 호가
        

    # 호가 조회 시간 문자열로 변환
    def strftime(self):
        return self.request_time.strftime('%Y:%m:%d %H:%M:%S')


    # 호가 데이터 불러오기
    def get_orderbook_data(self):
        if self.item.get_exchange().id == 1:
            url = "https://api.upbit.com/v1/orderbook?markets=" + self.item.get_code()
            headers = {"accept": "application/json"}

            orderbook_data = requests.get(url, headers=headers).json()[0]["orderbook_units"]

            return orderbook_data


    # 호가 데이터 파싱하여 [(가격, 잔량)] 형식의 리스트로 변환
    def parse_orderbook_data(self):    # 거래소 이름, 호가 데이터
        if self.item.get_exchange().id == 1: # 업비트 호가 데이터 파싱
            ask = [(order["ask_price"], order["ask_size"]) for order in self.orderbook_data]
            bid = [(order["bid_price"], order["bid_size"]) for order in self.orderbook_data]
        
        return ask, bid


    # 고래 탐색
    def find_whale(self, order_quantity):    # 고래 기준치
        whales_in_ask = [order for order in self.ask if order[0] * order[1] >= order_quantity]    # 지정한 고래 기준치보다 클 경우 고래으로 구분
        whales_in_bid = [order for order in self.bid if order[0] * order[1] >= order_quantity]
    
        return whales_in_ask, whales_in_bid


    # 고래 안내 메시지 작성
    def whale_alarm(self, order_quantity):
        whales_in_ask, whales_in_bid = self.find_whale(order_quantity) 
        msg = []    # 메시지 목록
        for whale in whales_in_ask:
            msg.append("업비트 {0} 고래 발견!\n\n일시: {1}\n매도벽 {2[1]:.2f}@{2[0]:,}\nKRW {3:,.2f}".format(self.item.get_code(), self.strftime(), whale, whale[0] * whale[1]))

        for whale in whales_in_bid:
            msg.append("업비트 {0} 고래 발견!\n\n일시: {1}\n매수벽 {2[1]:.2f}@{2[0]:,}\nKRW {3:,.2f}".format(self.item.get_code(), self.strftime(), whale, whale[0] * whale[1]))
        
        return msg