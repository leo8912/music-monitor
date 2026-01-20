import logging
import collections
from datetime import datetime

# Log Buffer for API
class APILogHandler(logging.Handler):
    def __init__(self, capacity=100):
        super().__init__()
        self.capacity = capacity
        self.buffer = collections.deque(maxlen=capacity)
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append({
                "time": datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                "level": record.levelname,
                "message": msg,
                "source": record.name
            })
        except Exception:
            self.handleError(record)

api_log_handler = APILogHandler()
api_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
