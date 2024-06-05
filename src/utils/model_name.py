from enum import Enum


class ChatModelName(Enum):
    TURBO = "gpt-3.5-turbo"
    GPT4 = "gpt-4o"
    CLAUDE = "claude-3-haiku-20240307"
    CLAUDE_INSTANT = "claude-instant-v1"
    WINDOW = "window"
