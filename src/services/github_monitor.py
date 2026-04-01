import time
import httpx
from src.utils.logger import logger
from src.services.llm_fixer import analyze_and_fix_workflow_error
from src.services.deployer import deploy

def monitor_and_autofix_workflow(deploy_config: dict, deployed_files: dict, target_commit_sha: str, llm_config: dict, progress_callback, max_retries=3):
    """
    Monitors GitHub Actions for the specific branch push matching target_commit_sha.
    If it fails, it pulls the logs, feeds them to the LLM along with the file contents,
    requests a fix, redeploys the files, and loops until success or max_retries.
    """
    token = deploy_config.get("github_token", "")
    repo = deploy_config.get("github_repo", "").replace("https://github.com/", "").strip("/")
    branch = deploy_config.get("github_branch", "main")
    
    # Restrict continuous deployment fixing to main/master per user rule
    if branch.lower() not in ["main", "master"]:
        progress_callback(f"Skipping autonomous monitor (branch '{branch}' is not main/master).")
        return
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    attempts = 0
    current_files = deployed_files.copy()
    current_commit_sha = target_commit_sha
    
    with httpx.Client(timeout=30) as client:
        while attempts <= max_retries:
            progress_callback(f"Waiting 10s for GitHub Actions to trigger (Attempt {attempts}/{max_retries})...")
            time.sleep(10)
            
            run_url = f"https://api.github.com/repos/{repo}/actions/runs"
            params = {"branch": branch, "event": "push", "per_page": 10}
            
            run_id = None
            run_data = None
            
            # Robust polling loop to find the exact workflow run for our commit
            for poll_attempt in range(5):
                try:
                    res = client.get(run_url, headers=headers, params=params)
                    if res.status_code == 200:
                        runs = res.json().get("workflow_runs", [])
                        for r in runs:
                            if not current_commit_sha or r.get("head_sha") == current_commit_sha:
                                run_id = r["id"]
                                run_data = r
                                break
                    if run_id:
                        break
                except httpx.RequestError as e:
                    logger.warning(f"Network error polling GitHub API: {e}")
                
                time.sleep(5)
                
            if not run_id:
                progress_callback(f"Could not find workflow run matching commit {current_commit_sha}. Skipping.")
                return
                
            progress_callback(f"Tracking workflow run ID: {run_id} (SHA: {current_commit_sha})...")
            
            status = run_data["status"]
            conclusion = run_data["conclusion"]
            
            # Poll while the job is active
            while status in ["queued", "in_progress"]:
                progress_callback(f"Workflow {run_id} is {status}. Waiting 15s...")
                time.sleep(15)
                try:
                    run_res = client.get(f"{run_url}/{run_id}", headers=headers)
                    if run_res.status_code == 200:
                        run_data = run_res.json()
                        status = run_data.get("status")
                        conclusion = run_data.get("conclusion")
                    elif run_res.status_code == 404:
                        progress_callback(f"Workflow {run_id} disappeared. Aborting monitor.")
                        return
                    else:
                        logger.error(f"Failed to poll run {run_id}: {run_res.status_code}")
                except httpx.RequestError as e:
                    logger.warning(f"Network error polling workflow status: {e}")
                    time.sleep(5)
                    
            if conclusion == "success":
                progress_callback(f"Workflow {run_id} completed successfully! CI/CD is green.")
                return
                
            if conclusion in ["failure", "cancelled", "timed_out", "action_required"]:
                if attempts == max_retries:
                    progress_callback(f"Workflow {run_id} completely failed ({conclusion}) after {max_retries} retries. Aborting.")
                    raise RuntimeError(f"Workflow failed to compile after {max_retries} LLM fix attempts.")
                    
                progress_callback(f"Workflow {run_id} failed with conclusion: {conclusion}. Fetching logs...")
                
                # Fetch individual job logs to send to LLM
                jobs_url = f"{run_url}/{run_id}/jobs"
                jobs_res = client.get(jobs_url, headers=headers)
                failed_job_id = None
                
                if jobs_res.status_code == 200:
                    for job in jobs_res.json().get("jobs", []):
                        if job.get("conclusion") == "failure":
                            failed_job_id = job["id"]
                            break
                            
                error_log = "Unable to fetch specific failed job logs."
                if failed_job_id:
                    log_url = f"https://api.github.com/repos/{repo}/actions/jobs/{failed_job_id}/logs"
                    log_res = client.get(log_url, headers=headers, follow_redirects=True)
                    if log_res.status_code == 200:
                        error_log = log_res.text
                
                progress_callback("Analyzing workflow failure logs with LLM syntax engine...")
                
                # We need to format the LLM config if passing from plugin context
                # The llm_config comes from the content runner, usually has api_key and provider
                fixed_files = analyze_and_fix_workflow_error(error_log, current_files, llm_config)
                
                if not fixed_files:
                    progress_callback("LLM failed to securely isolate the error or construct valid JSON payload. Aborting.")
                    raise RuntimeError("LLM couldn't interpret the workflow crash natively.")
                    
                progress_callback(f"LLM generated valid patches for {len(fixed_files)} files. Redeploying changes...")
                
                for fpath, fcontent in fixed_files.items():
                    # Redeploy patched code back to GitHub
                    deploy_res = deploy(fpath, fcontent, deploy_config)
                    if not deploy_res.get("success"):
                        progress_callback(f"Failed to push fixed file: {fpath}")
                    else:
                        if deploy_res.get("commit_sha"):
                            current_commit_sha = deploy_res.get("commit_sha")
                    current_files[fpath] = fcontent # Keep local tracker updated
                    
                attempts += 1
                progress_callback(f"Redeployment pushed (New SHA: {current_commit_sha}). Rebooting workflow monitor loop...")
            else:
                progress_callback(f"Workflow concluded externally with unknown state: {conclusion}")
                break
