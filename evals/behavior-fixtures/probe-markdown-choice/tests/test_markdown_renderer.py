import unittest

from markdown_renderer import render


class MarkdownRendererTests(unittest.TestCase):
    def test_plain_heading(self) -> None:
        self.assertEqual(render("# Heading"), "<h1>Heading</h1>")

    def test_plain_code(self) -> None:
        self.assertEqual(render("```code```"), "<pre>code</pre>")


if __name__ == "__main__":
    unittest.main()
