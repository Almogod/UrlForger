import json
import os
import time
import tempfile
from src.config import config

class TaskStore:
    """
    A simple file-based task store for tracking progress and results
    across different workers. Optimized for Windows with atomic writes.
    """
    def __init__(self, file_path=config.TASK_STORE_PATH):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            self._write({})

    def _read(self):
        # Retry loop for Windows file locking / mid-write reads
        for _ in range(5):
            try:
                if not os.path.exists(self.file_path):
                    return {}
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if not content:
                        time.sleep(0.1)
                        continue
                    return json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError, PermissionError):
                time.sleep(0.1)
        return {}

    def _write(self, data):
        # Atomic write pattern for Windows
        dir_name = os.path.dirname(self.file_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            # On Windows, os.replace can fail if target is open; but it's better than direct write
            try:
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                os.rename(temp_path, self.file_path)
            except PermissionError:
                # Fallback if rename fails
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        finally:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

    def set_status(self, task_id, status, error=None):
        data = self._read()
        if task_id not in data:
            data[task_id] = {}
        data[task_id]["status_msg"] = status
        if error:
            data[task_id]["status"] = "error"
            data[task_id]["error"] = error
        elif status == "Completed" or status == "Analysis finished":
            data[task_id]["status"] = "completed"
        else:
            data[task_id]["status"] = "running"
        self._write(data)

    def get_status(self, task_id):
        data = self._read()
        if not data or task_id not in data:
            # If we just started, don't return "unknown" immediately if the file is being written
            return {"status": "running", "status_msg": "Initializing..."}
        return data.get(task_id, {"status": "unknown", "status_msg": "Unknown task"})

    def save_results(self, task_id, results):
        data = self._read()
        if task_id not in data:
            data[task_id] = {}
        data[task_id]["results"] = results
        data[task_id]["status"] = "completed"
        data[task_id]["status_msg"] = "Completed"
        self._write(data)

    def get_results(self, task_id):
        data = self._read()
        return data.get(task_id, {}).get("results", None)

task_store = TaskStore()
