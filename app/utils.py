import re
import json
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from app.config import PROMPTS_DIR, LOGS_DIR


# Configure logging
def setup_logging(log_level: str = "INFO"):
    log_file = LOGS_DIR / f"app-{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


logger = setup_logging()


def load_yaml_prompt(filename: str) -> Dict[str, Any]:
    file_path = PROMPTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_issue_id_from_message(message: str) -> Optional[int]:
    patterns = [
        r'#(\d+)',
        r'refs\s+#(\d+)',
        r'issue\s+#(\d+)',
        r'fix\s+#(\d+)',
        r'close\s+#(\d+)',
        r'resolve\s+#(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def should_ignore_file(file_path: str, ignored_patterns: list) -> bool:
    from fnmatch import fnmatch

    for pattern in ignored_patterns:
        if fnmatch(file_path, pattern):
            return True
    return False


def extract_json_from_text(text: str) -> Optional[Dict]:

    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def sanitize_sensitive_data(text: str) -> str:
    text = re.sub(
        r'(password|passwd|pwd)\s*[:=]\s*["\']?[^"\'\s]+["\']?',
        r'\1=***',
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r'(api[_-]?key|token|secret)\s*[:=]\s*["\']?[^"\'\s]+["\']?',
        r'\1=***',
        text,
        flags=re.IGNORECASE
    )

    return text


def log_sync_event(event_data: Dict[str, Any]):
    log_file = LOGS_DIR / f"sync-{datetime.now().strftime('%Y-%m-%d')}.log"

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            **event_data,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False) + '\n')


def format_file_changes(diffs: list) -> str:
    lines = []
    for diff in diffs:
        additions = diff.get('additions', 0)
        deletions = diff.get('deletions', 0)
        path = diff.get('path', diff.get('new_path', 'unknown'))
        lines.append(f"- {path} (+{additions}, -{deletions})")

    return '\n'.join(lines)


def format_redmine_issues(issues: list) -> str:
    if not issues:
        return "현재 Open 상태인 issue가 없습니다."

    lines = []
    for idx, issue in enumerate(issues, 1):
        tracker = issue.get('tracker', {}).get('name', 'Unknown')
        status = issue.get('status', {}).get('name', 'Unknown')
        assigned_to = issue.get('assigned_to', {}).get('name', 'Unassigned')
        done_ratio = issue.get('done_ratio', 0)

        lines.append(
            f"{idx}. Issue #{issue['id']}: \"{issue['subject']}\"\n"
            f"   - Tracker: {tracker}\n"
            f"   - Status: {status}\n"
            f"   - Assigned: {assigned_to}\n"
            f"   - Progress: {done_ratio}%\n"
            f"   - Description: {issue.get('description', 'N/A')[:100]}..."
        )

    return '\n\n'.join(lines)


def is_commit_already_processed(commit_sha: str) -> bool:
    """
    Check if commit has already been processed by searching sync logs

    Args:
        commit_sha: Full or short commit SHA

    Returns:
        True if already processed
    """
    import glob
    from pathlib import Path

    log_files = glob.glob(str(LOGS_DIR / "sync-*.log"))

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if commit_sha in content or commit_sha[:8] in content:
                    return True
        except Exception as e:
            logger.warning(f"Error reading log file {log_file}: {e}")
            continue

    return False


def mark_commit_as_processed(commit_sha: str):
    """
    Mark commit as processed in a separate tracking file

    This is a lightweight alternative to checking full sync logs
    """
    tracking_file = LOGS_DIR / "processed_commits.log"

    try:
        with open(tracking_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()}|{commit_sha}\n")
    except Exception as e:
        logger.error(f"Failed to mark commit as processed: {e}")
