# Phase 0: 문서 개정 (spec / testing)

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/mission.md` — 프로젝트 mission (수정 금지)
- `/docs/spec.md` — iteration 2 spec. 제목은 "iteration 2" 그대로 유지. 이번 phase에서 `## 라우트 목록`, `## CSV Export`, `## 다음 스프린트 예약 티켓` 3개 섹션을 수정한다.
- `/docs/testing.md` — 테스트 정책. 이번 phase에서 `## 테스트 구성` 섹션에 7번째 파일을 추가한다.
- `/docs/user-intervention.md` — **변경 없음.** 이 phase에서 손대지 마라.
- `/iterations/3-20260424_075811/requirement.md` — 이번 iteration 요구사항 (R0 + CTO 조건부 조건 4개)

이 phase는 **코드 이전 문서 단계**다. 코드 변경을 일체 하지 마라. 오직 `/docs/spec.md`와 `/docs/testing.md` 2개 파일만 수정한다. `docs/mission.md`, `docs/user-intervention.md`, `app/`, `tests/`, `scripts/`, `pyproject.toml`, `fly.toml` 등 어떤 파일도 건드리지 마라.

## 작업 내용

### 1. `/docs/spec.md` 개정

#### 1-a. 제목 유지

맨 윗줄 `# BET Spec (iteration 2)`는 **그대로 유지**한다. iteration 3으로 bump하지 마라.

이유: iteration 2 spec이 라이브 상태를 기술하고 있고 R0는 iteration 2 spec에 이미 "다음 스프린트 예약 티켓"으로 명시돼 있던 기능의 이행이다. 제목은 유지하되 CSV Export 섹션 본문에 "iteration 3 추가: 트레이너 본인 export" 각주 1줄을 삽입해 변경 이력을 남긴다.

#### 1-b. `## 라우트 목록` 섹션에 1줄 추가

기존 마지막 줄 `- GET /admin/export/sessions.csv?trainer_id=<int>` 아래에 1줄 추가:

```
- `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 입력분 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
```

#### 1-c. `## CSV Export` 섹션 확장

기존 `## CSV Export` 섹션 본문을 유지하되, 아래 구조로 재편성하라.

**(1)** 섹션 맨 앞에 **iteration 3 각주** 1줄을 추가한다:

```
> iteration 3에서 `/my/export/sessions.csv`가 추가됐다. 관장 전용 `/admin/export/sessions.csv`와 공통 헬퍼 `_write_sessions_csv`를 공유하여 컬럼 drift를 코드 레벨에서 방지한다.
```

**(2)** 그 아래에 기존 관장 export 계약을 **### 관장 export (`GET /admin/export/sessions.csv`)** 하위 섹션으로 감싸라. 본문 내용 자체는 그대로 유지 (권한 is_owner / 쿼리 trainer_id / UTF-8 BOM / 컬럼 순서 / 파일명 `sessions_YYYYMMDD.csv` / rate limit dict `app.state.export_last_ts` / 감사 로그 `[export] owner_id=X target_trainer_id=Y|all rows=N`).

**(3)** 관장 export 하위 섹션 뒤에 **### 트레이너 본인 export (`GET /my/export/sessions.csv`)** 하위 섹션을 신규 추가하라. 본문은 다음 계약을 정확히 명시:

- 권한: `is_authenticated(request) == True` 만. is_owner 체크 없음. 관장도 본인 자격으로 호출 가능 (단, 관장 본인의 `trainer_id` row만 반환되며 is_owner bypass 없음).
- 쿼리 파라미터: 없음. `pt_sessions.input_trainer_id = session["user"]["trainer_id"]`로 고정 필터링.
- 응답: `text/csv; charset=utf-8`, 본문 **UTF-8 BOM** 접두 1회. 관장 export와 **컬럼 순서 bit-exact 동일** (`session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`).
- 파일명 헤더: `Content-Disposition: attachment; filename="my_sessions_YYYYMMDD.csv"`. trainer_id 접미사 없음 (본인 것이므로 URL로 암시됨).
- Rate limit: 별도 `app.state.my_export_last_ts` dict. 관장 `app.state.export_last_ts`와 **물리 분리**되어 상호 영향 없음. 60초 이내 재요청 시 429.
- 감사 로그: stdout 1줄 `[my-export] trainer_id={X} rows={N}`. 관장 export 로그(`[export] ...`)와 prefix로 구분.
- 공통 헬퍼: 양 라우트는 `app/routes.py` 내부 private 함수 `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int`를 공유한다. 컬럼명은 단일 상수 tuple `_SESSIONS_CSV_COLUMNS`로 정의되며 header/data writerow가 모두 이를 참조해 컬럼 drift를 코드 레벨에서 차단한다.

#### 1-d. `## 다음 스프린트 예약 티켓` 섹션 교체

**기존 본문 전체를 삭제**하고 아래 내용으로 교체하라:

```
**트레이너 본인 감사 로그 뷰어** — `GET /my/audit-log` — 트레이너가 "누가 언제 내 입력분을 export 했는가"를 능동 조회하는 페이지. 현재 `[export]` / `[my-export]` stdout 감사 흔적은 트레이너가 직접 볼 수 없으므로, DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다. 시뮬 5/6 언급 2순위 우려(트레이너가 "감시 메커니즘이 live, 방어장치는 roadmap"이라고 판단하는 비대칭성 해소)에 대응.
```

이유: 기존 예약 티켓(`GET /my/export/sessions.csv`)은 iteration 3에서 이행되므로 더 이상 "예약"이 아니다. 대신 다음 우선순위 우려(감사 로그 투명화)를 다음 스프린트 후보로 남긴다 (CTO 조건 4).

#### 1-e. 기타 섹션은 건드리지 마라

- `## 개요`, `## 스택`, `## 데이터 모델`, `## 운동 종목`, `## 인증`, `## 차트 데이터 계약`, `## 트레이너간 회원 접근 격리`, `## 명시적 제외 항목`, `## 배포`, `## DoD` — 전부 수정 금지.

### 2. `/docs/testing.md` 개정

#### 2-a. `## 테스트 구성` 섹션에 7번째 파일 추가

기존 6개 파일 목록 끝에 이어서 7번째 항목을 추가하라:

```
7. `tests/test_my_export.py` (iteration 3 신규) — `/my/export/sessions.csv` 권한 분기(is_authenticated만 필요, is_owner bypass 없음), 본인 `input_trainer_id` 필터, 관장 로그인 시에도 본인 row만 반환, 60초 rate limit (관장 export와 dict 물리 분리), stdout 감사 로그 포맷 `[my-export] trainer_id=X rows=N`, UTF-8 BOM 본문 접두, `filename="my_sessions_YYYYMMDD.csv"` 헤더, **컬럼 동등성 회귀 테스트**(관장 `/admin/export?trainer_id=X` body와 X 로그인 `/my/export` body가 bit-exact 일치).
```

#### 2-b. 기타 섹션은 건드리지 마라

- `## 원칙`, `## 프레임워크`, `## 산출물` — 전부 수정 금지.

### 3. `/docs/user-intervention.md`

**변경 없음.** 이 phase에서 손대지 마라. env/secret/수동 스크립트 추가 없음. iteration 2 백필은 이미 완료 상태.

## Acceptance Criteria

아래 커맨드를 순서대로 실행해서 전부 exit 0이어야 한다.

```bash
test -f docs/spec.md
test -f docs/testing.md
test -f docs/user-intervention.md

# spec.md 제목 유지 확인
grep -q '^# BET Spec (iteration 2)' docs/spec.md

# spec.md 라우트 목록에 /my/export 추가
grep -q '/my/export/sessions.csv' docs/spec.md

# spec.md CSV Export 섹션 확장
grep -q '### 관장 export' docs/spec.md
grep -q '### 트레이너 본인 export' docs/spec.md
grep -q 'iteration 3에서' docs/spec.md
grep -q '_write_sessions_csv' docs/spec.md
grep -q 'my_export_last_ts' docs/spec.md
grep -q 'my_sessions_' docs/spec.md
grep -q '\[my-export\]' docs/spec.md

# 예약 티켓 교체 확인
grep -q '/my/audit-log' docs/spec.md
grep -q 'export_audit' docs/spec.md

# testing.md 확장 확인
grep -q 'test_my_export.py' docs/testing.md
grep -q 'my-export' docs/testing.md
grep -q '컬럼 동등성' docs/testing.md

# user-intervention.md 변경 금지 확인 — 파일 존재만 확인 (내용은 이전 phase에서 확정됨)
test -s docs/user-intervention.md
```

## AC 검증 방법

위 AC 커맨드를 순서대로 실행하라. 전부 exit 0이면 `/tasks/2-my-export/index.json`의 phase 0 status를 `"completed"`로 변경하라.

수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고 `"error_message"` 필드에 원인을 기록하라.

## 주의사항

- **`/docs/mission.md`는 절대 수정하지 마라** (파일 최상단에 "이 문서는 사용자가 직접 관리합니다" 명시).
- **`/docs/user-intervention.md`도 수정하지 마라.** 이번 iteration은 사용자 개입 지점 변경 없음.
- 이 phase는 **문서만 만든다.** 어떤 `.py` 파일도 건드리지 마라.
- spec.md 제목 bump 금지 — "iteration 2" 그대로 유지. CSV Export 섹션 내부 각주만 "iteration 3 추가".
- 기존 `## 다음 스프린트 예약 티켓` 본문(`트레이너 본인의 "내 입력분 CSV export" 라우트`)은 **완전히 제거**하라 — 이걸 그대로 두면 CTO 조건 4 위반.
- 기존 테스트를 깨뜨리지 마라 (문서만 건드리므로 테스트 깨질 일 없음).
