# Redmine Task Manager

GitLab과 Redmine을 연동하여 commit 정보를 기반으로 자동으로 task를 생성/업데이트하는 LLM 기반 서비스입니다.

## 최근 주요 업데이트 (2025-12)

- **LLM 기반 문서화**: 명시적 issue 참조 시 비즈니스 관점의 문서화 자동 생성, done_ratio/status_id 자동 판단
- **업데이트 이력 관리**: Issue description에 모든 commit 변경사항 누적 기록 (Textile 포맷)
- **자동 프로젝트 매핑**: GitLab repo 이름 + suffix로 Redmine project 자동 매핑
- **청킹 시스템**: 대용량 commit 자동 청킹 처리 (GPT-4o-mini + GPT-4o)
- **날짜 필터**: 최근 7일 이내 업데이트된 issue만 검색 (관련성 향상)
- **로그 자동 정리**: 30일 이상 된 로그 파일 자동 삭제
- **중복 처리 방지**: Webhook 재전송 시에도 중복 처리 방지

## 주요 기능

- GitLab commit 분석 → Redmine issue 자동 생성/업데이트
- LLM 기반 분석 (GPT-4o, GPT-4o-mini)
- 스마트 매칭: 진행중인 issue와 자동 매칭
- 명시적 참조: `#123` 형태로 issue 직접 지정
- 비즈니스 관점 문서화: 작업 목표 중심 설명
- 대용량 commit 처리: 청킹 시스템으로 안정적 처리

## 아키텍처

```
GitLab Push → Webhook → FastAPI → LLM (GPT-4o/mini) → Redmine API
```

자세한 내용: `sequence.md` (Mermaid 다이어그램)

## 설치 및 설정

### 요구사항

- Python 3.10+
- GitLab, Redmine 서버
- OpenAI API Key

### 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 환경 설정

`.env.example`을 복사하여 `.env` 생성 후 편집:

```env
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key-here

# GitLab Configuration
GITLAB_URL=http://192.168.2.201
GITLAB_TOKEN=your-gitlab-token-here
GITLAB_WEBHOOK_SECRET=your-webhook-secret-here

# Redmine Configuration
REDMINE_URL=http://192.168.2.201:3000
REDMINE_API_KEY=your-redmine-api-key-here

# 자동 프로젝트 매핑 (선택)
REDMINE_PROJECT_SUFFIX=::AI  # GitLab repo 이름 + suffix로 Redmine 프로젝트 자동 매핑

# 토큰 최적화 (선택)
TOKEN_BUDGET_LIMIT=25000      # 토큰 예산 (초과 시 청킹 모드)
CHUNK_MAX_LINES=1000          # 청크당 최대 라인 수
CHUNK_MAX_FILES=20            # 청크당 최대 파일 개수

# 날짜 필터링 (선택)
REDMINE_ISSUE_SEARCH_DAYS=7   # 최근 N일 이내 업데이트된 issue만 검색

# 로그 관리 (선택)
LOG_RETENTION_DAYS=30         # 로그 파일 보관 기간 (일)
```

### API Key 발급

- **GitLab**: Settings → Access Tokens (scopes: `read_api`, `read_repository`)
- **Redmine**: My account → API access key
- **OpenAI**: https://platform.openai.com/api-keys

### 프로젝트 매핑 설정

**방법 1: 자동 매핑 (권장)**

`.env`에서 suffix 설정:
```env
REDMINE_PROJECT_SUFFIX=::AI
```
예: "WiseIDS-Frontend" → "WiseIDS-Frontend::AI"

**방법 2: 수동 매핑**

`app/config.py`에서 설정:
```python
PROJECT_MAPPING = {
    "WiseIDS-Frontend": "WiseIDS",
    "WiseIDS-Backend": "WiseIDS",
}
```

**매핑 확인:**
```bash
python scripts/list_projects.py
```

## 실행

```bash
# 개발 모드
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

실행 후 http://localhost:8000 확인

## GitLab Webhook 설정

GitLab Repository → Settings → Webhooks:

- **URL**: `http://your-server-ip:8000/webhook/gitlab`
- **Secret Token**: `.env`의 `GITLAB_WEBHOOK_SECRET`와 동일
- **Trigger**: `Push events` 체크
- **테스트**: "Test" 버튼으로 동작 확인

## 사용 방법

### 케이스 1: 자동 분석

일반적인 commit을 push하면 자동으로 분석:

```bash
git commit -m "fix: 이벤트 로그 검색 오류 수정"
git push
```

**동작:**
1. 진행중인 issue 조회 (최근 7일, 최대 15개)
2. 토큰 수 추정 후 표준/청킹 모드 자동 선택
3. LLM 분석 후 유사도 70% 이상이면 업데이트, 아니면 생성
4. Issue description에 "업데이트 이력" 추가

### 케이스 2: 명시적 issue 참조 (권장)

Commit message에 issue 번호를 명시:

```bash
git commit -m "#668 IP 검색 기능 입력값 검증 강화"
git push
```

**동작:**
1. LLM이 diff 분석 → 비즈니스 관점 문서화 생성
2. Issue description 업데이트 (기존 내용 유지)
3. "업데이트 이력" 섹션에 새 entry 추가
4. done_ratio, status_id 자동 판단

**지원 패턴:** `#123`, `refs #123`, `fix #123`, `close #123`, `resolve #123`

## API 엔드포인트

- `GET /health`: Health check
- `POST /webhook/gitlab`: GitLab webhook 수신
- `POST /test/analyze`: 수동 테스트 (개발용)

## 로그

로그는 `logs/` 디렉토리에 저장됩니다:

- `app-YYYY-MM-DD.log`: 애플리케이션 로그
- `sync-YYYY-MM-DD.log`: Sync 이벤트 로그 (JSON)
- `processed_commits.log`: 처리 완료 commit 추적 (중복 방지용, **삭제 금지**)

**자동 정리:** 30일 이상 된 로그 파일 자동 삭제 (`LOG_RETENTION_DAYS` 설정)

```bash
# 실시간 로그 확인
tail -f logs/app-$(date +%Y-%m-%d).log
```

## 프롬프트 커스터마이징

프롬프트는 `prompts/` 디렉토리의 YAML 파일로 관리됩니다:

- `system.yaml`: 자동 분석 시스템 프롬프트 (역할, 규칙)
- `analysis.yaml`: 표준 분석 템플릿
- `documentation.yaml`: 명시적 참조 시 문서화
- `chunk_analysis.yaml`: 청크 개별 분석 (GPT-4o-mini)
- `synthesis.yaml`: 청크 결과 종합 (GPT-4o)
- `helpers.yaml`: 포맷팅 헬퍼

**수정 방법:**
1. YAML 파일 편집
2. 서버 재시작
3. 테스트 commit으로 검증

## 트러블슈팅

**Webhook 수신 안됨**
- 방화벽 확인 (포트 8000)
- GitLab Webhook 설정에서 Test
- `logs/app-*.log` 확인

**LLM 분석 실패**
- OpenAI API Key 및 잔액 확인
- 로그에서 에러 메시지 확인

**Redmine issue 생성 실패**
- Redmine API Key 및 권한 확인
- Tracker/Priority ID 확인

**프로젝트를 찾을 수 없음**
- `python scripts/list_projects.py` 실행
- `PROJECT_MAPPING` 및 `REDMINE_PROJECT_SUFFIX` 확인

**중복 처리**
- `logs/processed_commits.log`에서 해당 commit SHA 확인 및 삭제

**LLM 응답 이상**
- `prompts/*.yaml` 파일 검토 및 수정
- 서버 재시작 후 테스트

## 테스트 및 유틸리티

```bash
# 연결 테스트
python scripts/test_connection.py

# 프로젝트 매핑 확인
python scripts/list_projects.py

# 수동 Webhook 테스트
curl -X POST http://localhost:8000/webhook/gitlab \
  -H "X-Gitlab-Token: your-secret" \
  -H "X-Gitlab-Event: Push Hook" \
  -H "Content-Type: application/json" \
  -d @test_webhook.json
```

## 설정 튜닝

주요 설정은 `app/config.py`에서 조정 가능합니다:

```python
# Diff 필터링
IGNORED_PATTERNS = ["package-lock.json", "*.min.js", "dist/*", ...]

# Diff 크기 제한
MAX_DIFF_LINES = 500      # Full diff 기준
MAX_SUMMARY_LINES = 2000  # Summary 기준

# LLM 최적화
MAX_ISSUES_FOR_LLM = 15              # LLM 전달 최대 issue 개수
TOKEN_BUDGET_LIMIT = 25000           # 청킹 모드 전환 기준
CHUNK_MAX_LINES = 1000               # 청크당 최대 라인
CHUNK_MAX_FILES = 20                 # 청크당 최대 파일
REDMINE_ISSUE_SEARCH_DAYS = 7        # 최근 N일 issue만 검색

# Redmine 상태 ID
REDMINE_STATUS_IN_PROGRESS = 2       # 진행중
REDMINE_STATUS_RESOLVED = 3          # 해결
```

## 비용 예상

**예상 비용:** 하루 100 commits 기준 약 $3-4/월

- 작은 commit: ~$0.001
- 중간 commit: ~$0.002
- 대용량 commit: ~$0.002 (청킹 시스템으로 50-70% 절감)

자세한 정보는 `CLAUDE.md` 참조

## 향후 개선 사항

- Agent 기반 분석 (자율적 정보 수집)
- Vector DB 연동 (유사 issue 검색)
- 웹 대시보드 (시각화, 통계)
- Commit 분류 모델 개선

## 참고 자료

- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://python.langchain.com/)
- [GitLab Webhooks](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html)
- [Redmine API](https://www.redmine.org/projects/redmine/wiki/Rest_api)

## 라이선스

MIT License

