def escape_markdown_dollars(text: str) -> str:
    return text.replace("$", "\\$")
