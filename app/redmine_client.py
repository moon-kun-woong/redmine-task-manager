import logging
from typing import Dict, List, Optional, Any
import requests
from app.config import settings

logger = logging.getLogger(__name__)


class RedmineClient:
    def __init__(self):
        self.base_url = settings.REDMINE_URL.rstrip('/')
        self.api_key = settings.REDMINE_API_KEY
        self.headers = {
            "X-Redmine-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def get_projects(self) -> Optional[List[Dict]]:
        try:
            url = f"{self.base_url}/projects.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get('projects', [])
        except requests.RequestException as e:
            logger.error(f"Failed to get projects: {e}")
            return None

    def get_project_by_name(self, name: str) -> Optional[Dict]:
        if name in settings.PROJECT_MAPPING:
            mapped_name = settings.PROJECT_MAPPING[name]
            logger.info(f"Using PROJECT_MAPPING: {name} -> {mapped_name}")
        else:
            mapped_name = f"{name}{settings.REDMINE_PROJECT_SUFFIX}"
            logger.info(f"Using suffix mapping: {name} -> {mapped_name}")

        projects = self.get_projects()
        if not projects:
            return None

        for project in projects:
            if project['name'] == mapped_name or project['identifier'] == mapped_name.lower():
                logger.info(f"Found Redmine project: {project['name']} (id: {project['id']})")
                return project

        for project in projects:
            if project['name'].lower() == mapped_name.lower():
                logger.info(f"Found Redmine project (case-insensitive): {project['name']} (id: {project['id']})")
                return project

        logger.warning(f"Redmine project not found for GitLab repo '{name}' (looking for: '{mapped_name}')")
        logger.info(f"To fix: Create a Redmine project named '{mapped_name}' or add mapping in PROJECT_MAPPING")
        return None

    def get_issues(
        self,
        project_id: Optional[int] = None,
        status_id: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:

        try:
            url = f"{self.base_url}/issues.json"
            params = {'limit': limit}

            if project_id:
                params['project_id'] = project_id

            if status_id == 'in_progress':
                params['status_id'] = settings.REDMINE_STATUS_IN_PROGRESS
            elif status_id == 'open':
                params['status_id'] = 'open'
            elif status_id:
                params['status_id'] = status_id

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('issues', [])
        except requests.RequestException as e:
            logger.error(f"Failed to get issues: {e}")
            return None

    def get_issue(self, issue_id: int) -> Optional[Dict]:
        try:
            url = f"{self.base_url}/issues/{issue_id}.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get('issue')
        except requests.RequestException as e:
            logger.error(f"Failed to get issue {issue_id}: {e}")
            return None

    def create_issue(self, issue_data: Dict[str, Any]) -> Optional[Dict]:

        try:
            url = f"{self.base_url}/issues.json"
            payload = {"issue": issue_data}

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            created_issue = response.json().get('issue')
            logger.info(f"Created Redmine issue #{created_issue['id']}: {issue_data['subject']}")
            return created_issue

        except requests.RequestException as e:
            logger.error(f"Failed to create issue: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None

    def update_issue(
        self,
        issue_id: int,
        issue_data: Dict[str, Any],
        notes: Optional[str] = None
    ) -> Optional[Dict]:

        try:
            url = f"{self.base_url}/issues/{issue_id}.json"
            payload = {"issue": issue_data}

            if notes:
                payload["issue"]["notes"] = notes

            response = requests.put(
                url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Updated Redmine issue #{issue_id}")
            return self.get_issue(issue_id)

        except requests.RequestException as e:
            logger.error(f"Failed to update issue {issue_id}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None

    def search_issues_by_subject(
        self,
        project_id: int,
        keywords: List[str],
        status_id: Optional[str] = 'in_progress'
    ) -> List[Dict]:

        issues = self.get_issues(project_id=project_id, status_id=status_id)
        if not issues:
            return []

        scored_issues = []
        for issue in issues:
            subject = issue.get('subject', '').lower()
            description = issue.get('description', '').lower()

            score = 0
            for keyword in keywords:
                keyword = keyword.lower()
                if keyword in subject:
                    score += 3 
                if keyword in description:
                    score += 1

            if score > 0:
                scored_issues.append((score, issue))

        scored_issues.sort(key=lambda x: x[0], reverse=True)

        return [issue for score, issue in scored_issues]
