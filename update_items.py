from upbit import Upbit
from db import Database


upbit = Upbit()
database = Database('database.db')

upbit_item_json = upbit.get_every_items("KRW")
for item in upbit_item_json:
    item_code = item['market']
    item_name = item['korean_name']
    item_currency_unit, item_unit = item['market'].split('-')

    if not database.is_exists('Item', ItemCode=item_code, ExchangeID=1):
        database.add_item(item_code, item_name, 1, item_unit, item_currency_unit)
        print(f"Added {item_code}")
