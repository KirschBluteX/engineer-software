import unittest

from messages import Conversation


class ConversationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conversation = Conversation()
        self.conversation.add_message(1, "hello")

    def test_ordinary_message_accepts_thread(self) -> None:
        self.conversation.start_thread(1, "reply")
        self.assertEqual(self.conversation.threads[1], ["reply"])

    def test_online_deleted_message_rejects_thread(self) -> None:
        self.conversation.delete_message(1)
        with self.assertRaises(ValueError):
            self.conversation.start_thread(1, "reply")


if __name__ == "__main__":
    unittest.main()
