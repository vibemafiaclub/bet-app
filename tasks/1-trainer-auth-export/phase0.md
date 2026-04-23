# Phase 0: 문서 개정 (spec / testing / user-intervention)

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/mission.md` — 프로젝트 mission (수정 금지)
- `/docs/spec.md` — iteration 1 spec (이번 phase에서 개정 대상)
- `/docs/testing.md` — 테스트 정책 (이번 phase에서 개정 대상)
- `/docs/user-intervention.md` — 운영 개입 지점 (이번 phase에서 개정 대상)
- `/iterations/2-20260424_034244/requirement.md` — 이번 iteration 요구사항 (가치제안 + 채택된 스펙 + CTO 조건부 조건)

이 phase는 **코드 이전 문서 단계**다. 코드 변경을 일체 하지 마라. 오직 `/docs/` 하위 3개 파일만 수정한다.

## 작업 내용

### 1. `/docs/spec.md` 개정

다음 변경을 적용하라. 전체 파일 재작성보다는 해당 섹션만 정확히 수정하라.

#### 1-a. 제목과 개요 갱신

맨 위 제목을 `# BET Spec (iteration 2)`로 바꾸고, 개요 끝에 1-2문장을 덧붙여라:

> iteration 2부터는 단일 헬스장 내 다중 트레이너 로그인 계정과 세션 기록의 "입력자 트레이너" 귀속, 관장(is_owner) 전용 CSV 내보내기를 지원한다. 다중 헬스장과 복잡 RBAC는 여전히 범위 외.

#### 1-b. `## 데이터 모델` 섹션 수정

4개 테이블 유지. 아래와 같이 컬럼을 추가/수정하라 (텍스트 표현만 바꾸면 됨):

- `trainers(id, name, created_at, username TEXT UNIQUE, password_hash TEXT, is_owner INTEGER NOT NULL DEFAULT 0)`
- `pt_sessions(id, member_id FK, session_date TEXT YYYY-MM-DD, created_at, input_trainer_id INTEGER REFERENCES trainers(id) NULL 허용)`

스키마는 `init_db()`가 idempotent ALTER TABLE (PRAGMA table_info 체크 후 ADD)로 적용한다는 1줄도 추가.

#### 1-c. `## 인증` 섹션 전면 교체

기존 "하드코딩 어드민 1개" 설명을 아래로 대체하라:

- 인증 주체는 `trainers` 테이블. 로그인 식별자는 `username`, 비밀번호는 `password_hash` (`hashlib.scrypt`, n=16384, r=8, p=1, salt 16B, dklen=64, 포맷 `scrypt$<salt_hex>$<hash_hex>`).
- `passlib` / `bcrypt` / 기타 외부 해싱 의존 추가 금지 — 표준 라이브러리 `hashlib`만 사용.
- 세션 쿠키: `request.session["user"] = {"trainer_id": int, "is_owner": bool}`. 기존 `["admin"] = True` 구조는 제거.
- `starlette.middleware.sessions.SessionMiddleware`, secret은 `APP_SESSION_SECRET`. 쿠키 속성 httponly, samesite=lax, `SESSION_COOKIE_SECURE` env toggle 유지.
- **관장 부트 시드 (ensure_owner_seed)**: `create_app()` 부트 시 실행.
  - is_owner=1 row가 0건 & username==ADMIN_USERNAME row 없음 → 신규 INSERT (name=ADMIN_USERNAME, username=ADMIN_USERNAME, password_hash=hash(ADMIN_PASSWORD), is_owner=1)
  - is_owner=1 row가 0건 & username==ADMIN_USERNAME row 있음 → UPDATE is_owner=1 (password_hash는 NULL일 때만 채움)
  - is_owner=1 row ≥1건 & 그 row의 username == ADMIN_USERNAME → no-op (password_hash 불변)
  - is_owner=1 row ≥1건 & username != ADMIN_USERNAME → stdout에 `[warn] ADMIN_USERNAME mismatch: env=X db_owner=Y (관장 교체 절차 필요)` 1줄 출력 + skip. **부팅은 계속 진행 (exit 0 유지)**.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `APP_SESSION_SECRET` 3개 env는 여전히 필수 (부트 시드용). 미설정 시 RuntimeError fail-fast.
- 계정 CRUD는 웹 UI 없음. `scripts/seed_trainer.py`만 사용.

#### 1-d. `## 라우트 목록` 섹션에 1줄 추가

기존 8개 라우트 아래에 추가:
- `GET /admin/export/sessions.csv?trainer_id=<int>` — 관장 전용 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)

#### 1-e. 신규 섹션 `## CSV Export` 추가 (`## 차트 데이터 계약` 뒤)

- 권한: `session["user"]["is_owner"] == True`만. 아니면 303 → `/`.
- 쿼리: `trainer_id` (optional). 있으면 `pt_sessions.input_trainer_id = trainer_id` 필터. 없으면 전체.
- 응답: `text/csv; charset=utf-8`. 본문 **UTF-8 BOM (`﻿`) 접두** 1회 (Excel 기본 열기 한글 깨짐 방지).
- 컬럼 순서 고정: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`
- `input_trainer_name`은 `LEFT JOIN trainers ON pt_sessions.input_trainer_id = trainers.id` 후 `COALESCE(trainers.name, '')`.
- 파일명 헤더: `Content-Disposition: attachment; filename=sessions_YYYYMMDD.csv` (trainer_id 쿼리 시 `sessions_YYYYMMDD_trainer_<tid>.csv`).
- Rate limit: 모듈 전역 `dict[int, float]` (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429. **테스트 간 state 누수 방지를 위해 전역 dict는 `app.state`에 붙이거나 앱 팩토리 closure로 은닉**.
- 감사 로그: 매 성공 응답마다 stdout 1줄 `[export] owner_id={X} target_trainer_id={Y|all} rows={N}`.

#### 1-f. 신규 섹션 `## 트레이너간 회원 접근 격리` 추가

- 이번 스프린트는 **permissive**. 트레이너A가 트레이너B 담당 회원의 `/trainers/{tid}/members/{mid}/...` URL을 직접 입력하면 접근 가능.
- 단 URL의 `tid`와 `mid`는 `members WHERE id=mid AND trainer_id=tid` 필터로 검증 유지 → 잘못된 조합은 404.
- 트레이너간 완전 격리는 **R5 (회원용 자가 대시보드 + 트레이너 IP 가드레일)**에서 다룸. 이번 스프린트 범위 외.

#### 1-g. `## 명시적 제외 항목` 섹션 수정

**삭제**할 항목:
- "다중 트레이너 / 다중 헬스장"
- "권한 분리 / 다중 유저"

**수정**할 항목:
- 기존 "**로그인 brute-force 보호 / rate limit** (명시적으로 스프린트 외)" → "**로그인 brute-force 보호 / 로그인 rate limit** (스프린트 외). 단 `/admin/export/sessions.csv`는 IP 자산 유출 경로이므로 owner_trainer_id별 60초 in-memory rate limit만 최소 감사 흔적으로 허용."

**추가**할 항목:
- "다중 헬스장 (여전히 금지)"
- "복잡 RBAC / 트레이너 간 회원 접근 격리 (R5에서 다룸)"
- "계정 CRUD 웹 UI (`scripts/seed_trainer.py` only)"

#### 1-h. 신규 섹션 `## 다음 스프린트 예약 티켓` 추가 (최하단)

> **트레이너 본인의 "내 입력분 CSV export" 라우트** — `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 `input_trainer_id`만 필터링하여 다운로드. 관장 허가 불요. 이 기능이 붙어야 개선점 4("트레이너·헬스장 공동 소유, 퇴사 시 트레이너 본인이 export 가능")의 해소가 완성된다. iteration 2 백필 스크립트 실행이 이 기능의 전제.

#### 1-i. `## DoD` 섹션은 그대로 유지

iteration 1의 DoD(dashboard.png)는 이미 달성됨. 이번 iteration은 별도 DoD 추가하지 않음 (요구사항 문서에 명시 없음).

### 2. `/docs/testing.md` 개정

#### 2-a. 테스트 구성 섹션 확장

기존 5파일 유지 + 6번째 신규 + 기존 2개 확장 설명 추가:

2. `tests/test_auth.py` — 로그인 / 세션 / 로그아웃 라우트. **iteration 2 확장**: 관장 부트 시드(신규 INSERT / 기존 password_hash 불변 / username mismatch 시 warn+skip), non-owner 트레이너 로그인, `session["user"]` 스키마 검증.
3. `tests/test_log_routes.py` — 로그 폼 GET / POST, 빈 세트 스킵, 검증 실패 처리. **iteration 2 확장**: POST /log가 세션의 `trainer_id`를 `pt_sessions.input_trainer_id`에 기록.

6. `tests/test_export.py` (iteration 2 신규) — `/admin/export/sessions.csv` 권한 분기(owner only), `trainer_id` 쿼리 필터, 60초 rate limit, stdout 감사 로그 포맷, NULL `input_trainer_id` row의 빈 이름 렌더, UTF-8 BOM 본문 접두.

#### 2-b. "원칙" 섹션에 1줄 추가

> `pytest.monkeypatch`를 통한 env / 모듈 attribute / 모듈 전역 dict 조작은 mock 금지 원칙에 저촉되지 않음 (conftest가 이미 이 방식으로 DB 경로와 env를 주입한다). 단 DB 자체를 mock하거나 `time.monotonic` 자체를 패치하는 것은 금지.

### 3. `/docs/user-intervention.md` 개정

#### 3-a. 신규 섹션 `## iteration 2 트레이너 계정 운영` 추가

아래 내용을 포함하라:

```markdown
## iteration 2 트레이너 계정 운영

### 배포 후 관장 1회 재로그인 필요
iteration 2 배포 직후, 기존에 로그인된 관장 세션 쿠키는 구조(`admin=True`)가 달라져 자동으로 로그아웃된다. 배포 완료 후 관장이 직접 로그인 폼에서 재로그인해야 한다.

### 트레이너 계정 생성 / 비밀번호 리셋
`fly ssh console` 후:
\`\`\`bash
 uv run python -m scripts.seed_trainer --name "트레이너 이름" --username trainer_u --password "pw"
\`\`\`
- 같은 `--username`으로 재실행하면 비밀번호 리셋 (upsert).
- `--owner` 플래그를 주면 해당 계정을 is_owner=1로 승격 (다른 계정의 is_owner는 0으로 전환되며 stdout에 목록 출력).
- **shell history 회피**: 명령 앞에 공백 prefix를 붙이거나 실행 후 `history -c` (HISTCONTROL=ignorespace 가정).

### 관장 교체
`fly ssh console` 후:
\`\`\`bash
sqlite3 /data/bet.db "UPDATE trainers SET is_owner=0; UPDATE trainers SET is_owner=1 WHERE username='<새관장_username>';"
\`\`\`
그 후 `fly secrets set ADMIN_USERNAME='<새관장_username>' ADMIN_PASSWORD='<새비번 또는 기존비번>'` 로 env도 갱신. env를 갱신하지 않으면 부팅 시 `[warn] ADMIN_USERNAME mismatch` 경고가 stdout에 뜨지만 앱은 계속 기동한다.

### 백필 스크립트 실행 (iteration 2 배포 후 필수 1회)
`fly ssh console` 후 **반드시** 1회 실행:
\`\`\`bash
uv run python -m scripts.backfill_input_trainer
\`\`\`
- iteration 1 시절 누적된 `pt_sessions.input_trainer_id IS NULL` row를 관장의 trainer_id로 UPDATE.
- 멱등: 2회 실행해도 0건 UPDATE.
- 관장 계정이 DB에 없으면 (env 미설정 또는 seed 미완료) exit 1 + stderr 안내. 이 경우 먼저 `seed_trainer --owner`로 관장 생성 후 재실행.
- 이 백필이 다음 스프린트 "트레이너 본인의 CSV export 라우트"의 전제다. 백필 없이 배포되면 NULL rows가 계속 쌓여 후속 스프린트가 깨진다.
- 배포 순서: **(1) Phase 1~2 코드 배포 → (2) 이 백필 1회 실행 → (3) 운영 재개**.
```

#### 3-b. 기존 "## 작업하지 말 것" 등 다른 섹션은 건드리지 않음

## Acceptance Criteria

아래 커맨드를 순서대로 실행해서 전부 exit 0이어야 한다.

```bash
test -f docs/spec.md
test -f docs/testing.md
test -f docs/user-intervention.md

# spec.md 핵심 키워드
grep -q 'iteration 2' docs/spec.md
grep -q 'is_owner' docs/spec.md
grep -q 'input_trainer_id' docs/spec.md
grep -q 'hashlib.scrypt' docs/spec.md
grep -q 'ensure_owner_seed' docs/spec.md
grep -q 'ADMIN_USERNAME mismatch' docs/spec.md
grep -q '/admin/export/sessions.csv' docs/spec.md
grep -q 'UTF-8 BOM' docs/spec.md
grep -q '다음 스프린트 예약 티켓' docs/spec.md
grep -q '/my/export/sessions.csv' docs/spec.md
grep -q '트레이너간 회원 접근 격리' docs/spec.md
# 자기모순 방지: CSV export rate limit만 허용
grep -q 'owner_trainer_id별 60초' docs/spec.md

# testing.md
grep -q 'test_export.py' docs/testing.md
grep -q 'monkeypatch' docs/testing.md

# user-intervention.md 핵심 4개 키워드
grep -q 'backfill_input_trainer' docs/user-intervention.md
grep -q '재로그인' docs/user-intervention.md
grep -q 'history' docs/user-intervention.md
grep -q "UPDATE trainers SET is_owner" docs/user-intervention.md
```

## AC 검증 방법

위 AC 커맨드들을 순서대로 실행하라. 전부 exit 0이면 `/tasks/1-trainer-auth-export/index.json`의 phase 0 status를 `"completed"`로 변경하라.

실패 시 문서 내용을 수정한 뒤 재시도. 수정 3회 이상 실패 시 status를 `"error"`로 변경하고 `"error_message"` 필드에 원인을 기록하라.

## 주의사항

- **`/docs/mission.md`는 절대 수정하지 마라** (파일 최상단에 "이 문서는 사용자가 직접 관리합니다" 명시).
- 이 phase는 **문서만 만든다.** 어떤 `.py` 파일도 건드리지 마라. `app/`, `scripts/`, `tests/`, `pyproject.toml`, `fly.toml` 모두 변경 금지.
- spec.md 개정은 **선(先) 개정** 원칙이다. 나중 phase들이 이 spec을 근거로 구현하므로, spec 본문과 코드 시그니처가 다르면 드리프트가 된다.
- spec.md "명시적 제외 항목"에서 "다중 트레이너 / 다중 헬스장" 조항을 **반드시 삭제**하라 — iteration 2가 이 조항을 깨기 때문. 대신 "다중 헬스장 (여전히 금지)"를 추가.
- CSV export rate limit과 "로그인 rate limit 스프린트 외" 조항의 **자기모순**을 없애야 한다 — CSV에 한해서만 허용임을 1문장으로 명시.
- spec.md의 `## 다음 스프린트 예약 티켓` 섹션은 **CTO 조건부 조건 6번**의 이행이므로 반드시 포함.
- 기존 테스트를 깨뜨리지 마라 (문서만 건드리므로 테스트 깨질 일 없음).
