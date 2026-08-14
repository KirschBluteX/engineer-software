import unittest

from styles import ERROR_TEXT_STYLE, contact_error_style


class ErrorStyleTests(unittest.TestCase):
    def test_contact_errors_use_shared_style(self) -> None:
        self.assertIs(contact_error_style(), ERROR_TEXT_STYLE)


if __name__ == "__main__":
    unittest.main()
