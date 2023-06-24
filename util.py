from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# 문자열로 된 숫자를 입력받아 한국식 표기로 변환함
# 예) '123456789.01' -> '1억 2345만 6789.01'
def convert_to_korean_num(value: str, omit_decimal=False) -> str:
    text = ""
    integer_part, decimal_part = None, None

    # 문자열에서 정수와 소수 부분 추출
    if '.' not in value:
        integer_part = value
        if integer_part == '0':
            return '0'

    elif value.endswith('.'):
        integer_part = value[:-1]

    else:
        integer_part, decimal_part = value.split('.')

    # 한국식 표기로 변환
    integer_part = int(integer_part)
    if integer_part // (10 ** 8) > 0:
        text += f"{integer_part // (10 ** 8)}억 "
        integer_part = integer_part % (10 ** 8)
        
    if integer_part // (10 ** 4) > 0:
        text += f"{integer_part // (10 ** 4)}만 "
        integer_part = integer_part % (10 ** 4)

    if integer_part // 1 > 0:
        text += f"{integer_part}"

    if omit_decimal:    # 소수 부분 생략 시
        if decimal_part != None:
            text += '0' if (integer_part // 1 == 0) and int(decimal_part) != 0 else ''   # 천의 자리 이하 정수 부분이 0이고 소수 부분이 없으면 '0' 생략
            text += f".{decimal_part}" if int(decimal_part) != 0 else ''    # 소수 부분이 0이거나 없을 경우 소수점과 소수부분 생략

    else:   # 소수 부분 모두 출력 시
        text += f"{'0' if (integer_part // 1 == 0) and ('.' in value) else ''}"  # 천의 자리 이하 정수 부분이 0일 때 소수점 입력 시 '0' 표시
        text += f"{'.' if '.' in value else ''}{f'{decimal_part}' if decimal_part != None else ''}"   # 소수점과 소수 부분 숫자 입력 시 표시

    if text.endswith(' '):
        text = text[:-1]

    return text


# 취소 버튼
def CancelButton() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="취소", callback_data="cancel")


# 숫자를 입력할 수 있는 키보드 마크업
class QuantityCalculator:
    def __init__(self, next_trigger: str, value: str, unit: str, display_type=1):
        self.next_trigger = next_trigger
        self.value = value
        self.unit = unit
        self.display_type = int(display_type)    # 입력값 표시 버튼에서 숫자를 표시할 방식 선택 (0: 숫자만 표시, 1: 한국식 표기로 표시)
        self.markup = InlineKeyboardMarkup()
            
        self.markup.add(
            self.DisplayButton(),
            row_width=3
        )

        # 한 줄에 3개의 숫자씩 숫자 버튼을 마크업에 추가
        for cnt in range(1, 8, 3):
            self.markup.add(
                self.KeypadButton(str(cnt)),
                self.KeypadButton(str(cnt + 1)),
                self.KeypadButton(str(cnt + 2)),
                row_width=3
            )
        
        self.markup.add(
            self.PointButton(),
            self.KeypadButton('0'),
            self.BackspaceButton(),
            row_width=3
        )

        self.markup.add(
            self.SubmitButton(),
            row_width=3
        )

        self.markup.add(
            CancelButton(),
            row_width=3
        )
    

    # 숫자 버튼
    def KeypadButton(self, text: str) -> InlineKeyboardButton:
        value_data, callback_data = "", ""
        if '.' in self.value and len(self.value.split('.')[1]) == 3:    # 소수점 아래 세 자리 수까지 입력했다면 더 이상 입력받지 않음
            callback_data = "none"

        elif self.value == '0':     # 현재 값이 0이라면 입력한 값만 입력
            value_data = f"{text}"

        else:   # 현재 값 오른쪽에 입력한 값 추가
            value_data = f"{self.value}{text}"
        
        if callback_data != "none":
            callback_data = f"update_keyboard:{value_data}:{self.unit}:{self.next_trigger}:{self.display_type}"
        return InlineKeyboardButton(text=text, callback_data=callback_data)

    
    # 소수점 버튼
    def PointButton(self) -> InlineKeyboardButton:
        value_data, callback_data = "", ""
        if '.' in self.value:     # 이미 소수점을 입력했다면 소수점을 입력받지 않음
            callback_data = "none"
        
        else:   # 소수점 추가
            value_data = f"{self.value}."

        if callback_data != "none":
            callback_data = f"update_keyboard:{value_data}:{self.unit}:{self.next_trigger}:{self.display_type}"
        return InlineKeyboardButton(text='.', callback_data=callback_data)


    # 백스페이스 버튼
    def BackspaceButton(self) -> InlineKeyboardButton:
        value_data, callback_data = "", ""
        if self.value == '0':   # 현재 값이 0일 경우 아무 변화도 주지 않음
            callback_data = "none"

        elif len(self.value) == 1:  # 현재 값이 한자리 수일 경우 현재 값을 0으로 표시
            value_data = "0"

        else:   # 오른쪽부터 한 글자씩 삭제
            value_data = f"{self.value[:-1]}"

        if callback_data != "none":
            callback_data = f"update_keyboard:{value_data}:{self.unit}:{self.next_trigger}:{self.display_type}"
        return InlineKeyboardButton(text='←', callback_data=callback_data)


    # 현재 입력한 값을 표시하는 버튼
    def DisplayButton(self) -> InlineKeyboardButton:
        value_data, callback_data = "", ""
        if self.display_type == 0:
            if '.' in self.value:
                integer_part, decimal_part = self.value.split('.')
                value_data = f"{int(integer_part):,}.{decimal_part}"
            
            else:
                value_data = f"{int(self.value):,}"
        
        elif self.display_type == 1:
            value_data = f"{convert_to_korean_num(self.value)}"

        text = f"{value_data} {self.unit}"
        callback_data = f"update_keyboard:{self.value}:{self.unit}:{self.next_trigger}:{int(not self.display_type)}"
        return InlineKeyboardButton(text=text, callback_data=callback_data)


    # 현재 입력한 값을 확정하여 다음 단계로 값을 전송하는 버튼
    def SubmitButton(self) -> InlineKeyboardButton:
        callback_data = ""

        if float(self.value) == 0:
            callback_data = "none"
        else:
            callback_data = f"{self.next_trigger}:{self.value}:{self.unit}"

        return InlineKeyboardButton(text="입력", callback_data=callback_data)