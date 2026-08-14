import re


LOGIN_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def accepts_login(value: str) -> bool:
    return bool(LOGIN_EMAIL.fullmatch(value))
