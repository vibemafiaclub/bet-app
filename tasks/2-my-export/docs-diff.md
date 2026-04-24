# docs-diff: my-export

Baseline: `596c930`

## `docs/spec.md`

```diff
diff --git a/docs/spec.md b/docs/spec.md
index 218c1a3..525bc3c 100644
--- a/docs/spec.md
+++ b/docs/spec.md
@@ -36,6 +36,7 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - GET /trainers/{tid}/members/{mid}/dashboard — 차트 뷰 (Chart.js canvas 2개)
 - GET /trainers/{tid}/members/{mid}/chart-data.json — 차트 데이터 JSON
 - `GET /admin/export/sessions.csv?trainer_id=<int>` — 관장 전용 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
+- `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 입력분 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
 
 ## 인증
 
@@ -72,15 +73,29 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 
 ## CSV Export
 
+> iteration 3에서 `/my/export/sessions.csv`가 추가됐다. 관장 전용 `/admin/export/sessions.csv`와 공통 헬퍼 `_write_sessions_csv`를 공유하여 컬럼 drift를 코드 레벨에서 방지한다.
+
+### 관장 export (`GET /admin/export/sessions.csv`)
+
 - 권한: `session["user"]["is_owner"] == True`만. 아니면 303 → `/`.
 - 쿼리: `trainer_id` (optional). 있으면 `pt_sessions.input_trainer_id = trainer_id` 필터. 없으면 전체.
 - 응답: `text/csv; charset=utf-8`. 본문 **UTF-8 BOM (`﻿`) 접두** 1회 (Excel 기본 열기 한글 깨짐 방지).
 - 컬럼 순서 고정: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`
 - `input_trainer_name`은 `LEFT JOIN trainers ON pt_sessions.input_trainer_id = trainers.id` 후 `COALESCE(trainers.name, '')`.
 - 파일명 헤더: `Content-Disposition: attachment; filename=sessions_YYYYMMDD.csv` (trainer_id 쿼리 시 `sessions_YYYYMMDD_trainer_<tid>.csv`).
-- Rate limit: 모듈 전역 `dict[int, float]` (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429. **테스트 간 state 누수 방지를 위해 전역 dict는 `app.state`에 붙이거나 앱 팩토리 closure로 은닉**.
+- Rate limit: `app.state.export_last_ts` dict (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429.
 - 감사 로그: 매 성공 응답마다 stdout 1줄 `[export] owner_id={X} target_trainer_id={Y|all} rows={N}`.
 
+### 트레이너 본인 export (`GET /my/export/sessions.csv`)
+
+- 권한: `is_authenticated(request) == True` 만. is_owner 체크 없음. 관장도 본인 자격으로 호출 가능 (단, 관장 본인의 `trainer_id` row만 반환되며 is_owner bypass 없음).
+- 쿼리 파라미터: 없음. `pt_sessions.input_trainer_id = session["user"]["trainer_id"]`로 고정 필터링.
+- 응답: `text/csv; charset=utf-8`, 본문 **UTF-8 BOM** 접두 1회. 관장 export와 **컬럼 순서 bit-exact 동일** (`session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`).
+- 파일명 헤더: `Content-Disposition: attachment; filename="my_sessions_YYYYMMDD.csv"`. trainer_id 접미사 없음 (본인 것이므로 URL로 암시됨).
+- Rate limit: 별도 `app.state.my_export_last_ts` dict. 관장 `app.state.export_last_ts`와 **물리 분리**되어 상호 영향 없음. 60초 이내 재요청 시 429.
+- 감사 로그: stdout 1줄 `[my-export] trainer_id={X} rows={N}`. 관장 export 로그(`[export] ...`)와 prefix로 구분.
+- 공통 헬퍼: 양 라우트는 `app/routes.py` 내부 private 함수 `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int`를 공유한다. 컬럼명은 단일 상수 tuple `_SESSIONS_CSV_COLUMNS`로 정의되며 header/data writerow가 모두 이를 참조해 컬럼 drift를 코드 레벨에서 차단한다.
+
 ## 트레이너간 회원 접근 격리
 
 - 이번 스프린트는 **permissive**. 트레이너A가 트레이너B 담당 회원의 `/trainers/{tid}/members/{mid}/...` URL을 직접 입력하면 접근 가능.
@@ -113,4 +128,4 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 
 ## 다음 스프린트 예약 티켓
 
-**트레이너 본인의 "내 입력분 CSV export" 라우트** — `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 `input_trainer_id`만 필터링하여 다운로드. 관장 허가 불요. 이 기능이 붙어야 개선점 4("트레이너·헬스장 공동 소유, 퇴사 시 트레이너 본인이 export 가능")의 해소가 완성된다. iteration 2 백필 스크립트 실행이 이 기능의 전제.
+**트레이너 본인 감사 로그 뷰어** — `GET /my/audit-log` — 트레이너가 "누가 언제 내 입력분을 export 했는가"를 능동 조회하는 페이지. 현재 `[export]` / `[my-export]` stdout 감사 흔적은 트레이너가 직접 볼 수 없으므로, DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다. 시뮬 5/6 언급 2순위 우려(트레이너가 "감시 메커니즘이 live, 방어장치는 roadmap"이라고 판단하는 비대칭성 해소)에 대응.
```

## `docs/testing.md`

```diff
diff --git a/docs/testing.md b/docs/testing.md
index cb2ccb2..1edcc1c 100644
--- a/docs/testing.md
+++ b/docs/testing.md
@@ -14,6 +14,7 @@
 4. `tests/test_dashboard.py` — `chart-data.json` 계약. **빈 member 케이스(세션 0건)에서 labels=[], datasets=[] 반환 확인 필수**.
 5. `tests/test_e2e_dashboard.py` — Playwright headless. uvicorn 서브프로세스 fixture는 teardown에서 `process.terminate() + process.wait(timeout=5)` 필수. 임시 DB 파일 cleanup 필수.
 6. `tests/test_export.py` (iteration 2 신규) — `/admin/export/sessions.csv` 권한 분기(owner only), `trainer_id` 쿼리 필터, 60초 rate limit, stdout 감사 로그 포맷, NULL `input_trainer_id` row의 빈 이름 렌더, UTF-8 BOM 본문 접두.
+7. `tests/test_my_export.py` (iteration 3 신규) — `/my/export/sessions.csv` 권한 분기(is_authenticated만 필요, is_owner bypass 없음), 본인 `input_trainer_id` 필터, 관장 로그인 시에도 본인 row만 반환, 60초 rate limit (관장 export와 dict 물리 분리), stdout 감사 로그 포맷 `[my-export] trainer_id=X rows=N`, UTF-8 BOM 본문 접두, `filename="my_sessions_YYYYMMDD.csv"` 헤더, **컬럼 동등성 회귀 테스트**(관장 `/admin/export?trainer_id=X` body와 X 로그인 `/my/export` body가 bit-exact 일치).
 
 ## 프레임워크
 - `pytest`, `pytest-asyncio` (async 라우트 테스트용)
```
