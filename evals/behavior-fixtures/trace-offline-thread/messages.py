from dataclasses import dataclass


@dataclass
class Message:
    text: str
    deleted: bool = False
    pending_delete: bool = False


class Conversation:
    def __init__(self) -> None:
        self.messages: dict[int, Message] = {}
        self.threads: dict[int, list[str]] = {}

    def add_message(self, message_id: int, text: str) -> None:
        self.messages[message_id] = Message(text=text)

    def delete_message(self, message_id: int, *, offline: bool = False) -> None:
        message = self.messages[message_id]
        if offline:
            message.pending_delete = True
        else:
            message.deleted = True

    def can_start_thread(self, message_id: int) -> bool:
        return not self.messages[message_id].deleted

    def start_thread(self, message_id: int, text: str) -> None:
        if not self.can_start_thread(message_id):
            raise ValueError("cannot start a thread on a deleted message")
        self.threads.setdefault(message_id, []).append(text)
