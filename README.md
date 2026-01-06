# Redmine Task Manager

GitLab과 Redmine을 연동하여 commit 정보를 기반으로 자동으로 task를 생성/업데이트하는 LLM 기반 서비스입니다.

## 최근 주요 업데이트 (2025-12)

### 새로 추가된 기능

1. **LLM 기반 문서화 시스템** (`prompts/documentation.yaml`)
   - 명시적 issue 참조 시 LLM이 commit을 분석하여 비즈니스 관점의 문서화 자동 생성
   - done_ratio와 status_id를 LLM이 자동 판단
   - 코드 레벨이 아닌 작업/기능 레벨로 설명

2. **Issue 업데이트 이력 관리**
   - Redmine issue description에 "업데이트 이력" 섹션 자동 관리
   - 모든 commit 변경사항을 누적 기록
   - Textile 포맷으로 깔끔한 포맷팅

3. **자동 프로젝트 매핑** (`REDMINE_PROJECT_SUFFIX`)
   - GitLab repo 이름에 suffix를 붙여서 Redmine project 자동 매핑
   - 수동 매핑 없이도 프로젝트 연동 가능
   - 예: "WiseIDS-Frontend" → "WiseIDS-Frontend::AI"

4. **토큰 최적화 및 청킹 시스템**
   - 대용량 diff에 대한 자동 청킹 처리
   - 토큰 예산(25,000 토큰) 초과 시 자동으로 청킹 모드 전환
   - GPT-4o-mini로 청크 분석 후 GPT-4o로 종합 분석
   - 비용 절감 (50-70%) 및 대용량 commit 안정 처리

5. **날짜 필터링 시스템**
   - 최근 7일 이내 업데이트된 issue만 검색 (`REDMINE_ISSUE_SEARCH_DAYS`)
   - LLM 부하 감소 및 관련성 높은 issue에 집중
   - 오래된 issue는 자동으로 제외

6. **로그 자동 정리**
   - 30일 이상 된 로그 파일 자동 삭제
   - 서버 시작 시 및 24시간마다 백그라운드에서 실행

7. **중복 처리 방지**
   - `logs/processed_commits.log`로 처리된 commit 추적
   - Webhook 재전송 시에도 중복 처리 방지

### 주요 변경사항

- ✅ 명시적 issue 참조 시: **notes → description 업데이트**로 변경
- ✅ LLM이 done_ratio/status_id 자동 판단 (키워드 기반 X)
- ✅ Issue 생성/업데이트 시 업데이트 이력 자동 추가
- ✅ LLM 토큰 최적화: 최대 15개 issue만 전달
- ✅ 토큰 예산 초과 시 자동 청킹 처리로 대용량 commit 지원
- ✅ GPT-4o-mini 추가로 비용 최적화 (청크 분석용)
- ✅ 최근 7일 이내 업데이트된 issue만 조회 (관련성 향상)

## 주요 기능

- **자동 Task 관리**: GitLab commit을 분석하여 Redmine issue 자동 생성/업데이트
- **LLM 기반 분석**: GPT-4o 및 GPT-4o-mini를 사용하여 commit의 의도와 내용을 이해
- **스마트 매칭**: 진행중인 issue와 자동 매칭 (최근 7일 이내 업데이트된 issue 우선)
- **명시적 참조 지원**: Commit message에 `#123` 형태로 issue를 직접 지정 가능
- **비즈니스 관점 문서화**: 코드가 아닌 작업 목표 중심으로 설명 생성
- **자동 프로젝트 매핑**: 수동 설정 없이 GitLab repo → Redmine project 자동 연결
- **대용량 commit 처리**: 청킹 시스템으로 수천 줄 변경도 안정적 처리 (비용 50-70% 절감)

## 시스템 구조

```
GitLab Webhook → FastAPI Server → LLM Analysis → Redmine API
                      ↓
                  Logs 기록
```

## 설치 및 설정

### 1. 요구사항

- Python 3.10 이상
- GitLab (사내 서버)
- Redmine (사내 서버)
- OpenAI API Key

### 2. 설치

```bash
# 저장소 클론
cd redmine-task-manager

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 API 키와 URL 설정:

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

### 4. API Key 발급

**GitLab Personal Access Token:**
1. GitLab → Settings → Access Tokens
2. Scopes: `read_api`, `read_repository` 선택
3. 생성된 token을 `GITLAB_TOKEN`에 설정

**Redmine API Key:**
1. Redmine → My account → API access key
2. Show 클릭하여 key 확인
3. `REDMINE_API_KEY`에 설정

**OpenAI API Key:**
1. https://platform.openai.com/api-keys
2. Create new secret key
3. `OPENAI_API_KEY`에 설정

### 5. 프로젝트 매핑 설정

프로젝트 매핑은 다음 우선순위로 동작합니다:

#### 방법 1: 자동 매핑 (권장)

`.env`에서 `REDMINE_PROJECT_SUFFIX` 설정:

```env
REDMINE_PROJECT_SUFFIX=::AI
```

- GitLab repo 이름에 suffix를 붙여 Redmine project 자동 매핑
- 예: "WiseIDS-Frontend" → "WiseIDS-Frontend::AI"
- 별도 설정 없이 간편하게 사용 가능

#### 방법 2: 수동 매핑

GitLab repository 이름과 Redmine project 이름이 완전히 다른 경우, `app/config.py`에서 수동 매핑:

```python
PROJECT_MAPPING = {
    "WiseIDS-Frontend": "WiseIDS",
    "WiseIDS-Backend": "WiseIDS",
    "mobile-app": "Mobile App",
}
```

**매핑 우선순위:**
1. `PROJECT_MAPPING`에서 정확한 매칭 우선 (대소문자 구분)
2. 없으면 `{GitLab Repo Name}{REDMINE_PROJECT_SUFFIX}` 시도
3. 둘 다 실패하면 에러 반환

**프로젝트 목록 확인:**

```bash
python scripts/list_projects.py
```

이 스크립트로 GitLab과 Redmine 프로젝트 목록을 확인하고 자동 매핑 결과를 미리 볼 수 있습니다.

## 실행

### 개발 모드

```bash
python -m app.main
```

또는

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션 모드

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

서버가 실행되면 http://localhost:8000 에서 확인 가능합니다.

## GitLab Webhook 설정

### 1. Webhook 추가

GitLab Repository → Settings → Webhooks:

- **URL**: `http://your-server-ip:8000/webhook/gitlab`
- **Secret Token**: `.env`의 `GITLAB_WEBHOOK_SECRET`와 동일하게 설정
- **Trigger**: `Push events` 체크
- **SSL verification**: 사내망이면 Disable 가능

### 2. 테스트

Webhook 설정 후 "Test" 버튼으로 테스트:
- Push events 선택
- 서버 로그에서 수신 확인

## 사용 방법

### 케이스 1: 자동 분석

일반적인 commit을 push하면 자동으로 분석:

```bash
git commit -m "fix: 이벤트 로그 검색 오류 수정"
git push
```

**동작:**
1. 진행중인 Redmine issue 조회 (new + in_progress 상태, 최근 7일 이내, 최대 15개)
2. 토큰 수 추정 및 청킹 여부 판단
   - 토큰 < 25,000: 표준 분석 (GPT-4o)
   - 토큰 ≥ 25,000: 청킹 분석 (GPT-4o-mini → GPT-4o)
3. LLM이 commit과 issue들을 분석하여 관련성 판단
4. 유사도 70% 이상이면 기존 issue 업데이트, 아니면 새 issue 생성
5. Issue description에 "업데이트 이력" 섹션 추가/업데이트
6. done_ratio, priority_id 등을 LLM이 자동 판단

### 케이스 2: 명시적 issue 참조 (권장)

Commit message에 issue 번호를 명시:

```bash
git commit -m "#668 IP 검색 기능 입력값 검증 강화"
git push
```

**동작:**
1. LLM이 commit diff를 분석하여 **비즈니스 관점의 문서화** 생성
2. Redmine issue #668의 **description** 업데이트 (기존 내용 유지)
3. "업데이트 이력" 섹션에 새 entry 추가 (Textile 포맷)
4. done_ratio와 status_id를 LLM이 자동 판단하여 업데이트

**출력 예시:**
```
h3. 업데이트 이력

h4. 2025-12-15 14:30:00

* IP 검색 기능 입력값 검증 강화
* 잘못된 입력 방지 및 사용자 피드백 개선
* API 호출 최적화로 불필요한 요청 제거

*Commit*: @abc12345@
*변경*: 3개 파일 (@+15@ / @-7@)
```

**지원하는 패턴:**
- `#123`
- `refs #123`
- `fix #123`
- `close #123`
- `resolve #123`

**차이점:**
- ❌ 이전: notes에 commit 정보만 추가, fix 키워드 기반 done_ratio=90
- ✅ 현재: LLM이 diff 분석 → 문서화 + done_ratio/status_id 자동 판단, description 업데이트

## API 엔드포인트

### Health Check

```bash
GET /health
```

응답:
```json
{
  "status": "healthy",
  "gitlab_url": "http://192.168.2.201",
  "redmine_url": "http://192.168.2.201:3000",
  "queue_size": 0
}
```

### Webhook

```bash
POST /webhook/gitlab
Headers:
  X-Gitlab-Token: your-secret
  X-Gitlab-Event: Push Hook
Body: GitLab webhook payload
```

### 테스트 분석 (개발용)

```bash
POST /test/analyze
Body: {
  "project_id": 123,
  "commits": [...]
}
```

## 로그

로그는 `logs/` 디렉토리에 저장됩니다:

### app-YYYY-MM-DD.log
일반 애플리케이션 로그 (INFO, WARNING, ERROR 레벨)

```
2025-12-15 14:30:00 - INFO - Processing commit abc1234...
2025-12-15 14:30:05 - INFO - Created issue #123
```

### sync-YYYY-MM-DD.log
Sync 이벤트 로그 (JSON 형식) - 분석 및 통계에 활용

```json
{
  "status": "success",
  "timestamp": "2025-12-15T14:30:00",
  "webhook_data": {...},
  "commit_results": [...]
}
```

### processed_commits.log
처리 완료 commit 추적 (중복 방지용) - **삭제하지 마세요**

```
2025-12-15T14:30:00|abc12345678901234567890123456789012345678
2025-12-15T14:35:00|def98765432109876543210987654321098765432
```

**용도:**
- Webhook 재전송 시 중복 처리 방지
- 각 줄: 타임스탬프|full_commit_sha

### 로그 자동 정리

서버 시작 시 및 24시간마다 자동으로 오래된 로그 파일을 삭제합니다.

**설정:**
```env
LOG_RETENTION_DAYS=30  # 기본값: 30일
```

**동작:**
- `app-*.log`, `sync-*.log` 파일만 삭제
- `processed_commits.log`는 삭제되지 않음 (중복 방지 목적)
- 서버 시작 시 즉시 1회 실행 후 24시간마다 백그라운드에서 실행

**로그 확인:**
```bash
# 실시간 로그 확인
tail -f logs/app-$(date +%Y-%m-%d).log

# 모든 로그 파일 목록
ls -lh logs/
```

## 프롬프트 커스터마이징

프롬프트는 `prompts/` 디렉토리의 YAML 파일로 관리:

### system.yaml
**용도:** 자동 분석 시 LLM 시스템 프롬프트 (역할, 규칙)

**주요 규칙:**
- Tracker 판단: fix/bug → 결함(1), feat/add → 기능(2), refactor → 개선(3)
- Priority 판단: hotfix → 긴급(1), main branch → 높음(2)
- Done ratio 판단: WIP → 30%, fix → 90%
- 유사도 70% 이상이면 업데이트, 아니면 생성

### analysis.yaml
**용도:** 자동 분석 요청 템플릿 (명시적 참조 없는 경우)

**변수:** repository, branch, author, commit_hash, commit_message, diff_summary, gitlab_issue_info, redmine_issues

### documentation.yaml
**용도:** 명시적 issue 참조 시 문서화 프롬프트

**주요 규칙:**
- 코드 파일명/함수명이 아닌 **작업 목표** 중심으로 설명
- Redmine Textile 형식 (`* ` 불릿 포인트)
- 3-5개 항목으로 간결하게
- done_ratio 자동 판단 (0-100%)
- status_id 자동 판단 (1:New, 2:In Progress, 3:Resolved, 5:Closed)

**출력 예시:**
```json
{
  "documentation": "* IP 검색 기능 입력값 검증 강화\n* 잘못된 입력 방지...",
  "done_ratio": 70,
  "status_id": 2
}
```

### chunk_analysis.yaml
**용도:** 대용량 commit의 청크를 개별 분석

**주요 규칙:**
- 각 청크의 변경사항 요약
- 주요 변경 사항 추출
- 관련 가능성 있는 Redmine issue 추측

**출력 형식:**
```json
{
  "chunk_summary": "이 청크의 변경사항 요약",
  "key_changes": ["주요 변경 1", "주요 변경 2"],
  "potential_issues": ["관련 issue ID 또는 설명"]
}
```

**모델:** GPT-4o-mini (비용 절감)

### synthesis.yaml
**용도:** 모든 청크 분석 결과를 종합하여 최종 판단

**주요 규칙:**
- 모든 청크 결과를 종합 분석
- 전체 commit의 목적 파악
- 최종 action (create/update) 결정

**출력:** system.yaml의 표준 출력과 동일

**모델:** GPT-4o (정확한 종합 분석)

### helpers.yaml
**용도:** 포맷팅 헬퍼

**프롬프트 수정 시:**
1. YAML 파일 편집
2. 서버 재시작 (reload 지원 안 됨)
3. 테스트 commit으로 검증

**프롬프트 파일 목록:**
- `system.yaml`: 자동 분석 시스템 프롬프트
- `analysis.yaml`: 표준 분석 템플릿
- `documentation.yaml`: 명시적 참조 시 문서화
- `chunk_analysis.yaml`: 청크 개별 분석 (GPT-4o-mini)
- `synthesis.yaml`: 청크 결과 종합 (GPT-4o)
- `helpers.yaml`: 포맷팅 헬퍼

## 트러블슈팅

### Webhook이 수신되지 않음

1. 방화벽 확인: 서버 포트(8000) 오픈 확인
2. GitLab에서 테스트: Webhooks 설정에서 "Test" 클릭
3. 로그 확인: `logs/app-*.log` 파일 확인

### LLM 분석 실패

1. OpenAI API Key 확인
2. API 잔액 확인
3. 로그에서 에러 메시지 확인
4. Diff가 너무 크면 자동으로 요약됨 (정상)

### Redmine issue 생성 실패

1. Redmine API Key 확인
2. 프로젝트 권한 확인
3. Tracker ID, Priority ID가 Redmine 설정과 일치하는지 확인

### 프로젝트를 찾을 수 없음

1. `python scripts/list_projects.py` 실행하여 프로젝트 목록 확인
2. `app/config.py`에서 `PROJECT_MAPPING` 확인
3. `.env`에서 `REDMINE_PROJECT_SUFFIX` 확인
4. Redmine에서 프로젝트 이름 정확히 확인
5. 대소문자, 띄어쓰기 일치 확인

### Commit이 중복 처리됨

1. `logs/processed_commits.log` 파일 확인
2. 해당 commit SHA가 이미 기록되어 있는지 확인
3. 중복 처리를 원하면 해당 줄 삭제 (주의!)

### LLM 응답이 이상함

1. `prompts/system.yaml` 및 `prompts/documentation.yaml` 검토
2. 프롬프트 수정 후 서버 재시작
3. 로그에서 LLM 응답 확인
4. Confidence가 낮으면 프롬프트 개선 필요

## 테스트 및 유틸리티

### 연결 테스트

서버 실행 전 GitLab, Redmine, OpenAI 연결을 확인:

```bash
python scripts/test_connection.py
```

**확인 사항:**
- GitLab API 연결 및 프로젝트 목록
- Redmine API 연결 및 프로젝트 목록
- OpenAI API 연결
- 진행중인 issue 조회 테스트

### 프로젝트 매핑 도구

GitLab과 Redmine 프로젝트 목록을 확인하고 자동 매핑 결과를 미리 확인:

```bash
python scripts/list_projects.py
```

**출력:**
- GitLab repository 목록
- Redmine project 목록
- 자동 매핑 제안 (REDMINE_PROJECT_SUFFIX 적용)
- 수동 매핑 필요 여부

### 수동 Webhook 테스트

실제 GitLab push 없이 webhook 테스트:

```bash
curl -X POST http://localhost:8000/webhook/gitlab \
  -H "X-Gitlab-Token: redmine-task-manager-secret-2025" \
  -H "X-Gitlab-Event: Push Hook" \
  -H "Content-Type: application/json" \
  -d @test_webhook.json
```

**참고:**
- `test_webhook.json` 파일 사용
- `test_webhook.example.json`을 복사하여 수정 가능
- 실제 commit SHA와 프로젝트 ID 사용 권장

## 설정 튜닝

### Diff 필터링

불필요한 파일 변경을 무시하려면 `app/config.py`에서 `IGNORED_PATTERNS` 수정:

```python
IGNORED_PATTERNS = [
    "package-lock.json",
    "*.min.js",
    "dist/*",
    # 추가 패턴...
]
```

### Diff 크기 제한

큰 commit의 처리 방식을 조정:

```python
MAX_DIFF_LINES = 500      # Full diff 전송 기준
MAX_SUMMARY_LINES = 2000  # Summary 전송 기준
```

### Redmine Status ID

Redmine의 status ID가 다른 경우:

```python
REDMINE_STATUS_IN_PROGRESS = 2  # 진행중 상태 ID
REDMINE_STATUS_RESOLVED = 3     # 해결 상태 ID
```

Redmine에서 확인: Administration → Issue statuses

### LLM 최적화

토큰 사용량과 비용을 줄이기 위한 설정:

```python
MAX_ISSUES_FOR_LLM = 15  # LLM에게 전달할 최대 issue 개수
```

- 진행중인 issue가 많을 때 최신 15개만 LLM에 전달
- 토큰 사용량을 크게 줄여 비용 절감
- 대부분의 경우 최신 issue들이 관련성이 높음

### 청킹 시스템

대용량 commit 처리를 위한 청킹 설정:

```python
TOKEN_BUDGET_LIMIT = 25000  # 토큰 예산 (초과 시 청킹 모드)
CHUNK_MAX_LINES = 1000      # 청크당 최대 라인 수
CHUNK_MAX_FILES = 20        # 청크당 최대 파일 개수
```

**동작 방식:**
- 토큰 수 추정 후 예산 초과 시 자동으로 청킹 모드 전환
- Diff를 청크로 분할하여 개별 분석 (GPT-4o-mini)
- 모든 청크 결과를 종합 분석 (GPT-4o)
- 대용량 commit도 안정적 처리, 비용 50-70% 절감

### 날짜 필터링

최근 issue만 검색하여 관련성 향상:

```python
REDMINE_ISSUE_SEARCH_DAYS = 7  # 최근 N일 이내 업데이트된 issue만 검색
```

**효과:**
- 오래된 issue 제외로 LLM 부하 감소
- 최근 작업 중인 issue에 집중
- 매칭 정확도 향상

## 비용 예상

**GPT-4o 가격:**
- Input: $2.50 / 1M tokens
- Output: $10 / 1M tokens

**GPT-4o-mini 가격:**
- Input: $0.15 / 1M tokens (GPT-4o의 1/17)
- Output: $0.60 / 1M tokens (GPT-4o의 1/17)

**예상 사용량:**
- 작은 commit (< 500줄): ~3,000 tokens → $0.001 (GPT-4o)
- 중간 commit (500-2000줄): ~5,000 tokens → $0.002 (GPT-4o)
- 큰 commit (> 2000줄): ~8,000 tokens → $0.003 (GPT-4o)
- 대용량 commit (청킹): ~15,000 tokens → $0.002 (GPT-4o-mini 청크 + GPT-4o 종합)

**청킹 시스템 비용 절감:**
- 청크 분석: GPT-4o-mini 사용 (비용 1/17)
- 종합 분석: GPT-4o 사용 (최종 품질 보장)
- 대용량 commit도 기존 대비 50-70% 비용 절감

**월 예상 비용 (하루 100 commits):**
- 표준 commit 90개: $0.09/일
- 대용량 commit 10개: $0.02/일
- 합계: ~$3.3/월

## 아키텍처 문서

프로젝트의 아키텍처는 `sequence.md`에 Mermaid 다이어그램으로 시각화되어 있습니다:

**포함된 다이어그램:**
1. 시퀀스 다이어그램 (전체 흐름)
2. 플로우차트 (분석 로직)
3. 컴포넌트 다이어그램 (시스템 구조)
4. 배포 다이어그램 (인프라)
5. 상태 다이어그램 (Issue 상태 변화)
6. 클래스 다이어그램 (주요 클래스)
7. 기타 아키텍처 문서

```bash
# 아키텍처 문서 확인
cat sequence.md
```

Mermaid를 지원하는 에디터(VS Code, GitHub 등)에서 다이어그램을 시각적으로 확인할 수 있습니다.

## 향후 개선 사항

- [ ] Agent 기반 분석 (자율적 정보 수집)
- [ ] Vector DB 연동 (과거 issue 검색, 유사 issue 찾기)
- [ ] 웹 대시보드 (분석 결과 시각화, 통계)
- [ ] 다중 Redmine 프로젝트 지원 강화
- [ ] Commit 분류 모델 개선 (Fine-tuning)

**참고:** 양방향 동기화(Redmine → GitLab)는 로드맵에서 제거되었습니다. 현재 단방향 동기화로 충분하다고 판단됨.

## 참고 자료

- **상세 개발 문서**: `CLAUDE.md` - AI 어시스턴트 및 개발자를 위한 상세 가이드
- **아키텍처 문서**: `sequence.md` - Mermaid 다이어그램으로 시각화된 시스템 구조
- **FastAPI**: https://fastapi.tiangolo.com/
- **LangChain**: https://python.langchain.com/
- **GitLab Webhooks**: https://docs.gitlab.com/ee/user/project/integrations/webhooks.html
- **Redmine API**: https://www.redmine.org/projects/redmine/wiki/Rest_api
- **Redmine Textile**: https://www.redmine.org/projects/redmine/wiki/RedmineTextFormatting

## 라이선스

MIT License

---

**프로젝트 철학:**

이 프로젝트는 **설정 기반**으로 동작하도록 설계되었습니다. 대부분의 커스터마이징은 코드 수정 없이 설정 변경만으로 가능합니다:

- 프롬프트: `prompts/*.yaml` 파일
- 설정: `app/config.py`, `.env` 파일
- 매핑: `PROJECT_MAPPING`, `REDMINE_PROJECT_SUFFIX`

질문이나 개선 사항이 있다면 이슈를 남겨주세요!

