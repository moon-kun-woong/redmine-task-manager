import logging
from typing import Dict, List, Optional, Any
import requests
from app.config import settings
from app.utils import should_ignore_file

logger = logging.getLogger(__name__)


class GitLabClient:

    def __init__(self):
        self.base_url = settings.GITLAB_URL.rstrip('/')
        self.api_url = f"{self.base_url}/api/v4"
        self.token = settings.GITLAB_TOKEN
        self.headers = {
            "PRIVATE-TOKEN": self.token
        }

    def get_commit(self, project_id: int, commit_sha: str) -> Optional[Dict]:
        try:
            url = f"{self.api_url}/projects/{project_id}/repository/commits/{commit_sha}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get commit {commit_sha}: {e}")
            return None

    def get_commit_diff(self, project_id: int, commit_sha: str) -> Optional[List[Dict]]:
        try:
            url = f"{self.api_url}/projects/{project_id}/repository/commits/{commit_sha}/diff"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get commit diff {commit_sha}: {e}")
            return None

    def get_project(self, project_id: int) -> Optional[Dict]:
        try:
            url = f"{self.api_url}/projects/{project_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None

    def get_merge_request(self, project_id: int, mr_iid: int) -> Optional[Dict]:
        try:
            url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get MR {mr_iid}: {e}")
            return None

    def _truncate_diff(self, diff_content: str, max_lines: int = 20) -> str:

        if not diff_content:
            return ""

        lines = diff_content.split('\n')

        if len(lines) <= max_lines:
            return diff_content

        important_lines = []
        for line in lines:
            if line.startswith('@@') or line.startswith('+') or line.startswith('-'):
                important_lines.append(line)
                if len(important_lines) >= max_lines:
                    break

        result = '\n'.join(important_lines)
        if len(lines) > len(important_lines):
            result += f"\n... ({len(lines) - len(important_lines)} more lines)"

        return result

    def filter_and_summarize_diff(self, diffs: List[Dict]) -> Dict[str, Any]:

        filtered_diffs = [
            diff for diff in diffs
            if not should_ignore_file(
                diff.get('new_path', diff.get('old_path', '')),
                settings.IGNORED_PATTERNS
            )
        ]

        total_additions = sum(diff.get('additions', 0) for diff in filtered_diffs)
        total_deletions = sum(diff.get('deletions', 0) for diff in filtered_diffs)
        total_lines = total_additions + total_deletions

        summary = {
            'total_files': len(filtered_diffs),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_lines': total_lines,
        }

        if total_lines < settings.MAX_DIFF_LINES:
            return {
                'type': 'full',
                'diffs': [
                    {
                        'path': diff.get('new_path', diff.get('old_path')),
                        'additions': diff.get('additions', 0),
                        'deletions': diff.get('deletions', 0),
                        'diff': diff.get('diff', ''),  # Include actual diff content
                    }
                    for diff in filtered_diffs
                ],
                'summary': summary
            }
        elif total_lines < settings.MAX_SUMMARY_LINES:
            return {
                'type': 'summary',
                'diffs': [
                    {
                        'path': diff.get('new_path', diff.get('old_path')),
                        'additions': diff.get('additions', 0),
                        'deletions': diff.get('deletions', 0),
                        'diff_preview': self._truncate_diff(diff.get('diff', ''), max_lines=20),
                    }
                    for diff in filtered_diffs
                ],
                'summary': summary
            }
        else:
            sorted_diffs = sorted(
                filtered_diffs,
                key=lambda d: d.get('additions', 0) + d.get('deletions', 0),
                reverse=True
            )[:10]

            return {
                'type': 'high_level',
                'diffs': [
                    {
                        'path': diff.get('new_path', diff.get('old_path')),
                        'lines': diff.get('additions', 0) + diff.get('deletions', 0),
                    }
                    for diff in sorted_diffs
                ],
                'summary': summary
            }

    def extract_gitlab_issue_from_commit(self, commit_message: str) -> Optional[int]:
        import re

        patterns = [
            r'#(\d+)',
            r'gitlab\s+#(\d+)',
            r'issue\s+#(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, commit_message, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def get_issue(self, project_id: int, issue_iid: int) -> Optional[Dict]:
        try:
            url = f"{self.api_url}/projects/{project_id}/issues/{issue_iid}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get issue {issue_iid}: {e}")
            return None
