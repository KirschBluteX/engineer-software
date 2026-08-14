from dataclasses import dataclass


@dataclass
class Message:
    message_id: int
    deleted: bool = False
    pending_delete: bool = False
