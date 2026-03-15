import json
import os
import uuid
from typing import List, Dict
from src.utils.logger import logger, audit_logger
from src.services.task_store import task_store

class BatchManager:
    def __init__(self, sites_config_path: str = "sites.json"):
        self.sites_config_path = sites_config_path

    def load_sites(self) -> List[Dict]:
        if not os.path.exists(self.sites_config_path):
            return []
        with open(self.sites_config_path, 'r') as f:
            return json.load(f)

    def trigger_batch(self, user_id: str):
        sites = self.load_sites()
        batch_id = str(uuid.uuid4())[:8]
        audit_logger.info(f"User {user_id} triggered batch job {batch_id} for {len(sites)} sites")
        
        results = []
        for site in sites:
            # In a real enterprise app, we'd fire off Celery tasks or similar.
            # Here we'll just track the intent.
            task_id = f"{batch_id}-{uuid.uuid4().hex[:4]}"
            logger.info(f"Queuing site {site['url']} in batch {batch_id} as task {task_id}")
            results.append({"url": site["url"], "task_id": task_id})
            
        return {"batch_id": batch_id, "tasks": results}

batch_manager = BatchManager()
