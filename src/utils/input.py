import sys
import logging
from colorama import Fore

from ..utils.formatting import print_to_console
from .colors import LogColor

logger = logging.getLogger(__name__)

def get_user_input(question: str):
    # Check if we're in a terminal
    if not (hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()):
        logger.warning("Attempted to get user input in non-tty environment")
        return ""
        
    print_to_console("Question", LogColor.CLI_INPUT, question)
    i = input()
    return i
