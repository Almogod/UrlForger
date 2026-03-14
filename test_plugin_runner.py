# test_plugin_runner.py
"""
Simple test script to verify the plugin runner logic.
This will perform a dry-run (filesystem deployment) on a target site.
"""

import uuid
import os
from src.plugin.plugin_runner import run_plugin
from src.config import config

# CONFIGURATION FOR TEST
TEST_DOMAIN = "https://example.com"
TEST_COMPETITORS = ["https://competitor1.com", "https://competitor2.com"]
TEST_TASK_ID = f"test-{uuid.uuid4().hex[:8]}"

def test():
    print(f"🚀 Starting plugin test for {TEST_DOMAIN}")
    print(f"Task ID: {TEST_TASK_ID}")

    deploy_config = {
        "platform": "filesystem",
        "base_dir": "./test_output"
    }

    llm_config = {
        "provider": "openai",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4o-mini"
    }

    crawl_options = {
        "use_js": False,
        "limit": 5,
        "timeout": 30
    }

    try:
        run_plugin(
            site_url=TEST_DOMAIN,
            task_id=TEST_TASK_ID,
            deploy_config=deploy_config,
            llm_config=llm_config,
            competitors=TEST_COMPETITORS,
            crawl_options=crawl_options
        )
        print("\n✅ Plugin run completed. Check test_output/ for results.")
    except Exception as e:
        print(f"\n❌ Plugin run failed: {e}")

if __name__ == "__main__":
    test()
