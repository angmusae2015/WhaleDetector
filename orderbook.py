from datetime import datetime
from db import db_handler
import requests

class Orderbook:
    def __init__(self, exchange_code, market_code):  # 거래소 이름, 종목 이름, 호가 데이터
        self.exchange_code = exchange_code  # 거래소 이름
        self.market_code = market_code  # 종목 이름
        self.request_time = datetime.today()    # 요청 일시
        self.orderbook_data = self.get_orderbook_data(exchange_code, market_code)   # 호가 데이터
        self.ask, self.bid = self.parse_orderbook_data(exchange_code, self.orderbook_data)   # 매도/매수 호가
        

    # 호가 조회 시간 문자열로 변환
    def strftime(self):
        return self.request_time.strftime('%Y:%m:%d %H:%M:%S')


    # 호가 데이터 불러오기
    @staticmethod
    def get_orderbook_data(exchange_code, market_code):
        if exchange_code == "upbit":
            url = "https://api.upbit.com/v1/orderbook?markets=" + market_code
            headers = {"accept": "application/json"}

            orderbook_data = requests.get(url, headers=headers).json()[0]["orderbook_units"]

            return orderbook_data


    # 호가 데이터 파싱하여 [(가격, 잔량)] 형식의 리스트로 변환
    @staticmethod
    def parse_orderbook_data(exchange_code, orderbook_data):    # 거래소 이름, 호가 데이터
        if exchange_code == "upbit": # 업비트 호가 데이터 파싱
            ask = [(order["ask_price"], order["ask_size"]) for order in orderbook_data]
            bid = [(order["bid_price"], order["bid_size"]) for order in orderbook_data]
        
        return ask, bid


    # 고래 탐색
    def find_whale(self, threshold):    # 고래 기준치
        whales_in_ask = [order for order in self.ask if order[0] * order[1] >= threshold]    # 지정한 고래 기준치보다 클 경우 고래으로 구분
        whales_in_bid = [order for order in self.bid if order[0] * order[1] >= threshold]
    
        return whales_in_ask, whales_in_bid


    # 고래 안내 메시지 작성
    def whale_alarm(self, threshold):
        whales_in_ask, whales_in_bid = self.find_whale(threshold)   # 고래 탐색

        msg = []    # 메시지 목록
        for whale in whales_in_ask:
            msg.append("업비트 {0} 고래 발견!\n\n일시: {1}\n매도벽 {2[1]:.2f}@{2[0]:,}\nKRW {3:,.2f}".format(self.market_code, self.strftime(), whale, whale[0] * whale[1]))

        for whale in whales_in_bid:
            msg.append("업비트 {0} 고래 발견!\n\n일시: {1}\n매수벽 {2[1]:.2f}@{2[0]:,}\nKRW {3:,.2f}".format(self.market_code, self.strftime(), whale, whale[0] * whale[1]))
        
        return msg