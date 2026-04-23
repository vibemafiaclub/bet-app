# User Intervention Points

이 프로젝트는 CLI/자동화로 가능한 모든 것을 헤드리스 세션으로 처리한다. 이 문서는 자동화로 뚫을 수 없어 **사람 손이 필요한 지점**만 모은다.

## Fly.io 배포 (iteration 1)

### Fly CLI 설치
```bash
# macOS
brew install flyctl

# Linux / WSL
curl -L https://fly.io/install.sh | sh
```

### 필요 환경변수 (secrets)
배포 전 아래 3개 secret을 Fly.io에 주입해야 한다:
- `APP_SESSION_SECRET` — 세션 쿠키 서명용 (임의 64바이트 문자열 권장)
- `ADMIN_USERNAME` — 어드민 로그인 ID
- `ADMIN_PASSWORD` — 어드민 로그인 비밀번호 (평문, 헬스장 관장이 기억할 수 있는 값)

### 최초 배포 명령
```bash
fly launch --no-deploy                              # fly.toml 기반 앱 생성, 즉시 배포 안 함
fly volumes create bet_data --region nrt --size 1   # SQLite 영속화용 1GB 볼륨 (fly.toml이 mount)
fly secrets set APP_SESSION_SECRET="$(openssl rand -hex 32)" \
                ADMIN_USERNAME="trainer" \
                ADMIN_PASSWORD="<헬스장 관장이 기억할 비밀번호>"
fly deploy                                          # 실제 배포
```

### 재배포 (코드 변경 후)
```bash
fly deploy
```
secret 변경이 필요하면 `fly secrets set ...` 후 자동 재시작.

### 왜 헤드리스 자동화 불가?
- `fly auth` 가 OAuth 브라우저 플로우를 요구
- volume 프로비저닝은 계정 결제 상태 확인 후 승인
- secret 값은 로컬 repo에 남지 않아야 함

## 로컬 개발 워크플로

```bash
uv sync --extra dev && uv run playwright install chromium
APP_SESSION_SECRET=dev-secret-change-me ADMIN_USERNAME=admin ADMIN_PASSWORD=password uv run uvicorn app.main:app --reload
```

브라우저에서 `http://localhost:8000` 접속 후 위에서 설정한 `ADMIN_USERNAME` / `ADMIN_PASSWORD`로 로그인.
