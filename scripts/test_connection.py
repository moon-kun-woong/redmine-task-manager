import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.gitlab_client import GitLabClient
from app.redmine_client import RedmineClient
from app.config import settings


def test_gitlab():
    print("\n" + "=" * 60)
    print("GitLab 연결 테스트")
    print("=" * 60)

    client = GitLabClient()

    try:
        import requests
        url = f"{client.api_url}/projects"
        response = requests.get(url, headers=client.headers, timeout=10)
        response.raise_for_status()

        projects = response.json()
        print(f"✓ 연결 성공!")
        print(f"✓ 프로젝트 개수: {len(projects)}")

        if projects:
            print("\n프로젝트 목록:")
            for proj in projects[:5]:  # 처음 5개만
                print(f"  - {proj['name']} (ID: {proj['id']})")

        return True

    except Exception as e:
        print(f"✗ 연결 실패: {e}")
        return False


def test_redmine():
    print("\n" + "=" * 60)
    print("Redmine 연결 테스트")
    print("=" * 60)

    client = RedmineClient()

    try:
        projects = client.get_projects()

        if projects is None:
            print("✗ 프로젝트 목록을 가져올 수 없습니다.")
            return False

        print(f"✓ 연결 성공!")
        print(f"✓ 프로젝트 개수: {len(projects)}")

        if projects:
            print("\n프로젝트 목록:")
            for proj in projects[:10]:
                print(f"  - {proj['name']} (ID: {proj['id']}, Identifier: {proj['identifier']})")

        if projects:
            first_project = projects[0]
            issues = client.get_issues(project_id=first_project['id'], status_id='in_progress')

            if issues:
                print(f"\n'{first_project['name']}' 프로젝트의 진행중인 이슈: {len(issues)}개")
                for issue in issues[:3]:
                    print(f"  - #{issue['id']}: {issue['subject']}")

        return True

    except Exception as e:
        print(f"✗ 연결 실패: {e}")
        return False


def test_openai():
    print("\n" + "=" * 60)
    print("OpenAI 연결 테스트")
    print("=" * 60)

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
            max_tokens=50
        )

        response = llm.invoke([HumanMessage(content="Hello, respond with just 'OK'")])

        print(f"✓ 연결 성공!")
        print(f"✓ 응답: {response.content}")

        return True

    except Exception as e:
        print(f"✗ 연결 실패: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("Redmine Task Manager - 연결 테스트")
    print("=" * 60)

    results = {
        "GitLab": test_gitlab(),
        "Redmine": test_redmine(),
        "OpenAI": test_openai()
    }

    print("\n" + "=" * 60)
    print("테스트 결과")
    print("=" * 60)

    for service, success in results.items():
        status = "✓ 성공" if success else "✗ 실패"
        print(f"{service}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n모든 연결 테스트가 성공했습니다! 🎉")
        print("이제 서버를 실행할 수 있습니다: python run.py")
    else:
        print("\n일부 연결 테스트가 실패했습니다.")
        print(".env 파일의 설정을 확인해주세요.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
