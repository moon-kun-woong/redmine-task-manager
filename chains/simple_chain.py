import json
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.utils import load_yaml_prompt, extract_json_from_text

logger = logging.getLogger(__name__)


class CommitAnalysisChain:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
            max_retries=3,
        )

        # prompts 폴더에서 YAML load
        self.system_prompt = load_yaml_prompt("system.yaml")
        self.analysis_template = load_yaml_prompt("analysis.yaml")
        self.documentation_prompt = load_yaml_prompt("documentation.yaml")

    def analyze(
        self,
        commit_data: Dict[str, Any],
        redmine_issues: list,
        gitlab_issue: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:

        try:
            system_msg = SystemMessage(content=self.system_prompt['content'])

            user_content = self._format_user_prompt(
                commit_data,
                redmine_issues,
                gitlab_issue
            )
            user_msg = HumanMessage(content=user_content)

            logger.info(f"Analyzing commit {commit_data.get('commit_hash', 'unknown')}")
            response = self.llm.invoke([system_msg, user_msg])

            result = self._parse_response(response.content)

            if result:
                logger.info(
                    f"Analysis complete: action={result.get('action')}, "
                    f"confidence={result.get('confidence')}%"
                )
                return result
            else:
                logger.error("Failed to parse LLM response")
                return None

        except Exception as e:
            logger.error(f"Error during commit analysis: {e}", exc_info=True)
            return None

    def _format_user_prompt(
        self,
        commit_data: Dict[str, Any],
        redmine_issues: list,
        gitlab_issue: Optional[Dict]
    ) -> str:
        from app.utils import format_file_changes, format_redmine_issues

        template = self.analysis_template['template']

        if gitlab_issue:
            gitlab_issue_info = (
                f"GitLab Issue 참조:\n"
                f"- Issue #{gitlab_issue.get('iid')}: {gitlab_issue.get('title')}\n"
                f"- Description: {gitlab_issue.get('description', 'N/A')[:200]}"
            )
        else:
            gitlab_issue_info = "GitLab Issue: 없음"

        diff_data = commit_data.get('diff_data', {})
        diff_type = diff_data.get('type', 'unknown')

        if diff_type == 'full':
            diff_summary = (
                f"전체 변경사항 ({diff_data['summary']['total_lines']}줄)\n\n"
                f"{format_file_changes(diff_data['diffs'], include_diff=True)}"
            )
        elif diff_type == 'summary':
            diff_summary = (
                f"변경 요약 ({diff_data['summary']['total_lines']}줄)\n\n"
                f"{format_file_changes(diff_data['diffs'], include_diff=True)}"
            )
        else:  # high_level
            diff_summary = (
                f"대규모 변경 ({diff_data['summary']['total_lines']}줄)\n"
                f"상위 변경 파일:\n{format_file_changes(diff_data['diffs'], include_diff=False)}"
            )

        prompt = template.format(
            repository=commit_data.get('repository', 'Unknown'),
            branch=commit_data.get('branch', 'Unknown'),
            author=commit_data.get('author', 'Unknown'),
            commit_hash=commit_data.get('commit_hash', 'Unknown'),
            commit_message=commit_data.get('commit_message', ''),
            files_count=diff_data.get('summary', {}).get('total_files', 0),
            changed_files=format_file_changes(diff_data.get('diffs', [])),
            diff_summary=diff_summary,
            gitlab_issue_info=gitlab_issue_info,
            redmine_issues=format_redmine_issues(redmine_issues)
        )

        return prompt

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        try:
            result = json.loads(response_text)
            return self._validate_result(result)
        except json.JSONDecodeError:
            result = extract_json_from_text(response_text)
            if result:
                return self._validate_result(result)

            logger.error(f"Could not parse JSON from response: {response_text[:200]}")
            return None

    def _validate_result(self, result: Dict) -> Optional[Dict]:
        required_fields = ['action', 'tracker_id', 'priority_id', 'subject', 'done_ratio']

        for field in required_fields:
            if field not in result:
                logger.error(f"Missing required field: {field}")
                return None

        if result['action'] not in ['create', 'update']:
            logger.error(f"Invalid action: {result['action']}")
            return None

        if result['action'] == 'update' and not result.get('redmine_issue_id'):
            logger.error("Update action requires redmine_issue_id")
            return None

        return result

    def document_commit(
        self,
        commit_message: str,
        diff_data: Dict[str, Any],
        author: str
    ) -> Optional[Dict[str, Any]]:
        """
        Commit을 분석하여 문서화하고 진척도/상태를 제안합니다.

        Returns:
            {
                'documentation': str,  # Textile 형식 문서
                'done_ratio': int,     # 0-100
                'status_id': int       # Redmine status ID
            }
        """
        try:
            from app.utils import format_file_changes

            system_msg = SystemMessage(content=self.documentation_prompt['content'])

            diff_summary = diff_data.get('summary', {})
            files_changed = format_file_changes(diff_data.get('diffs', []))

            diff_detail = ""
            diff_type = diff_data.get('type', 'unknown')
            if diff_type == 'full':
                diff_detail = format_file_changes(diff_data.get('diffs', []), include_diff=True)
            else:
                diff_detail = files_changed

            user_msg = HumanMessage(
                content=(
                    f"다음 commit의 변경 내용을 분석하여 문서화하고 진척도/상태를 판단해주세요:\n\n"
                    f"**Commit 메시지** (참고용): {commit_message}\n\n"
                    f"**변경 통계**:\n"
                    f"- 파일: {diff_summary.get('total_files', 0)}개\n"
                    f"- 추가: +{diff_summary.get('total_additions', 0)}줄\n"
                    f"- 삭제: -{diff_summary.get('total_deletions', 0)}줄\n\n"
                    f"**변경 파일 상세**:\n{diff_detail}\n\n"
                    f"위 내용을 분석하여 JSON 형식으로 응답해주세요."
                )
            )

            logger.info("Generating commit documentation...")
            response = self.llm.invoke([system_msg, user_msg])

            result = self._parse_documentation_response(response.content)

            if result:
                logger.info(
                    f"Documentation generated: done_ratio={result.get('done_ratio')}%, "
                    f"status_id={result.get('status_id')}"
                )
                return result
            else:
                logger.error("Failed to parse documentation response")
                return None

        except Exception as e:
            logger.error(f"Error generating commit documentation: {e}", exc_info=True)
            return None

    def _parse_documentation_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Documentation 응답 JSON 파싱"""
        try:
            result = json.loads(response_text)

            if 'documentation' not in result or 'done_ratio' not in result or 'status_id' not in result:
                logger.error("Missing required fields in documentation response")
                return None

            return result

        except json.JSONDecodeError:
            result = extract_json_from_text(response_text)
            if result and 'documentation' in result:
                return result

            logger.error(f"Could not parse JSON from documentation response: {response_text[:200]}")
            return None

    async def analyze_async(
        self,
        commit_data: Dict[str, Any],
        redmine_issues: list,
        gitlab_issue: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:

        return self.analyze(commit_data, redmine_issues, gitlab_issue)
