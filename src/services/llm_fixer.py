# src/services/llm_fixer.py
import json
import re
from src.utils.logger import logger

def analyze_and_fix_workflow_error(error_logs: str, deployed_files: dict, llm_config: dict) -> dict:
    """
    Sends the GitHub Actions workflow error log and the recently deployed files to the LLM.
    Returns a dictionary mapping file_path -> new_corrected_content.
    """
    files_str = ""
    for file_path, content in deployed_files.items():
        files_str += f"\n--- {file_path} ---\n{content}\n"

    prompt = f"""You are an expert CI/CD DevOps Engineer and Frontend Developer fixing a broken GitHub Actions workflow.

We recently deployed some automated SEO and Content updates to a repository, but the GitHub Actions workflow immediately failed (e.g., a build error, syntax error, or Next.js build crash).

Here is the tail of the GitHub Actions error log:
```
{error_logs[-3000:]} # Keep the last 3000 chars of the log
```

Here are the exact file contents we just deployed that likely caused the error:
{files_str}

Your job is to identify the syntactic or structural error in these specific files that caused the build to fail, and output the completely corrected files. 
Do not explain your thought process outside of the JSON block.

You must reply strictly with a JSON object where the keys are the file paths, and the values are the complete, corrected file contents.

Example format:
```json
{{
  "pages/example-keyword.jsx": "// entirely corrected react component code here",
  "blog/post.html": "<html>completely corrected markup</html>"
}}
```
"""

    provider = llm_config.get("provider", "openai")
    try:
        if provider == "openai":
            response = _call_openai_fixer(prompt, llm_config)
        elif provider == "gemini":
            response = _call_gemini_fixer(prompt, llm_config)
        else:
            response = _call_ollama_fixer(prompt, llm_config)
            
        return _parse_json_response(response)
    except Exception as e:
        logger.error(f"LLM Fixer failed: {e}")
        return {}


def _parse_json_response(text: str) -> dict:
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM JSON response")
        return {}


def _call_openai_fixer(prompt: str, config: dict) -> str:
    import openai
    client = openai.OpenAI(api_key=config.get("api_key", ""))
    model = config.get("model", "gpt-4o")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an automated code fixing agent. Return strict JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()


def _call_gemini_fixer(prompt: str, config: dict) -> str:
    import google.generativeai as genai
    genai.configure(api_key=config.get("api_key", ""))
    # Use Pro model for coding logic
    model = genai.GenerativeModel("gemini-1.5-pro", generation_config={"temperature": 0.2})
    response = model.generate_content(prompt)
    return response.text.strip()


def _call_ollama_fixer(prompt: str, config: dict) -> str:
    import httpx
    host = config.get("ollama_host", "http://localhost:11434")
    model = config.get("model", "llama3")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2}
    }
    with httpx.Client(timeout=120) as client:
        res = client.post(f"{host}/api/generate", json=payload)
        res.raise_for_status()
        return res.json().get("response", "").strip()
