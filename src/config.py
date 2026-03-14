import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "SEO Autonomous Plugin"
    DEBUG: bool = False
    
    # Automation / Global Deployment Settings
    AUTOMATION_PLATFORM: str = "filesystem" # filesystem, github, ftp, webhook
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "user/repo")
    GITHUB_BRANCH: str = os.getenv("GITHUB_BRANCH", "main")
    
    FTP_HOST: str = os.getenv("FTP_HOST", "")
    FTP_USER: str = os.getenv("FTP_USER", "")
    FTP_PASSWORD: str = os.getenv("FTP_PASSWORD", "")
    FTP_BASE_DIR: str = os.getenv("FTP_BASE_DIR", "/public_html")
    
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_TOKEN: str = os.getenv("WEBHOOK_TOKEN", "")

    # LLM Settings for Page Generation
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai") # openai, gemini, ollama
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    # Crawler Settings
    CRAWL_LIMIT: int = 100
    CRAWL_TIMEOUT: int = 30
    
    # Storage Settings
    TASK_STORE_PATH: str = "tasks.json"

    class Config:
        env_file = ".env"

config = Settings()
