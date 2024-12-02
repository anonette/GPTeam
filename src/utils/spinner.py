import itertools
import sys
import threading
import time
import logging

logger = logging.getLogger(__name__)

class Spinner:
    def __init__(self, message="Loading...", delay=0.1):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.delay = delay
        self.message = message
        self.running = False
        self.spinner_thread = None

    def spin(self):
        while self.running:
            try:
                # Only write to stdout if it's a terminal
                if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
                    sys.stdout.write(next(self.spinner) + " " + self.message + "\r")
                    sys.stdout.flush()
                    time.sleep(self.delay)
                    sys.stdout.write("\b" * (len(self.message) + 2))
                else:
                    # If not a terminal, just log the message once
                    logger.debug(f"Processing: {self.message}")
                    time.sleep(self.delay)
            except (AttributeError, IOError):
                # If stdout has issues, just sleep
                time.sleep(self.delay)

    def __enter__(self):
        self.running = True
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.start()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.running = False
        if self.spinner_thread:
            self.spinner_thread.join()
        try:
            # Only write to stdout if it's a terminal
            if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
                sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
                sys.stdout.flush()
        except (AttributeError, IOError):
            pass
