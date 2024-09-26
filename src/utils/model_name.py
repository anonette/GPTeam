from enum import Enum


class ChatModelName(Enum):
    TURBO = "gpt-3.5-turbo"
    GPT4 = "gpt-4o-mini"
    CLAUDE = "claude-3-opus-20240229"
    CLAUDE_INSTANT = "claude-3-haiku-20240307"
    WINDOW = "window"
