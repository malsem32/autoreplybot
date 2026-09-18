import logging
import sys

from backend.core.config import settings

_SENSITIVE_KEYS = {"phone", "code", "password", "session", "session_string", "api_hash"}


class RedactSensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in _SENSITIVE_KEYS:
            if key in record.getMessage().lower():
                record.msg = "[redacted: message referenced sensitive field]"
                record.args = ()
                break
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}')
    )
    handler.addFilter(RedactSensitiveFilter())

    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers = [handler]
