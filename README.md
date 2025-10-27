# Redmine Task Manager

GitLab과 Redmine을 연동하여 commit 정보를 기반으로 자동으로 task를 생성/업데이트하는 LLM 기반 서비스입니다.

## 주요 기능

- **자동 Task 관리**: GitLab commit을 분석하여 Redmine issue 자동 생성/업데이트
- **LLM 기반 분석**: GPT-4o를 사용하여 commit의 의도와 내용을 이해
- **스마트 매칭**: 진행중인 issue와 자동 매칭
- **명시적 참조 지원**: Commit message에 `#123` 형태로 issue를 직접 지정 가능

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

### 5. 프로젝트 매핑 (선택)

GitLab repository 이름과 Redmine project 이름이 다른 경우, `app/config.py`에서 매핑 설정:

```python
PROJECT_MAPPING = {
    "WiseIDS-Frontend": "WiseIDS",
    "WiseIDS-Backend": "WiseIDS",
    "mobile-app": "Mobile App",
}
```

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

### 자동 분석

일반적인 commit을 push하면 자동으로 분석:

```bash
git commit -m "fix: 이벤트 로그 검색 오류 수정"
git push
```

→ LLM이 진행중인 issue 중 관련된 것을 찾아 업데이트하거나 새로 생성

### 명시적 issue 참조

Commit message에 issue 번호를 명시:

```bash
git commit -m "#668 이벤트 로그 IP 검색 오류 수정"
git push
```

→ Redmine issue #668을 직접 업데이트 (LLM 분석 없이 빠르게 처리)

지원하는 패턴:
- `#123`
- `refs #123`
- `fix #123`
- `close #123`
- `resolve #123`

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

- `app-YYYY-MM-DD.log`: 애플리케이션 로그
- `sync-YYYY-MM-DD.log`: Sync 이벤트 로그 (JSON 형식)

## 프롬프트 커스터마이징

프롬프트는 `prompts/` 디렉토리의 YAML 파일로 관리:

- `system.yaml`: LLM 시스템 프롬프트 (역할, 규칙)
- `analysis.yaml`: 분석 요청 템플릿
- `helpers.yaml`: 포맷팅 헬퍼

프롬프트 수정 후 서버 재시작 필요.

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

1. `app/config.py`에서 `PROJECT_MAPPING` 확인
2. Redmine에서 프로젝트 이름 정확히 확인
3. 대소문자, 띄어쓰기 일치 확인

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

## 비용 예상

**GPT-4o 가격:**
- Input: $2.50 / 1M tokens
- Output: $10 / 1M tokens

**예상 사용량:**
- 작은 commit (< 500줄): ~3000 tokens → $0.001
- 중간 commit (500-2000줄): ~5000 tokens → $0.002
- 큰 commit (> 2000줄): ~8000 tokens → $0.003

**월 예상 비용 (하루 100 commits):**
- $0.10/일 × 30일 = $3/월

## 향후 개선 사항

- [ ] Agent 기반 분석 (자율적 정보 수집)
- [ ] Vector DB 연동 (과거 issue 검색)
- [ ] 웹 대시보드 (분석 결과 시각화)
- [ ] 양방향 동기화 (Redmine → GitLab)
- [ ] 다중 Redmine 프로젝트 지원 강화

## 라이선스

MIT License

