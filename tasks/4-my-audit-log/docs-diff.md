# docs-diff: my-audit-log

Baseline: `91769a2`

## `docs/spec.md`

```diff
diff --git a/docs/spec.md b/docs/spec.md
index 4193191..e820405 100644
--- a/docs/spec.md
+++ b/docs/spec.md
@@ -14,14 +14,15 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - 배포: Fly.io 단일 VM + volume mount
 
 ## 데이터 모델
-4개 테이블. 모든 PRIMARY KEY는 INTEGER AUTOINCREMENT.
+5개 테이블. 모든 PRIMARY KEY는 INTEGER AUTOINCREMENT.
 
 - `trainers(id, name, created_at, username TEXT UNIQUE, password_hash TEXT, is_owner INTEGER NOT NULL DEFAULT 0)`
 - `members(id, trainer_id FK, name, created_at)`
 - `pt_sessions(id, member_id FK, session_date TEXT YYYY-MM-DD, created_at, input_trainer_id INTEGER REFERENCES trainers(id) NULL 허용)`
 - `session_sets(id, session_id FK, exercise TEXT CHECK in 10종, weight_kg REAL CHECK>0, reps INTEGER CHECK>0, set_index INTEGER)`
+- `export_audit(id, created_at TEXT ISO8601 UTC, action TEXT CHECK IN ('owner_export','my_export'), actor_trainer_id INTEGER REFERENCES trainers(id) NOT NULL, target_trainer_id INTEGER REFERENCES trainers(id) NULL 허용, rows INTEGER NOT NULL)` — iter 6 신규. 관장/본인 CSV export 성공 시 1 row INSERT. `target_trainer_id IS NULL`은 관장이 `trainer_id` 쿼리 없이 전체 대상으로 뽑은 경우.
 
-스키마는 `init_db()`가 idempotent ALTER TABLE (PRAGMA table_info 체크 후 ADD)로 적용한다.
+스키마는 `init_db()`가 idempotent ALTER TABLE (PRAGMA table_info 체크 후 ADD)로 적용한다. 5번째 테이블 `export_audit`은 기존 `executescript(...)` 블록 안에 `CREATE TABLE IF NOT EXISTS`로 추가되며, `_migrate_iteration2` 같은 별도 마이그레이션 함수는 불필요하다.
 
 ## 운동 종목 (10종 고정, 확장 금지)
 스쿼트, 벤치프레스, 데드리프트, 오버헤드프레스, 바벨로우, 풀업, 레그프레스, 랫풀다운, 레그컬, 덤벨컬
@@ -37,6 +38,7 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - GET /trainers/{tid}/members/{mid}/chart-data.json — 차트 데이터 JSON
 - `GET /admin/export/sessions.csv?trainer_id=<int>` — 관장 전용 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
 - `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 입력분 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
+- `GET /my/audit-log` — 로그인한 트레이너 본인의 감사 로그 뷰어 (자세한 계약은 아래 `## 감사 로그 뷰어 (iter 6 live)` 참조)
 
 ## 인증
 
@@ -83,8 +85,9 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - 컬럼 순서 고정: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`
 - `input_trainer_name`은 `LEFT JOIN trainers ON pt_sessions.input_trainer_id = trainers.id` 후 `COALESCE(trainers.name, '')`.
 - 파일명 헤더: `Content-Disposition: attachment; filename=sessions_YYYYMMDD.csv` (trainer_id 쿼리 시 `sessions_YYYYMMDD_trainer_<tid>.csv`).
-- Rate limit: `app.state.export_last_ts` dict (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429.
+- Rate limit: `app.state.export_last_ts` dict (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429 (이 경로에서는 `export_audit` INSERT 스킵).
 - 감사 로그: 매 성공 응답마다 stdout 1줄 `[export] owner_id={X} target_trainer_id={Y|all} rows={N}`.
+- `export_audit` INSERT 부수효과: 매 성공 응답마다 1 row. `(action='owner_export', actor_trainer_id=<owner_id>, target_trainer_id=<쿼리 trainer_id 값 or NULL>, rows=<data row 수>)`. stdout `[export]` 로그와 이중 기록 (관측 루트 다양성 확보).
 
 ### 트레이너 본인 export (`GET /my/export/sessions.csv`)
 
@@ -92,8 +95,9 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - 쿼리 파라미터: 없음. `pt_sessions.input_trainer_id = session["user"]["trainer_id"]`로 고정 필터링.
 - 응답: `text/csv; charset=utf-8`, 본문 **UTF-8 BOM** 접두 1회. 관장 export와 **컬럼 순서 bit-exact 동일** (`session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`).
 - 파일명 헤더: `Content-Disposition: attachment; filename="my_sessions_YYYYMMDD.csv"`. trainer_id 접미사 없음 (본인 것이므로 URL로 암시됨).
-- Rate limit: 별도 `app.state.my_export_last_ts` dict. 관장 `app.state.export_last_ts`와 **물리 분리**되어 상호 영향 없음. 60초 이내 재요청 시 429.
+- Rate limit: 별도 `app.state.my_export_last_ts` dict. 관장 `app.state.export_last_ts`와 **물리 분리**되어 상호 영향 없음. 60초 이내 재요청 시 429 (이 경로에서는 `export_audit` INSERT 스킵).
 - 감사 로그: stdout 1줄 `[my-export] trainer_id={X} rows={N}`. 관장 export 로그(`[export] ...`)와 prefix로 구분.
+- `export_audit` INSERT 부수효과: 매 성공 응답마다 1 row. `(action='my_export', actor_trainer_id=target_trainer_id=<session user trainer_id>, rows=<data row 수>)`. stdout `[my-export]` 로그와 이중 기록.
 - 공통 헬퍼: 양 라우트는 `app/routes.py` 내부 private 함수 `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int`를 공유한다. 컬럼명은 단일 상수 tuple `_SESSIONS_CSV_COLUMNS`로 정의되며 header/data writerow가 모두 이를 참조해 컬럼 drift를 코드 레벨에서 차단한다.
 
 ## 트레이너간 회원 접근 격리 (partial, iter 5 live)
@@ -107,6 +111,21 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - DB 마이그레이션 불요 — `members.trainer_id`가 iter 1부터 owner FK로 작동 중.
 - 풀버전 완성 (회원 자가 대시보드 + 관장 "트레이너별 평균치 비교" UI 비가시화 구조)은 **R5-full** 별도 티켓.
 
+## 감사 로그 뷰어 (iter 6 live)
+
+- `GET /my/audit-log` — 로그인한 트레이너(관장 포함)가 본인이 호출한 export 및 본인에게 가해진 관장 export 이력을 능동 조회하는 페이지.
+- 권한: `is_authenticated(request) == True`만. **`is_owner` 체크 없음** — 관장도 본인 자격으로 접근.
+- 쿼리: `export_audit` 테이블에서 WHERE 3 OR 조건으로 본인 관련 row만 필터:
+    1. `target_trainer_id = :self_tid` (본인이 target인 row)
+    2. `actor_trainer_id = :self_tid` (본인이 호출자인 row)
+    3. `action = 'owner_export' AND target_trainer_id IS NULL` (관장이 전체 대상으로 뽑은 row — 본인 포함으로 간주)
+- 정렬·상한: `ORDER BY id DESC LIMIT :MY_AUDIT_LOG_LIMIT` (`MY_AUDIT_LOG_LIMIT = 100` 모듈 상수).
+- 표시 컬럼: 일시 / 행위 / 호출자 / 대상 / rows. `action='owner_export' AND target IS NULL` → 대상 셀에 `"전체 대상(본인 포함)"` 렌더.
+- **페이지네이션 / 필터 / 정렬 UI / CSV export 금지** (first 배포 scope 봉쇄). 첫 배포 이후 기능 확장 금지.
+- **본인 조회 자체는 감사 대상 아님** — `/my/audit-log` GET 요청은 stdout/DB 로그를 남기지 않는다.
+- 템플릿은 각 row에 **불변 토큰**(예: `<tr data-action="{{ row.action }}">`)을 행당 정확히 1회 포함해야 한다 (테스트가 `r.text.count(...)` 기반 카운트 assertion으로 row 수를 검증).
+- DB 마이그레이션: `export_audit` 테이블은 `init_db()`의 `CREATE TABLE IF NOT EXISTS` 블록에 추가되어 최초 배포 시 자동 생성. ALTER TABLE·백필 스크립트 불요.
+
 ## 명시적 제외 항목 (이번 스프린트 금지)
 - 자세 교정 기록 / 자가보고 / 인바디 연동
 - AI 트레이너 대화
@@ -133,6 +152,4 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 
 ## 다음 스프린트 예약 티켓
 
-**트레이너 본인 감사 로그 뷰어** — `GET /my/audit-log` — 트레이너가 "누가 언제 내 입력분을 export 했는가"를 능동 조회하는 페이지. 현재 `[export]` / `[my-export]` stdout 감사 흔적은 트레이너가 직접 볼 수 없으므로, DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다. 시뮬 5/6 언급 2순위 우려(트레이너가 "감시 메커니즘이 live, 방어장치는 roadmap"이라고 판단하는 비대칭성 해소)에 대응.
-
 **R5-full — 회원 자가 대시보드 + 관장 트레이너별 비교 UI 비가시화 구조** — 목적: stakeholder 개선 포인트 #1 "트레이너 비교지표 도구화"의 구조적 완전 차단. 주의: **향후 관장 대시보드에 "트레이너별 평균치 비교" UI를 신규 도입할 때는 R5-full 게이트가 선행되어야 한다.** 현재 "UI 비가시화" 축은 "비교 UI 부재"로 satisfy된 상태이므로, 비교 UI 신규 도입 자체가 stakeholder 재설득 이슈를 재활성화한다.
```

## `docs/testing.md`

```diff
diff --git a/docs/testing.md b/docs/testing.md
index 90e9192..62ef917 100644
--- a/docs/testing.md
+++ b/docs/testing.md
@@ -7,7 +7,7 @@
 - 테스트 DB는 각 테스트마다 별도 temp file → teardown에서 제거.
 - `pytest.monkeypatch`를 통한 env / 모듈 attribute / 모듈 전역 dict 조작은 mock 금지 원칙에 저촉되지 않음 (conftest가 이미 이 방식으로 DB 경로와 env를 주입한다). 단 DB 자체를 mock하거나 `time.monotonic` 자체를 패치하는 것은 금지.
 
-## 테스트 구성 (6 파일)
+## 테스트 구성 (9 파일)
 1. `tests/test_aggregates.py` — 집계 함수 단위 테스트 (`max_weight_per_session`, `total_volume_per_session`). **CHECK 제약 스모크 테스트 포함**: 음수 weight / 미등록 exercise INSERT가 `sqlite3.IntegrityError`를 내는지 런타임 증명.
 2. `tests/test_auth.py` — 로그인 / 세션 / 로그아웃 라우트. **iteration 2 확장**: 관장 부트 시드(신규 INSERT / 기존 password_hash 불변 / username mismatch 시 warn+skip), non-owner 트레이너 로그인, `session["user"]` 스키마 검증.
 3. `tests/test_log_routes.py` — 로그 폼 GET / POST, 빈 세트 스킵, 검증 실패 처리. **iteration 2 확장**: POST /log가 세션의 `trainer_id`를 `pt_sessions.input_trainer_id`에 기록.
@@ -16,6 +16,7 @@
 6. `tests/test_export.py` (iteration 2 신규) — `/admin/export/sessions.csv` 권한 분기(owner only), `trainer_id` 쿼리 필터, 60초 rate limit, stdout 감사 로그 포맷, NULL `input_trainer_id` row의 빈 이름 렌더, UTF-8 BOM 본문 접두.
 7. `tests/test_my_export.py` (iteration 3 신규) — `/my/export/sessions.csv` 권한 분기(is_authenticated만 필요, is_owner bypass 없음), 본인 `input_trainer_id` 필터, 관장 로그인 시에도 본인 row만 반환, 60초 rate limit (관장 export와 dict 물리 분리), stdout 감사 로그 포맷 `[my-export] trainer_id=X rows=N`, UTF-8 BOM 본문 접두, `filename="my_sessions_YYYYMMDD.csv"` 헤더, **컬럼 동등성 회귀 테스트**(관장 `/admin/export?trainer_id=X` body와 X 로그인 `/my/export` body가 bit-exact 일치).
 8. `tests/test_member_access.py` (iteration 5 신규) — R5 partial isolation 가드. 12 시나리오: 타 트레이너 회원 GET/POST/chart-data/dashboard 4 라우트 → 403 "forbidden"; POST 403 시 pt_sessions·session_sets INSERT 0건 회귀; 본인 회원 4 라우트 → 200 regression; 관장 bypass 4 라우트 → 200 (tid 일치); 관장 + URL tid 불일치 → 404 (URL 위조 방지); 비로그인 → 303 /login; 존재하지 않는 mid → 404 (403과 구분); GET / 비관장 로그인 → 본인 첫 회원으로 303; GET / 관장 로그인 → 기존 동작 유지 303; GET / 회원 0건 트레이너 → 200 안내 페이지.
+9. `tests/test_my_audit_log.py` (iteration 6 신규) — N0 감사 로그 뷰어. 8 시나리오: ① 관장 `?trainer_id=X` export → export_audit 1 row (owner_export, actor=owner, target=X, rows 정확). ② 관장 쿼리 없이 export → 1 row (target=NULL). ③ 본인 `/my/export` → 1 row (my_export, actor=target=self). ④ `/my/audit-log` WHERE 3 OR 조건 회귀 방지 (타 트레이너 only row 미노출 — CTO 조건 4). ⑤ 미로그인 → 303 /login. ⑥ 관장 self-target row + target=NULL row 둘 다 관장 `/my/audit-log`에 노출 (CTO 조건 6). ⑦ `LIMIT 100` 검증 (`MY_AUDIT_LOG_LIMIT` 상수 import 기반). ⑧ `rows` 컬럼이 `_write_sessions_csv` 반환값(header 제외 data row 수)과 일치 (CTO 조건 5).
 
 ## 프레임워크
 - `pytest`, `pytest-asyncio` (async 라우트 테스트용)
```
