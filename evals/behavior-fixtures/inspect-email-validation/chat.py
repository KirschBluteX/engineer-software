import re


CHAT_EMAIL = re.compile(r"^[\w.'#%+-]+@[A-Za-z\d.-]+\.[A-Za-z]{2,}$")


def accepts_chat_recipient(value: str) -> bool:
    return bool(CHAT_EMAIL.fullmatch(value))
