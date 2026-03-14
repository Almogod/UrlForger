# src/services/deployer.py
"""
Deploys fixed HTML files back to the target website.
Supports four deployment strategies:
  - filesystem: write directly to a local path
  - github:     commit files via the GitHub API
  - ftp:        upload via ftplib
  - webhook:    POST file content to a configured endpoint
"""

import os
import base64
from pathlib import Path
from src.utils.logger import logger


def deploy(file_path: str, content: str, config: dict) -> dict:
    """
    Deploy a single file.

    Args:
        file_path: relative path inside the site (e.g. 'blog/my-post.html')
        content:   full HTML content string
        config:    dict with keys: platform, and platform-specific settings

    Returns:
        dict with: success, platform, file_path, message
    """
    platform = config.get("platform", "filesystem").lower()

    try:
        if platform == "filesystem":
            return _deploy_filesystem(file_path, content, config)
        elif platform == "github":
            return _deploy_github(file_path, content, config)
        elif platform == "ftp":
            return _deploy_ftp(file_path, content, config)
        elif platform == "webhook":
            return _deploy_webhook(file_path, content, config)
        else:
            return {"success": False, "message": f"Unknown platform: {platform}"}
    except Exception as e:
        logger.error("Deploy failed for %s: %s", file_path, str(e))
        return {"success": False, "platform": platform, "file_path": file_path, "message": str(e)}


# ─────────────────────────────────────────────────────────
# FILESYSTEM
# ─────────────────────────────────────────────────────────

def _deploy_filesystem(file_path: str, content: str, config: dict) -> dict:
    base_dir = config.get("base_dir", "./output")
    full_path = Path(base_dir) / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "platform": "filesystem",
        "file_path": str(full_path),
        "message": "File written successfully"
    }


# ─────────────────────────────────────────────────────────
# GITHUB API
# ─────────────────────────────────────────────────────────

def _deploy_github(file_path: str, content: str, config: dict) -> dict:
    import httpx

    token = config.get("github_token") or os.environ.get("GITHUB_TOKEN", "")
    repo = config.get("github_repo", "")  # format: "owner/repo"
    branch = config.get("github_branch", "main")
    commit_message = config.get("commit_message", f"SEO plugin: update {file_path}")

    if not token or not repo:
        raise ValueError("github_token and github_repo are required for GitHub deployment")

    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Check if file exists to get its SHA
    sha = None
    with httpx.Client() as client:
        existing = client.get(api_url, headers=headers, params={"ref": branch})
        if existing.status_code == 200:
            sha = existing.json().get("sha")

        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_message,
            "content": encoded,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        response = client.put(api_url, headers=headers, json=payload)
        response.raise_for_status()

    return {
        "success": True,
        "platform": "github",
        "file_path": file_path,
        "repo": repo,
        "branch": branch,
        "message": "Committed successfully"
    }


# ─────────────────────────────────────────────────────────
# FTP
# ─────────────────────────────────────────────────────────

def _deploy_ftp(file_path: str, content: str, config: dict) -> dict:
    import ftplib
    from io import BytesIO

    host = config.get("ftp_host", "")
    user = config.get("ftp_user", "")
    password = config.get("ftp_password", "")
    base_dir = config.get("ftp_base_dir", "/public_html")

    remote_path = f"{base_dir}/{file_path}"

    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)

        # Ensure directory exists
        parts = remote_path.split("/")[:-1]
        current = ""
        for part in parts:
            if not part:
                continue
            current += f"/{part}"
            try:
                ftp.mkd(current)
            except ftplib.error_perm:
                pass  # already exists

        ftp.storbinary(f"STOR {remote_path}", BytesIO(content.encode("utf-8")))

    return {
        "success": True,
        "platform": "ftp",
        "file_path": remote_path,
        "message": "Uploaded via FTP"
    }


# ─────────────────────────────────────────────────────────
# WEBHOOK
# ─────────────────────────────────────────────────────────

def _deploy_webhook(file_path: str, content: str, config: dict) -> dict:
    import httpx

    webhook_url = config.get("webhook_url", "")
    webhook_token = config.get("webhook_token", "")

    if not webhook_url:
        raise ValueError("webhook_url is required for webhook deployment")

    headers = {"Content-Type": "application/json"}
    if webhook_token:
        headers["Authorization"] = f"Bearer {webhook_token}"

    payload = {
        "file_path": file_path,
        "content": content
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(webhook_url, json=payload, headers=headers)
        response.raise_for_status()

    return {
        "success": True,
        "platform": "webhook",
        "file_path": file_path,
        "message": f"Webhook responded: {response.status_code}"
    }
