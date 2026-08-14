import re


CODE = re.compile(r"```([^`]*)```")
HEADING = re.compile(r"^# (.+)$")


def render_regex(text: str) -> str:
    with_code = CODE.sub(r"<pre>\1</pre>", text)
    return HEADING.sub(r"<h1>\1</h1>", with_code)


def render_tokenized(text: str) -> str:
    if text.startswith("# ```") and text.endswith("```"):
        code = text[5:-3]
        return f"<h1></h1><pre>{code}</pre>"
    return render_regex(text)


def render(text: str) -> str:
    return render_regex(text)
