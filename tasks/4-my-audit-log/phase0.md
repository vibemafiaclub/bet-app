# Phase 0: docs

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` (현재 iter 2~5까지 반영된 단일 스펙. 이번 phase에서 수정 대상 영역: "라우트 목록"(29~39행), "데이터 모델"(16~24행), "CSV Export"(74~97행), "다음 스프린트 예약 티켓"(134행 이후))
- `/docs/testing.md` ("테스트 구성" 섹션 — "6 파일" 표기가 stale, 실제로는 8 파일까지 등재됨. 이번 phase에서 "9 파일"로 수정 + 9번째 항목 추가)
- `/docs/user-intervention.md` (변경 없음 확인용 read-only)
- `/docs/mission.md` (비즈니스 맥락)
- `/iterations/6-20260424_123444/requirement.md` (요구사항 원문. 특히 "채택된 요구사항" 섹션 + "구현 스케치" 1~5 + "CTO 승인 조건부 조건" 6개)

## 작업 내용

이번 phase는 **문서 업데이트만** 수행한다. 코드(`app/`, `tests/`, `scripts/`)는 절대 건드리지 않는다.

### 1. `docs/spec.md` — "라우트 목록" 섹션에 `GET /my/audit-log` 1줄 추가

29~39행의 라우트 목록 마지막 `GET /my/export/sessions.csv` 줄 바로 아래에 다음 한 줄을 추가하라:

```
- `GET /my/audit-log` — 로그인한 트레이너 본인의 감사 로그 뷰어 (자세한 계약은 아래 `## 감사 로그 뷰어 (iter 6 live)` 참조)
```

### 2. `docs/spec.md` — "데이터 모델" 섹션에 5번째 테이블 추가

16~24행의 4개 테이블 목록 뒤에 다음을 추가하라. `- ` 들여쓰기 동일, 각 컬럼 설명 동일 포맷:

```
- `export_audit(id, created_at TEXT ISO8601 UTC, action TEXT CHECK IN ('owner_export','my_export'), actor_trainer_id INTEGER REFERENCES trainers(id) NOT NULL, target_trainer_id INTEGER REFERENCES trainers(id) NULL 허용, rows INTEGER NOT NULL)` — iter 6 신규. 관장/본인 CSV export 성공 시 1 row INSERT. `target_trainer_id IS NULL`은 관장이 `trainer_id` 쿼리 없이 전체 대상으로 뽑은 경우.
```

또한 16~24행 범위의 "4개 테이블" 문구가 있다면 **"5개 테이블"**로 수정. `init_db()` 관련 서술은 그대로 유지하되, **이번 5번째 테이블은 기존 `executescript(...)` 블록 안에 `CREATE TABLE IF NOT EXISTS`로 추가되며, `_migrate_iteration2` 같은 별도 마이그레이션 함수는 불필요**임을 1문장 이내로 명시하라.

### 3. `docs/spec.md` — "CSV Export" 섹션 양쪽 서브섹션에 `export_audit INSERT 부수효과` 1줄씩 추가

#### 3-a. 관장 export (`GET /admin/export/sessions.csv`) 서브섹션 (78~87행 부근)

`감사 로그: 매 성공 응답마다 stdout 1줄 ...` 줄 바로 아래에 다음 한 줄을 추가:

```
- `export_audit` INSERT 부수효과: 매 성공 응답마다 1 row. `(action='owner_export', actor_trainer_id=<owner_id>, target_trainer_id=<쿼리 trainer_id 값 or NULL>, rows=<data row 수>)`. stdout `[export]` 로그와 이중 기록 (관측 루트 다양성 확보).
```

#### 3-b. 본인 export (`GET /my/export/sessions.csv`) 서브섹션 (89~97행 부근)

`감사 로그: stdout 1줄 ...` 줄 바로 아래에 다음 한 줄을 추가:

```
- `export_audit` INSERT 부수효과: 매 성공 응답마다 1 row. `(action='my_export', actor_trainer_id=target_trainer_id=<session user trainer_id>, rows=<data row 수>)`. stdout `[my-export]` 로그와 이중 기록.
```

두 줄 모두 성공 200 응답 경로에서만 INSERT되며, 429 rate-limit 경로에서는 INSERT 스킵임을 **양쪽 서브섹션에 공통으로 명시**하라 (해당 rate limit bullet과 export_audit bullet을 서로 근접하게 배치).

### 4. `docs/spec.md` — 신규 `## 감사 로그 뷰어 (iter 6 live)` 섹션 추가

현재 "트레이너간 회원 접근 격리 (partial, iter 5 live)" 섹션(99~108행) **바로 아래**에 새 H2 섹션을 추가하라. 제목 및 내용:

```
## 감사 로그 뷰어 (iter 6 live)

- `GET /my/audit-log` — 로그인한 트레이너(관장 포함)가 본인이 호출한 export 및 본인에게 가해진 관장 export 이력을 능동 조회하는 페이지.
- 권한: `is_authenticated(request) == True`만. **`is_owner` 체크 없음** — 관장도 본인 자격으로 접근.
- 쿼리: `export_audit` 테이블에서 WHERE 3 OR 조건으로 본인 관련 row만 필터:
    1. `target_trainer_id = :self_tid` (본인이 target인 row)
    2. `actor_trainer_id = :self_tid` (본인이 호출자인 row)
    3. `action = 'owner_export' AND target_trainer_id IS NULL` (관장이 전체 대상으로 뽑은 row — 본인 포함으로 간주)
- 정렬·상한: `ORDER BY id DESC LIMIT :MY_AUDIT_LOG_LIMIT` (`MY_AUDIT_LOG_LIMIT = 100` 모듈 상수).
- 표시 컬럼: 일시 / 행위 / 호출자 / 대상 / rows. `action='owner_export' AND target IS NULL` → 대상 셀에 `"전체 대상(본인 포함)"` 렌더.
- **페이지네이션 / 필터 / 정렬 UI / CSV export 금지** (first 배포 scope 봉쇄). 첫 배포 이후 기능 확장 금지.
- **본인 조회 자체는 감사 대상 아님** — `/my/audit-log` GET 요청은 stdout/DB 로그를 남기지 않는다.
- 템플릿은 각 row에 **불변 토큰**(예: `<tr data-action="{{ row.action }}">`)을 행당 정확히 1회 포함해야 한다 (테스트가 `r.text.count(...)` 기반 카운트 assertion으로 row 수를 검증).
- DB 마이그레이션: `export_audit` 테이블은 `init_db()`의 `CREATE TABLE IF NOT EXISTS` 블록에 추가되어 최초 배포 시 자동 생성. ALTER TABLE·백필 스크립트 불요.
```

### 5. `docs/spec.md` — "다음 스프린트 예약 티켓" 섹션에서 N0 라인 삭제 (CTO 조건 3)

"다음 스프린트 예약 티켓" 섹션(134행 이후)의 **"트레이너 본인 감사 로그 뷰어 — `GET /my/audit-log` — ..." 한 블록 전체를 삭제**하라. 해당 블록은 현재 136행에서 시작하는 굵은 글씨 제목과 뒤따르는 설명 문단을 포함한다.

**R5-full 블록은 유지**. 기타 섹션 건드리지 마라.

### 6. `docs/testing.md` — "테스트 구성" 섹션 제목 수정 + 9번째 파일 추가

현재 10행 `## 테스트 구성 (6 파일)` 문구를 **`## 테스트 구성 (9 파일)`**로 수정하라 (실제로는 이미 8 파일 등재 상태가 유지돼왔지만, iter 5까지 "6 파일" 표기가 stale했음. 이번 iter 6에서 정합성 회복).

11~18행의 번호 리스트에 9번째 항목을 추가하라:

```
9. `tests/test_my_audit_log.py` (iteration 6 신규) — N0 감사 로그 뷰어. 8 시나리오: ① 관장 `?trainer_id=X` export → export_audit 1 row (owner_export, actor=owner, target=X, rows 정확). ② 관장 쿼리 없이 export → 1 row (target=NULL). ③ 본인 `/my/export` → 1 row (my_export, actor=target=self). ④ `/my/audit-log` WHERE 3 OR 조건 회귀 방지 (타 트레이너 only row 미노출 — CTO 조건 4). ⑤ 미로그인 → 303 /login. ⑥ 관장 self-target row + target=NULL row 둘 다 관장 `/my/audit-log`에 노출 (CTO 조건 6). ⑦ `LIMIT 100` 검증 (`MY_AUDIT_LOG_LIMIT` 상수 import 기반). ⑧ `rows` 컬럼이 `_write_sessions_csv` 반환값(header 제외 data row 수)과 일치 (CTO 조건 5).
```

### 7. `docs/user-intervention.md` — 변경 없음 (CTO 조건 3)

이번 iteration은 새 env/secret/수동 스크립트를 추가하지 않으며 DB 마이그레이션이 자동(`CREATE TABLE IF NOT EXISTS`)이다. 이 파일은 **절대 수정하지 마라**.

## Acceptance Criteria

```bash
# 1. spec.md 라우트 목록에 /my/audit-log 추가 확인
grep "/my/audit-log" docs/spec.md

# 2. spec.md 데이터 모델에 export_audit 추가 확인
grep "export_audit" docs/spec.md

# 3. spec.md 신규 감사 로그 뷰어 섹션 존재 확인
grep "## 감사 로그 뷰어 (iter 6 live)" docs/spec.md

# 4. spec.md "다음 스프린트 예약 티켓" 섹션에서 N0 블록 삭제 확인
# (N0의 제목 `**트레이너 본인 감사 로그 뷰어**`가 예약 티켓 섹션에 더 이상 없어야 함. 단 신규 감사 로그 뷰어 섹션 본문에는 "감사 로그" 문자열이 있을 수 있음 — 조합으로 판정)
! grep -n "다음 스프린트 예약 티켓" docs/spec.md | head -1 | awk -F: '{print $1}' | xargs -I{} awk "NR>={}" docs/spec.md | grep -q "트레이너 본인 감사 로그 뷰어"

# 5. testing.md에 "9 파일" 표기 + 9번째 항목 추가 확인
grep "## 테스트 구성 (9 파일)" docs/testing.md
grep "test_my_audit_log.py" docs/testing.md
test "$(grep -cE '^[0-9]+\. ' docs/testing.md)" = "9"

# 6. user-intervention.md 변경 없음 확인
test -z "$(git diff --name-only HEAD -- docs/user-intervention.md)"

# 7. 코드/테스트/스크립트 파일 변경 없음 (이번 phase docs 전용)
! git diff --name-only HEAD | grep -E '^(app|tests|scripts)/'
```

## AC 검증 방법

위 AC 커맨드를 직접 실행하라. 모두 통과하면 `/tasks/4-my-audit-log/index.json`의 phase 0 status를 `"completed"`로 변경하라.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 index.json의 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- `app/`, `tests/`, `scripts/` 디렉토리 파일은 **절대 수정 금지**. 이번 phase는 문서 전용.
- `docs/user-intervention.md`는 **절대 수정 금지** (CTO 조건 3).
- `docs/spec.md`의 "인증" 섹션(41~53행), "차트 데이터 계약" 섹션(55~72행), "배포" 섹션(124~129행) 등 다른 영역은 건드리지 마라.
- "명시적 제외 항목" 섹션(110~123행)은 건드리지 마라 — N0가 제외에서 빠진다는 암묵적 전제만으로 충분.
- AC #4의 복합 조건은 "예약 티켓 섹션 이후 본문에 옛 N0 제목 블록이 없는지"를 검증하는 의도다. 신규 H2 `## 감사 로그 뷰어 (iter 6 live)` 섹션의 **본문**은 예약 티켓 섹션 **앞**에 배치되어야 AC가 통과한다 — H2 순서를 정확히 지켜라 (신규 섹션은 99행 근처 "트레이너간 회원 접근 격리" 섹션 바로 아래, "명시적 제외 항목" 섹션 위).
- `docs-diff.md`는 만들지 마라. phase 0 완료 후 `scripts/gen-docs-diff.py`가 자동 생성한다.
- 기존 테스트를 깨뜨리지 마라 (docs만 만지므로 깨뜨릴 일 없지만 원칙 확인).
