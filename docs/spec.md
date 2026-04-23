# BET MVP Spec (iteration 1)

## 개요

PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입력하는 폼과, 회원별 운동 종목별 최대 중량 추이 및 세션당 총 볼륨 추이를 꺾은선 그래프 2개로 시각화하는 단일 뷰 MVP다. 스택은 FastAPI + SQLite + HTMX + Chart.js이며, 트레이너 전용 하드코딩 어드민 인증으로 동작한다. 파일럿 12주 동안 "수치화된 회원 발전 증거"를 트레이너가 확인하고 잠재회원 상담에 활용하는 것이 핵심 목적이다.

## 스택
- Python 3.12 / FastAPI / uvicorn
- SQLite (표준 라이브러리 sqlite3 only, ORM 없음)
- Jinja2 templates
- HTMX (세트 행 추가·폼 POST)
- Chart.js 4.x CDN (대시보드 차트)
- 테스트: pytest + httpx + playwright
- 배포: Fly.io 단일 VM + volume mount

## 데이터 모델
4개 테이블. 모든 PRIMARY KEY는 INTEGER AUTOINCREMENT.

- trainers(id, name, created_at)
- members(id, trainer_id FK, name, created_at)
- pt_sessions(id, member_id FK, session_date TEXT YYYY-MM-DD, created_at)
- session_sets(id, session_id FK, exercise TEXT CHECK in 10종, weight_kg REAL CHECK>0, reps INTEGER CHECK>0, set_index INTEGER)

## 운동 종목 (10종 고정, 확장 금지)
스쿼트, 벤치프레스, 데드리프트, 오버헤드프레스, 바벨로우, 풀업, 레그프레스, 랫풀다운, 레그컬, 덤벨컬

## 라우트 목록
- GET /login — 로그인 폼
- POST /login — credential 검증 → 303 / (성공) / 200 재렌더 (실패)
- POST /logout — 세션 clear → 303 /login
- GET / — 로그인 후 기본 (첫 멤버 로그 화면으로 redirect)
- GET /trainers/{tid}/members/{mid}/log — 입력 폼
- POST /trainers/{tid}/members/{mid}/log — 세션 + 세트 생성 (HTMX 응답)
- GET /trainers/{tid}/members/{mid}/dashboard — 차트 뷰 (Chart.js canvas 2개)
- GET /trainers/{tid}/members/{mid}/chart-data.json — 차트 데이터 JSON

## 인증
- 하드코딩 어드민 1개, 환경변수 주입: `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- `starlette.middleware.sessions.SessionMiddleware`, secret은 `APP_SESSION_SECRET`
- 비밀번호는 평문 환경변수, 비교는 `secrets.compare_digest`
- 쿠키 속성: httponly, samesite=lax. `secure`는 env toggle로 on/off.
- **부팅 시 위 3개 env 미설정 → RuntimeError로 즉시 실패 (fail-fast)**

## 차트 데이터 계약
`GET /trainers/{tid}/members/{mid}/chart-data.json` 응답:
```json
{
  "member": {"id": int, "name": str},
  "max_weight": {
    "labels": ["YYYY-MM-DD", ...],
    "datasets": [{"label": "<운동명>", "data": [<kg>, ...]}, ...]
  },
  "total_volume": {
    "labels": ["YYYY-MM-DD", ...],
    "data": [<volume>, ...]
  }
}
```
- 세션이 0건인 회원 → `labels: []`, `datasets: []`, `data: []`. 이 계약은 테스트에서 강제.
- `datasets`는 회원이 실제로 수행한 운동 종목만 포함.
- `labels`는 세션 날짜 오름차순. `max_weight.labels`와 `total_volume.labels`는 동일.

## 명시적 제외 항목 (이번 스프린트 금지)
- 자세 교정 기록 / 자가보고 / 인바디 연동
- AI 트레이너 대화
- PDF 리포트 내보내기
- Rappo 연동 / CSV import
- 회원용 UI (트레이너 전용)
- 다중 트레이너 / 다중 헬스장
- 회원 CRUD 웹 UI (seed 스크립트 only)
- 권한 분리 / 다중 유저
- **로그인 brute-force 보호 / rate limit** (명시적으로 스프린트 외)
- 11번째 이후 운동 종목
- 코드 내 "TODO: 다중 트레이너" 같은 힌트 주석도 금지

## 배포
- Fly.io 단일 VM (region `nrt`)
- Dockerfile: `python:3.12-slim` 베이스, `pip install .`
- volume mount `/data`, DB 경로는 `DATABASE_PATH` env (기본 `./data/bet.db`)
- 관측: stdout + Fly 기본 로그. Sentry/Datadog/커스텀 관측 금지.
- `fly deploy` 실제 실행은 사용자 개입 (see `docs/user-intervention.md`)

## DoD
`iterations/1-20260424_020912/artifacts/dashboard.png` — 꺾은선 그래프가 실제로 그려진 대시보드 스크린샷 (Playwright headless 자동 캡처).
