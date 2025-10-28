import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.gitlab_client import GitLabClient
from app.redmine_client import RedmineClient
from app.utils import parse_issue_id_from_message, log_sync_event, is_commit_already_processed
from chains.simple_chain import CommitAnalysisChain

logger = logging.getLogger(__name__)


class CommitAnalyzer:

    def __init__(self):
        self.gitlab = GitLabClient()
        self.redmine = RedmineClient()
        self.chain = CommitAnalysisChain()

    def should_skip_commit(self, commit_data: Dict) -> bool:
        message = commit_data.get('message', '').lower()

        if message.startswith('merge'):
            logger.info("Skipping merge commit")
            return True

        if message.startswith('revert'):
            logger.info("Skipping revert commit")
            return True

        if '[bot]' in message or '[skip ci]' in message:
            logger.info("Skipping bot/CI commit")
            return True

        return False

    def process_commit(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:

        result = {
            'status': 'pending',
            'timestamp': datetime.now().isoformat(),
            'webhook_data': webhook_data
        }

        try:
            project_id = webhook_data.get('project_id')
            project_name = webhook_data.get('project', {}).get('name')
            commits = webhook_data.get('commits', [])

            if not commits:
                result['status'] = 'skipped'
                result['reason'] = 'No commits in webhook'
                return result

            for commit in commits:
                commit_result = self._process_single_commit(
                    project_id,
                    project_name,
                    commit,
                    webhook_data
                )

                result['commit_results'] = result.get('commit_results', [])
                result['commit_results'].append(commit_result)

            result['status'] = 'success'

        except Exception as e:
            logger.error(f"Error processing commit: {e}", exc_info=True)
            result['status'] = 'failed'
            result['error'] = str(e)

        finally:
            log_sync_event(result)

        return result

    def _process_single_commit(
        self,
        project_id: int,
        project_name: str,
        commit: Dict,
        webhook_data: Dict
    ) -> Dict[str, Any]:
        commit_sha = commit.get('id')
        commit_message = commit.get('message', '')
        author_name = commit.get('author', {}).get('name', 'Unknown')

        logger.info(f"Processing commit {commit_sha[:8]} in {project_name}")

        result = {
            'commit_sha': commit_sha,
            'status': 'pending'
        }

        if self.should_skip_commit(commit):
            result['status'] = 'skipped'
            result['reason'] = 'Commit type should be skipped'
            return result

        if is_commit_already_processed(commit_sha):
            logger.info(f"Commit {commit_sha[:8]} already processed, skipping")
            result['status'] = 'skipped'
            result['reason'] = 'Commit already processed'
            return result

        commit_detail = self.gitlab.get_commit(project_id, commit_sha)
        if not commit_detail:
            result['status'] = 'failed'
            result['error'] = 'Failed to fetch commit details'
            return result

        commit_diffs = self.gitlab.get_commit_diff(project_id, commit_sha)
        if commit_diffs is None:
            result['status'] = 'failed'
            result['error'] = 'Failed to fetch commit diff'
            return result

        diff_data = self.gitlab.filter_and_summarize_diff(commit_diffs)

        explicit_issue_id = parse_issue_id_from_message(commit_message)

        if explicit_issue_id:
            logger.info(f"Commit explicitly references Redmine issue #{explicit_issue_id}")
            return self._update_explicit_issue(
                explicit_issue_id,
                commit_sha,
                commit_message,
                author_name,
                diff_data
            )

        redmine_project = self.redmine.get_project_by_name(project_name)
        if not redmine_project:
            result['status'] = 'failed'
            result['error'] = f'Redmine project not found: {project_name}'
            return result

        # 오픈되어있는 이슈를 가져옴 (new, in_progress)
        open_issues = self.redmine.get_issues(
            project_id=redmine_project['id'],
            status_id='open'
        )

        if open_issues is None:
            result['status'] = 'failed'
            result['error'] = 'Failed to fetch Redmine issues'
            return result

        gitlab_issue = None
        gitlab_issue_number = self.gitlab.extract_gitlab_issue_from_commit(commit_message)
        if gitlab_issue_number:
            gitlab_issue = self.gitlab.get_issue(project_id, gitlab_issue_number)

        commit_data = {
            'repository': project_name,
            'branch': webhook_data.get('ref', 'unknown').split('/')[-1],
            'author': author_name,
            'commit_hash': commit_sha,
            'commit_message': commit_message,
            'diff_data': diff_data
        }

        logger.info("Calling LLM for analysis...")
        analysis_result = self.chain.analyze(
            commit_data,
            open_issues,
            gitlab_issue
        )

        if not analysis_result:
            result['status'] = 'failed'
            result['error'] = 'LLM analysis failed'
            return result

        if analysis_result['action'] == 'create':
            return self._create_issue(
                redmine_project['id'],
                analysis_result,
                commit_sha,
                author_name
            )
        else:
            return self._update_issue(
                analysis_result['redmine_issue_id'],
                analysis_result,
                commit_sha,
                commit_message,
                author_name
            )

    def _update_explicit_issue(
        self,
        issue_id: int,
        commit_sha: str,
        commit_message: str,
        author: str,
        diff_data: Dict
    ) -> Dict[str, Any]:
        result = {'status': 'pending', 'action': 'update', 'issue_id': issue_id}

        try:
            existing_issue = self.redmine.get_issue(issue_id)
            if not existing_issue:
                result['status'] = 'failed'
                result['error'] = f'Issue #{issue_id} not found'
                return result

            note = (
                f"h4. GitLab Sync\n\n"
                f"* Commit: @{commit_sha[:8]}@\n"
                f"* Author: _{author}_\n"
                f"* Message: {commit_message}\n"
                f"* Changed: *{diff_data['summary']['total_files']}* files "
                f"(+{diff_data['summary']['total_additions']}, "
                f"-{diff_data['summary']['total_deletions']})"
            )

            message_lower = commit_message.lower()
            update_data = {}

            if any(keyword in message_lower for keyword in ['fix', 'resolve', 'close', '수정', '해결']):
                update_data['done_ratio'] = 90
                note += "\n\n[자동 판단: 문제 해결로 진행도 90%로 업데이트]"

            updated = self.redmine.update_issue(issue_id, update_data, notes=note)

            if updated:
                result['status'] = 'success'
                result['updated_issue'] = updated
                logger.info(f"Successfully updated Redmine issue #{issue_id}")
            else:
                result['status'] = 'failed'
                result['error'] = 'Failed to update issue'

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error updating explicit issue: {e}")

        return result

    def _create_issue(
        self,
        project_id: int,
        analysis: Dict,
        commit_sha: str,
        author: str
    ) -> Dict[str, Any]:
        result = {'status': 'pending', 'action': 'create'}

        try:
            issue_data = {
                'project_id': project_id,
                'subject': analysis['subject'],
                'description': (
                    f"{analysis['description']}\n\n"
                    f"---\n\n"
                    f"h4. GitLab Sync Info\n\n"
                    f"* Commit: @{commit_sha[:8]}@\n"
                    f"* Author: _{author}_\n"
                    f"* Confidence: *{analysis.get('confidence', 'N/A')}%*\n\n"
                    f"_Reasoning: {analysis.get('reasoning', 'N/A')}_"
                ),
                'tracker_id': analysis['tracker_id'],
                'priority_id': analysis['priority_id'],
                'done_ratio': analysis['done_ratio'],
                'start_date': datetime.now().strftime('%Y-%m-%d')
            }

            created_issue = self.redmine.create_issue(issue_data)

            if created_issue:
                result['status'] = 'success'
                result['created_issue'] = created_issue
                logger.info(f"Successfully created Redmine issue #{created_issue['id']}")
            else:
                result['status'] = 'failed'
                result['error'] = 'Failed to create issue'

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error creating issue: {e}")

        return result

    def _update_issue(
        self,
        issue_id: int,
        analysis: Dict,
        commit_sha: str,
        commit_message: str,
        author: str
    ) -> Dict[str, Any]:
        result = {'status': 'pending', 'action': 'update', 'issue_id': issue_id}

        try:
            note = (
                f"h4. GitLab Update\n\n"
                f"* Commit: @{commit_sha[:8]}@\n"
                f"* Author: _{author}_\n"
                f"* Message: {commit_message}\n"
                f"* Confidence: *{analysis.get('confidence', 'N/A')}%*\n\n"
                f"_Reasoning: {analysis.get('reasoning', 'N/A')}_"
            )

            update_data = {
                'done_ratio': analysis['done_ratio'],
                'priority_id': analysis['priority_id']
            }

            updated_issue = self.redmine.update_issue(issue_id, update_data, notes=note)

            if updated_issue:
                result['status'] = 'success'
                result['updated_issue'] = updated_issue
                logger.info(f"Successfully updated Redmine issue #{issue_id}")
            else:
                result['status'] = 'failed'
                result['error'] = 'Failed to update issue'

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error updating issue: {e}")

        return result
