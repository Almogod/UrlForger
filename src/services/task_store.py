import json
import os
from src.config import config

class TaskStore:
    """
    A simple file-based task store for tracking progress and results
    across different workers.
    """
    def __init__(self, file_path=config.TASK_STORE_PATH):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    def _read(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    def set_status(self, task_id, status, error=None):
        data = self._read()
        if task_id not in data:
            data[task_id] = {}
        data[task_id]["status_msg"] = status
        if error:
            data[task_id]["status"] = "error"
            data[task_id]["error"] = error
        elif status == "Completed":
            data[task_id]["status"] = "completed"
        else:
            data[task_id]["status"] = "running"
        self._write(data)

    def get_status(self, task_id):
        data = self._read()
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
