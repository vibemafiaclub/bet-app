# Phase 0: docs

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` (현재 iter 2~3까지 반영된 단일 스펙. 특히 99~103행 "트레이너간 회원 접근 격리" 섹션, 113행 "명시적 제외 항목", "다음 스프린트 예약 티켓" 섹션 — 이번 phase에서 직접 수정 대상)
- `/docs/testing.md` ("테스트 구성" 섹션 — 8번째 파일 항목 추가 대상)
- `/docs/user-intervention.md` (변경 없음 확인용 read-only)
- `/docs/mission.md` (비즈니스 맥락)
- `/iterations/5-20260424_104337/requirement.md` (요구사항 원문. "채택된 요구사항" 섹션 + 98~104행 iter 4 언급)

## 작업 내용

이번 phase는 **문서 업데이트만** 수행한다. 코드(`app/`, `tests/`)는 절대 건드리지 않는다.

### 1. `docs/spec.md` — 99~103행 "트레이너간 회원 접근 격리" 섹션 재작성

현재 permissive 정책이 적혀있다. iter 5에서 partial isolation이 live로 붙었으므로 다음 내용이 **반드시 포함**되어야 한다:

- 섹션 제목은 "트레이너간 회원 접근 격리 (partial, iter 5 live)"로 변경.
- 비관장 트레이너는 `members.trainer_id == session.user.trainer_id`인 회원의 `/trainers/{tid}/members/{mid}/log` (GET/POST), `/trainers/{tid}/members/{mid}/chart-data.json`, `/trainers/{tid}/members/{mid}/dashboard` 4개 라우트만 접근 가능.
- 미소유 (존재하나 타 트레이너 소유) → **403** (`text/plain` 평문 `forbidden`).
- mid 자체가 부재 → **404** (`HTMLResponse` "회원을 찾을 수 없습니다."). 존재 여부 은폐 안 함 — 감사 가시성 목적.
- URL의 `tid`가 `members.trainer_id`와 불일치 → **404** (관장 포함, URL 위조 방지). 403과 구분됨에 주의.
- 관장(`is_owner=1`)은 소유 검사 bypass. 단 URL `tid`가 해당 회원의 소유 트레이너 ID와 일치할 때만 bypass 유효. 불일치 시 404.
- `GET /`는 로그인 트레이너의 **본인 소유 첫 회원**으로 redirect (`/trainers/{self_tid}/members/{first_mid}/log`). 관장은 기존 동작 유지(DB의 첫 트레이너 + 첫 회원). 비관장 + 본인 회원 0건 → 200 안내 페이지 (`담당 회원이 아직 없습니다. 관장에게 요청하세요.`).
- DB 마이그레이션 불요 — `members.trainer_id`가 iter 1부터 owner FK로 작동 중.
- 풀버전 완성 (회원 자가 대시보드 + 관장 "트레이너별 평균치 비교" UI 비가시화 구조)은 **R5-full** 별도 티켓.

### 2. `docs/spec.md` — 113행 "명시적 제외 항목"의 해당 줄 교체

현재: `복잡 RBAC / 트레이너 간 회원 접근 격리 (R5에서 다룸)` 줄을 다음으로 치환한다:

`트레이너 간 회원 접근 풀버전 격리 — 회원 자가 대시보드 + 관장 "트레이너별 평균치 비교" UI 비가시화 (R5-full에서 다룸). 서버사이드 4 라우트 가드 + GET / redirect는 iter 5에서 live.`

### 3. `docs/spec.md` — "다음 스프린트 예약 티켓" 섹션 갱신

이미 "트레이너 본인 감사 로그 뷰어" 항목이 적혀있다. 그 뒤에 **새 항목으로 R5-full**을 추가한다. 내용:

- **R5-full — 회원 자가 대시보드 + 관장 트레이너별 비교 UI 비가시화 구조**
- 목적: stakeholder 개선 포인트 #1 "트레이너 비교지표 도구화"의 구조적 완전 차단.
- 주의: **향후 관장 대시보드에 "트레이너별 평균치 비교" UI를 신규 도입할 때는 R5-full 게이트가 선행되어야 한다.** 현재 "UI 비가시화" 축은 "비교 UI 부재"로 satisfy된 상태이므로, 비교 UI 신규 도입 자체가 stakeholder 재설득 이슈를 재활성화한다.

### 4. `docs/testing.md` — "테스트 구성" 섹션에 8번째 파일 추가

10~17행의 번호 리스트에 다음 8번 항목을 추가한다:

`8. tests/test_member_access.py (iteration 5 신규) — R5 partial isolation 가드. 12 시나리오: 타 트레이너 회원 GET/POST/chart-data/dashboard 4 라우트 → 403 "forbidden"; POST 403 시 pt_sessions·session_sets INSERT 0건 회귀; 본인 회원 4 라우트 → 200 regression; 관장 bypass 4 라우트 → 200 (tid 일치); 관장 + URL tid 불일치 → 404 (URL 위조 방지); 비로그인 → 303 /login; 존재하지 않는 mid → 404 (403과 구분); GET / 비관장 로그인 → 본인 첫 회원으로 303; GET / 관장 로그인 → 기존 동작 유지 303; GET / 회원 0건 트레이너 → 200 안내 페이지.`

### 5. `docs/user-intervention.md` — 변경 없음

새 env/secret/수동 스크립트 없음. 이 파일은 건드리지 마라.

### 6. `iterations/5-20260424_104337/requirement.md` — iter 4 gap note 1줄 추가

98~104행 섹션 "F. (iteration 4) 트레이너 본인 감사 로그 뷰어..." 바로 아래에 다음 한 줄 blockquote를 추가한다(섹션 본문의 마지막 bullet 바로 아래, 섹션 G "트레이너간 회원 접근" 직전):

`> 주의: iter 4 '/my/audit-log'는 이 섹션 서술과 달리 실제 코드(app/routes.py)에 미반영 상태. 별도 reconciliation task 필요.`

이 note는 `docs/spec.md`에는 넣지 않는다 (single source of truth 원칙 — spec은 live 상태만 기술).

## Acceptance Criteria

```bash
# 1. docs/spec.md의 99~103행 범위에 "partial" 또는 "iter 5" 문자열 포함
grep -E "partial|iter 5" docs/spec.md | head -5

# 2. docs/spec.md 113행 영역에 "R5-full"이 포함되고 옛 "R5에서 다룸" 문구 부재
grep "R5-full" docs/spec.md
! grep "R5에서 다룸" docs/spec.md

# 3. docs/testing.md에 test_member_access.py 추가
grep "test_member_access.py" docs/testing.md

# 4. iterations/5-20260424_104337/requirement.md에 iter 4 gap note 추가
grep "reconciliation task 필요" iterations/5-20260424_104337/requirement.md

# 5. 파이썬 코드 파일이 수정되지 않았음 확인 (이번 phase 범위 외)
! git diff --name-only HEAD | grep -E '^(app|tests|scripts)/'
```

## AC 검증 방법

위 AC 커맨드를 직접 실행하라. 모두 통과하면 `/tasks/3-member-access/index.json`의 phase 0 status를 `"completed"`로 변경하라.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 index.json의 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- `app/`, `tests/`, `scripts/` 디렉토리 파일은 **절대 수정 금지**. 이번 phase는 문서 전용.
- `docs/spec.md`의 "CSV Export" 섹션(74~97행), "인증" 섹션(41~53행) 등 다른 영역은 건드리지 마라.
- 99~103행 재작성 시 기존 "URL의 tid와 mid는 members WHERE id=mid AND trainer_id=tid 필터로 검증" 문구는 **개편 후 문맥에 맞게 녹여도 되지만 삭제는 금지** — "tid 불일치 시 404"는 iter 5에서도 유효하다.
- docs-diff.md는 만들지 마라. phase 0 완료 후 `scripts/gen-docs-diff.py`가 자동 생성한다.
- iter 4 gap note는 **blockquote 1줄 이내**로 유지. 확장 금지.
- 기존 테스트를 깨뜨리지 마라 (이번 phase는 docs만 만지므로 깨뜨릴 일 없지만 원칙 확인).
