# docs-diff: member-access

Baseline: `03545a3`

## `docs/spec.md`

```diff
diff --git a/docs/spec.md b/docs/spec.md
index 525bc3c..4193191 100644
--- a/docs/spec.md
+++ b/docs/spec.md
@@ -96,11 +96,16 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - 감사 로그: stdout 1줄 `[my-export] trainer_id={X} rows={N}`. 관장 export 로그(`[export] ...`)와 prefix로 구분.
 - 공통 헬퍼: 양 라우트는 `app/routes.py` 내부 private 함수 `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int`를 공유한다. 컬럼명은 단일 상수 tuple `_SESSIONS_CSV_COLUMNS`로 정의되며 header/data writerow가 모두 이를 참조해 컬럼 drift를 코드 레벨에서 차단한다.
 
-## 트레이너간 회원 접근 격리
+## 트레이너간 회원 접근 격리 (partial, iter 5 live)
 
-- 이번 스프린트는 **permissive**. 트레이너A가 트레이너B 담당 회원의 `/trainers/{tid}/members/{mid}/...` URL을 직접 입력하면 접근 가능.
-- 단 URL의 `tid`와 `mid`는 `members WHERE id=mid AND trainer_id=tid` 필터로 검증 유지 → 잘못된 조합은 404.
-- 트레이너간 완전 격리는 **R5 (회원용 자가 대시보드 + 트레이너 IP 가드레일)**에서 다룸. 이번 스프린트 범위 외.
+- 비관장 트레이너는 `members.trainer_id == session.user.trainer_id`인 회원만 `/trainers/{tid}/members/{mid}/log` (GET/POST), `/trainers/{tid}/members/{mid}/chart-data.json`, `/trainers/{tid}/members/{mid}/dashboard` 4개 라우트에 접근 가능.
+- 미소유 (존재하나 타 트레이너 소유) → **403** (`text/plain` 평문 `forbidden`). 존재 여부 은폐 안 함 — 감사 가시성 목적.
+- mid 자체가 부재 → **404** (`HTMLResponse` "회원을 찾을 수 없습니다."). 403과 구분됨에 주의.
+- URL의 `tid`가 `members.trainer_id`와 불일치 → **404** (관장 포함, URL 위조 방지). `members WHERE id=mid AND trainer_id=tid` 필터로 검증 유지.
+- 관장(`is_owner=1`)은 소유 검사 bypass. 단 URL `tid`가 해당 회원의 소유 트레이너 ID와 일치할 때만 bypass 유효. 불일치 시 404.
+- `GET /`는 로그인 트레이너의 **본인 소유 첫 회원**으로 redirect (`/trainers/{self_tid}/members/{first_mid}/log`). 관장은 기존 동작 유지(DB의 첫 트레이너 + 첫 회원). 비관장 + 본인 회원 0건 → 200 안내 페이지 (`담당 회원이 아직 없습니다. 관장에게 요청하세요.`).
+- DB 마이그레이션 불요 — `members.trainer_id`가 iter 1부터 owner FK로 작동 중.
+- 풀버전 완성 (회원 자가 대시보드 + 관장 "트레이너별 평균치 비교" UI 비가시화 구조)은 **R5-full** 별도 티켓.
 
 ## 명시적 제외 항목 (이번 스프린트 금지)
 - 자세 교정 기록 / 자가보고 / 인바디 연동
@@ -110,7 +115,7 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - 회원용 UI (트레이너 전용)
 - 다중 헬스장 (여전히 금지)
 - 회원 CRUD 웹 UI (seed 스크립트 only)
-- 복잡 RBAC / 트레이너 간 회원 접근 격리 (R5에서 다룸)
+- 트레이너 간 회원 접근 풀버전 격리 — 회원 자가 대시보드 + 관장 "트레이너별 평균치 비교" UI 비가시화 (R5-full에서 다룸). 서버사이드 4 라우트 가드 + GET / redirect는 iter 5에서 live.
 - **로그인 brute-force 보호 / 로그인 rate limit** (스프린트 외). 단 `/admin/export/sessions.csv`는 IP 자산 유출 경로이므로 owner_trainer_id별 60초 in-memory rate limit만 최소 감사 흔적으로 허용.
 - 11번째 이후 운동 종목
 - 코드 내 "TODO: 다중 트레이너" 같은 힌트 주석도 금지
@@ -129,3 +134,5 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 ## 다음 스프린트 예약 티켓
 
 **트레이너 본인 감사 로그 뷰어** — `GET /my/audit-log` — 트레이너가 "누가 언제 내 입력분을 export 했는가"를 능동 조회하는 페이지. 현재 `[export]` / `[my-export]` stdout 감사 흔적은 트레이너가 직접 볼 수 없으므로, DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다. 시뮬 5/6 언급 2순위 우려(트레이너가 "감시 메커니즘이 live, 방어장치는 roadmap"이라고 판단하는 비대칭성 해소)에 대응.
+
+**R5-full — 회원 자가 대시보드 + 관장 트레이너별 비교 UI 비가시화 구조** — 목적: stakeholder 개선 포인트 #1 "트레이너 비교지표 도구화"의 구조적 완전 차단. 주의: **향후 관장 대시보드에 "트레이너별 평균치 비교" UI를 신규 도입할 때는 R5-full 게이트가 선행되어야 한다.** 현재 "UI 비가시화" 축은 "비교 UI 부재"로 satisfy된 상태이므로, 비교 UI 신규 도입 자체가 stakeholder 재설득 이슈를 재활성화한다.
```

## `docs/testing.md`

```diff
diff --git a/docs/testing.md b/docs/testing.md
index 1edcc1c..90e9192 100644
--- a/docs/testing.md
+++ b/docs/testing.md
@@ -15,6 +15,7 @@
 5. `tests/test_e2e_dashboard.py` — Playwright headless. uvicorn 서브프로세스 fixture는 teardown에서 `process.terminate() + process.wait(timeout=5)` 필수. 임시 DB 파일 cleanup 필수.
 6. `tests/test_export.py` (iteration 2 신규) — `/admin/export/sessions.csv` 권한 분기(owner only), `trainer_id` 쿼리 필터, 60초 rate limit, stdout 감사 로그 포맷, NULL `input_trainer_id` row의 빈 이름 렌더, UTF-8 BOM 본문 접두.
 7. `tests/test_my_export.py` (iteration 3 신규) — `/my/export/sessions.csv` 권한 분기(is_authenticated만 필요, is_owner bypass 없음), 본인 `input_trainer_id` 필터, 관장 로그인 시에도 본인 row만 반환, 60초 rate limit (관장 export와 dict 물리 분리), stdout 감사 로그 포맷 `[my-export] trainer_id=X rows=N`, UTF-8 BOM 본문 접두, `filename="my_sessions_YYYYMMDD.csv"` 헤더, **컬럼 동등성 회귀 테스트**(관장 `/admin/export?trainer_id=X` body와 X 로그인 `/my/export` body가 bit-exact 일치).
+8. `tests/test_member_access.py` (iteration 5 신규) — R5 partial isolation 가드. 12 시나리오: 타 트레이너 회원 GET/POST/chart-data/dashboard 4 라우트 → 403 "forbidden"; POST 403 시 pt_sessions·session_sets INSERT 0건 회귀; 본인 회원 4 라우트 → 200 regression; 관장 bypass 4 라우트 → 200 (tid 일치); 관장 + URL tid 불일치 → 404 (URL 위조 방지); 비로그인 → 303 /login; 존재하지 않는 mid → 404 (403과 구분); GET / 비관장 로그인 → 본인 첫 회원으로 303; GET / 관장 로그인 → 기존 동작 유지 303; GET / 회원 0건 트레이너 → 200 안내 페이지.
 
 ## 프레임워크
 - `pytest`, `pytest-asyncio` (async 라우트 테스트용)
```
