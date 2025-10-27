import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.gitlab_client import GitLabClient
from app.redmine_client import RedmineClient


def main():
    print("\n" + "=" * 60)
    print("프로젝트 목록 비교")
    print("=" * 60)

    gitlab = GitLabClient()
    redmine = RedmineClient()

    print("\n[GitLab 프로젝트]")
    try:
        import requests
        url = f"{gitlab.api_url}/projects"
        response = requests.get(url, headers=gitlab.headers, timeout=10)
        response.raise_for_status()
        gitlab_projects = response.json()

        for proj in gitlab_projects:
            print(f"  - {proj['name']} (ID: {proj['id']})")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        gitlab_projects = []

    print("\n[Redmine 프로젝트]")
    redmine_projects = redmine.get_projects()

    if redmine_projects:
        for proj in redmine_projects:
            print(f"  - {proj['name']} (ID: {proj['id']}, Identifier: {proj['identifier']})")
    else:
        print("  ✗ Failed to fetch projects")
        redmine_projects = []

    print("\n" + "=" * 60)
    print("프로젝트 매핑 제안")
    print("=" * 60)
    print("\napp/config.py에 다음과 같이 설정하세요:\n")
    print("PROJECT_MAPPING = {")

    for gl_proj in gitlab_projects:
        gl_name = gl_proj['name']

        matched = False
        for rm_proj in redmine_projects:
            rm_name = rm_proj['name']

            if gl_name == rm_name:
                print(f'    "{gl_name}": "{rm_name}",  # Exact match')
                matched = True
                break
            elif gl_name.lower() == rm_name.lower():
                print(f'    "{gl_name}": "{rm_name}",  # Case-insensitive match')
                matched = True
                break

        if not matched:
            print(f'    "{gl_name}": "???",  # No match found - 수동 설정 필요')

    print("}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
