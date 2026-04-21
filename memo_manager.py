import json
import os

MEMO_FILE = "data/memos.json"

class MemoManager:
    def __init__(self):
        self.memo_file = MEMO_FILE
        self._ensure_memo_file()

    def _ensure_memo_file(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.memo_file):
            with open(self.memo_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False)

    def _load_all(self):
        try:
            with open(self.memo_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_all(self, data):
        with open(self.memo_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_memo(self, h1, h2, item_title):
        """特定の論点のメモを取得する"""
        data = self._load_all()
        # キーは "H1名|H2名|論点タイトル" とする
        key = f"{h1}|{h2}|{item_title}"
        return data.get(key, "")

    def save_memo(self, h1, h2, item_title, text):
        """特定の論点にメモを保存する"""
        data = self._load_all()
        key = f"{h1}|{h2}|{item_title}"
        data[key] = text
        self._save_all(data)
