from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def convert_to_korean_num(value: int) -> str:
        text = ""
        if value == 0:
            text = "0"
        else:
            if abs(value) >= 10 ** 8:
                text += f"{str(value)[:-8]}억"

                if abs(value) % (10 ** 8) != 0:
                    text += " " + convert_to_korean_num(abs(value) % (10 ** 8))
            
            else:
                text += f"{str(value)[:-4]}만"

        return text


def CancelButton() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="취소", callback_data="cancel")


class OrderQuantityCalculator:
    def __init__(self, next_trigger: str, value: int):
        self.value = value
        self.next_trigger = next_trigger
        self.markup = InlineKeyboardMarkup()

        for exp in range(4, 10, 3):
            self.markup.add(
                self.KeypadButton(10 ** (exp)),
                self.KeypadButton(10 ** (exp + 1)),
                self.KeypadButton(10 ** (exp + 2)),
                row_width=3
            )
            
        self.markup.add(
            self.DisplayButton(),
            row_width=3
        )

        for exp in range(4, 10, 3):
            self.markup.add(
                self.KeypadButton(-(10 ** (exp))),
                self.KeypadButton(-(10 ** (exp + 1))),
                self.KeypadButton(-(10 ** (exp + 2))),
                row_width=3
            )

        self.markup.add(
            CancelButton(),
            row_width=3
        )

        if self.value != 0:
            self.markup.add(
                self.SubmitButton(),
                row_width=3
            )
    

    def KeypadButton(self, increment: int) -> InlineKeyboardButton:
        text = f"{convert_to_korean_num(increment)}"
        
        callback_data = f"update_keyboard:{self.value + increment if self.value + increment > 0 else 0}:{self.next_trigger}"
        
        return InlineKeyboardButton(text=text, callback_data=callback_data)


    def DisplayButton(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=f"{convert_to_korean_num(self.value)} 원", callback_data="none")


    def SubmitButton(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(text="입력", callback_data=f"{self.next_trigger}:{self.value}")