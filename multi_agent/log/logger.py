import logging
import json
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

REQUEST_ID_CTX = ContextVar("request_id", default="MCP_NOT_INFORMED")

class JsonFormatter(logging.Formatter):
    def __init__(self, component: str, max_msg_length: int = None):
        super().__init__()
        self.component = component
        self.max_msg_length = max_msg_length

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        if self.max_msg_length and len(message) > self.max_msg_length:
            message = message[: self.max_msg_length] + "..."

        log_entry = {
            "level": record.levelname.lower(),
            "component": record.name,
            "request-id":  REQUEST_ID_CTX.get(),
            "message": message,
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        return json.dumps(log_entry)
        
def setup_logger(LOG_LEVEL: str,
                 APP_NAME: str,
                 OTEL_STDOUT_LOG_GROUP: bool,
                 LOG_GROUP: str) -> None:

    root_logger  = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    handler = logging.StreamHandler()
    formatter = JsonFormatter(component=APP_NAME, max_msg_length=500)
    handler.setFormatter(formatter)

    root_logger .handlers.clear()
    root_logger .addHandler(handler)

    # File logging if OTEL_LOGS is enabled
    if OTEL_STDOUT_LOG_GROUP == True:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(LOG_GROUP), exist_ok=True) 
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        LOG_GROUP = os.path.join(BASE_DIR,LOG_GROUP)

        MAX_BYTES = 10 * 1024 # 1 MB
        BACKUP_COUNT = 1    
        file_handler = RotatingFileHandler(
            LOG_GROUP,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        root_logger.info(f"File logging enabled. Logs are being written to: {LOG_GROUP}")