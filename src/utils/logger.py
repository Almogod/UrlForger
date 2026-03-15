import logging
import json
import sys
from datetime import datetime
from src.config import config

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logger():
    logger = logging.getLogger("seo_enterprise")
    logger.setLevel(config.LOG_LEVEL)
    
    handler = logging.StreamHandler(sys.stdout)
    if config.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    
    logger.addHandler(handler)
    
    # Audit Logger
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_handler = logging.FileHandler(config.AUDIT_LOG_PATH)
    audit_handler.setFormatter(JSONFormatter())
    audit_logger.addHandler(audit_handler)
    
    return logger

logger = setup_logger()
audit_logger = logging.getLogger("audit")
