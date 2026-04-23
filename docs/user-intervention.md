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

## iteration 2 트레이너 계정 운영

### 배포 후 관장 1회 재로그인 필요
iteration 2 배포 직후, 기존에 로그인된 관장 세션 쿠키는 구조(`admin=True`)가 달라져 자동으로 로그아웃된다. 배포 완료 후 관장이 직접 로그인 폼에서 재로그인해야 한다.

### 트레이너 계정 생성 / 비밀번호 리셋
`fly ssh console` 후:
```bash
 uv run python -m scripts.seed_trainer --name "트레이너 이름" --username trainer_u --password "pw"
```
- 같은 `--username`으로 재실행하면 비밀번호 리셋 (upsert).
- `--owner` 플래그를 주면 해당 계정을 is_owner=1로 승격 (다른 계정의 is_owner는 0으로 전환되며 stdout에 목록 출력).
- **shell history 회피**: 명령 앞에 공백 prefix를 붙이거나 실행 후 `history -c` (HISTCONTROL=ignorespace 가정).

### 관장 교체
`fly ssh console` 후:
```bash
sqlite3 /data/bet.db "UPDATE trainers SET is_owner=0; UPDATE trainers SET is_owner=1 WHERE username='<새관장_username>';"
```
그 후 `fly secrets set ADMIN_USERNAME='<새관장_username>' ADMIN_PASSWORD='<새비번 또는 기존비번>'` 로 env도 갱신. env를 갱신하지 않으면 부팅 시 `[warn] ADMIN_USERNAME mismatch` 경고가 stdout에 뜨지만 앱은 계속 기동한다.

### 백필 스크립트 실행 (iteration 2 배포 후 필수 1회)
`fly ssh console` 후 **반드시** 1회 실행:
```bash
uv run python -m scripts.backfill_input_trainer
```
- iteration 1 시절 누적된 `pt_sessions.input_trainer_id IS NULL` row를 관장의 trainer_id로 UPDATE.
- 멱등: 2회 실행해도 0건 UPDATE.
- 관장 계정이 DB에 없으면 (env 미설정 또는 seed 미완료) exit 1 + stderr 안내. 이 경우 먼저 `seed_trainer --owner`로 관장 생성 후 재실행.
- 이 백필이 다음 스프린트 "트레이너 본인의 CSV export 라우트"의 전제다. 백필 없이 배포되면 NULL rows가 계속 쌓여 후속 스프린트가 깨진다.
- 배포 순서: **(1) Phase 1~2 코드 배포 → (2) 이 백필 1회 실행 → (3) 운영 재개**.
