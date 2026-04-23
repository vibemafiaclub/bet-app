# Phase 5: 배포 산출물 (Dockerfile + fly.toml + .dockerignore + user-intervention 최종)

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` — 배포 섹션 (Fly.io 단일 VM, volume mount `/data`, `DATABASE_PATH`)
- `/docs/user-intervention.md` — Phase 0에서 초안 작성됨 (이 phase에서 보강)
- `/tasks/0-pt-mvp/docs-diff.md`

이전 phase 산출물 (반드시 코드를 읽고 이해하라):
- `/pyproject.toml` (Python 3.12, entry: `app.main:app`)
- `/app/main.py` (fail-fast env 검증)
- `/scripts/seed.py`
- `/iterations/1-20260424_020912/artifacts/dashboard.png` (Phase 4 산출물 — 이 phase에서는 수정하지 않는다)

## 작업 내용

### 1. `Dockerfile` (프로젝트 루트, 신규)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# OS deps (최소)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# pyproject + lock 먼저 복사 → 의존성 설치 캐시
COPY pyproject.toml ./
# uv.lock 있으면 복사 (없어도 빌드 성공해야 함)
COPY uv.loc[k] ./

RUN pip install --no-cache-dir .

# 애플리케이션 코드
COPY app ./app
COPY scripts ./scripts

# DB 디렉토리 (volume mount target — spec.md와 일치)
RUN mkdir -p /data
ENV DATABASE_PATH=/data/bet.db

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**포인트**:
- `uv` 런타임 제외. `pip install .`로 충분.
- `.dev` extras (pytest, playwright)는 이미지에 포함하지 않음.
- CMD는 `app.main:app` 진입점. `app.main`이 모듈 최상단에 `app = create_app()` 인스턴스를 노출.
- 이미지 build 시 env가 없으면 `app.main` import에서 RuntimeError. **그래서 `pip install` 이후 애플리케이션 실행은 하지 않고 그냥 이미지 완성만.** 런타임에 secret 주입.

### 2. `.dockerignore` (프로젝트 루트, 신규)

```
.git
.gitignore
.venv
.pytest_cache
__pycache__
*.pyc
data/
*.db
tests/
iterations/
persuasion-data/
.omc
.claude
docs/
tasks/
prompts/
node_modules/
README*
```

CTO 조건부 조건 #5: `.venv`, `*.db` 포함. 이미지 슬림화.

### 3. `fly.toml` (프로젝트 루트, 신규)

```toml
app = "bet-mvp"
primary_region = "nrt"

[build]

[env]
  DATABASE_PATH = "/data/bet.db"
  SESSION_COOKIE_SECURE = "1"
  PORT = "8080"

[[mounts]]
  source = "bet_data"
  destination = "/data"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

- `app` 이름은 placeholder; 사용자가 `fly launch` 시점에 바꿀 수 있다.
- `SESSION_COOKIE_SECURE=1` — Fly는 HTTPS 강제.

### 4. `docs/user-intervention.md` 보강

Phase 0에서 만든 초안에서 다음이 **모두** 포함되어 있는지 확인. 없으면 추가:
- Fly CLI 설치 안내 링크 없이 명령만: `curl -L https://fly.io/install.sh | sh` 혹은 `brew install flyctl` (상황에 맞게)
- `fly launch --no-deploy`
- `fly volumes create bet_data --region nrt --size 1`
- `fly secrets set APP_SESSION_SECRET ADMIN_USERNAME ADMIN_PASSWORD` (값 예시 포함)
- `fly deploy`
- **왜 자동화 불가한가** 섹션 (브라우저 OAuth, 결제 상태, secret 보안)

**덧붙일 섹션**: "로컬 개발 워크플로" 3줄 — 개발자가 `uv sync --extra dev && uv run playwright install chromium && APP_SESSION_SECRET=... ADMIN_USERNAME=... ADMIN_PASSWORD=... uv run uvicorn app.main:app --reload`로 돌릴 수 있게.

### 5. (선택) README 만들지 마라

이번 스프린트에서 README.md 신설 금지. 모든 설명은 `docs/` 하위에. 이것 관련 결정은 Phase 0 문서 설계 시 CTO가 확정.

## Acceptance Criteria

```bash
# Dockerfile 존재 + Docker build 성공
test -f Dockerfile
test -f .dockerignore
test -f fly.toml

# Docker 데몬 사용 가능하면 build 수행
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker build -t bet-mvp:phase5 .
else
  echo "docker unavailable — skipping build verification"
fi

# fly.toml 필수 키 확인
grep -q '^app' fly.toml
grep -q 'DATABASE_PATH' fly.toml
grep -q 'internal_port = 8080' fly.toml
grep -q 'bet_data' fly.toml

# .dockerignore 필수 항목
grep -q '^\.venv' .dockerignore
grep -q '^\*\.db' .dockerignore
grep -q '^data/' .dockerignore
grep -q '^tests/' .dockerignore
grep -q '^iterations/' .dockerignore

# user-intervention 필수 항목
grep -q 'APP_SESSION_SECRET' docs/user-intervention.md
grep -q 'ADMIN_USERNAME' docs/user-intervention.md
grep -q 'ADMIN_PASSWORD' docs/user-intervention.md
grep -q 'fly deploy' docs/user-intervention.md
grep -q 'fly volumes create' docs/user-intervention.md

# 기존 테스트 여전히 통과 (스모크)
$RUN="uv run"; command -v uv >/dev/null 2>&1 || RUN=""
$RUN pytest tests/test_aggregates.py tests/test_auth.py tests/test_log_routes.py tests/test_dashboard.py -v
```

## AC 검증 방법

위 커맨드 모두 통과하면 `/tasks/0-pt-mvp/index.json`의 phase 5 status를 `"completed"`로 변경하라.
수정 3회 이상 실패 시 status `"error"` + `"error_message"` 기록.

**docker 데몬이 사용 불가한 환경**에서는 `docker build`를 건너뛰고 `test -f Dockerfile` + grep 검증만으로 AC 충족. 실제 빌드 검증은 user-intervention 단계에서 수행.

## 주의사항

- **`fly deploy` 실행하지 마라.** 이 phase는 산출물 파일만 만든다. 실제 배포는 사용자 개입(`docs/user-intervention.md`).
- **secret 실제 값을 repo에 커밋 금지.** 환경변수 이름만 문서화.
- **Dockerfile에서 `playwright install` 하지 마라.** 런타임 이미지에 chromium 불필요.
- **uv를 런타임 이미지에 넣지 마라.** `pip install .`로 끝. uv는 로컬 개발/테스트에서만 쓴다.
- **fly.toml `app` 이름은 placeholder.** 실제 배포 시 사용자가 수정한다 (user-intervention.md에 언급).
- **README 신설 금지.** docs/* 하위에서 해결.
- **기존 Phase 1~4 테스트 여전히 green 유지.** 이 phase는 코드 수정이 거의 없어야 정상.
- 운영 관측 도구(Sentry/Datadog) 도입 금지. stdout + Fly 기본 로그에서 멈춘다 (조건부 조건 #4).
