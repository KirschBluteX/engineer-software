from chat import accepts_chat_recipient
from contacts import accepts_contact
from login import accepts_login


VALIDATORS = {
    "chat": accepts_chat_recipient,
    "contact": accepts_contact,
    "login": accepts_login,
}
