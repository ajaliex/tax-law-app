import json
import os
from datetime import datetime, timedelta

LOG_FILE = "data/learning_log.json"

class LearningManager:
    def __init__(self):
        self.log_file = LOG_FILE
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump({}, f)

    def _load_log(self):
        try:
            with open(self.log_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_log(self, log_data):
        with open(self.log_file, 'w') as f:
            json.dump(log_data, f)

    def add_learning_time(self, seconds):
        if seconds <= 0:
            return
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        log_data = self._load_log()
        
        if today_str not in log_data:
            log_data[today_str] = 0
            
        log_data[today_str] += seconds
        
        # Optional: Clean up old data (older than yesterday)
        # keeping it simple: just save
        self._save_log(log_data)

    def get_learning_time(self):
        """Returns a tuple (today_seconds, yesterday_seconds)"""
        log_data = self._load_log()
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        today_str = today.strftime('%Y-%m-%d')
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        return (
            log_data.get(today_str, 0),
            log_data.get(yesterday_str, 0)
        )

    def format_time(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{int(h)}時間{int(m)}分"
        return f"{int(m)}分{int(s)}秒"
