# Requirement

## 가치제안

# BET (Best Training) — PT 트레이너·헬스장 관장용 가치제안 (iteration 2)

> 전달 모드: landing_plus_meeting
> 배포 상태: **MVP v1 라이브** (iteration 1 배포 완료). 현재 세션 입력 폼 + 회원별 2개 꺾은선 그래프(최대중량/세션 볼륨)가 Fly.io 서버에서 동작 중.
> 대상: 중소 동네 헬스장 관장 겸 트레이너 (회원 ~50명 규모)
> 기존 도구: Rappo 병행 사용 전제

---

## 0. 이번 미팅의 맥락

지난 미팅에서 합의한 12주 무료 파일럿의 **첫 2주가 지난 시점** 기준 후속 미팅입니다.
- iteration 1 실물이 Fly.io에 올라가 있고, 관장님 담당 회원 3명이 접근 가능한 URL로 제공됨.
- 아래 "현재 동작" 섹션이 지금 실제로 쓸 수 있는 것, "로드맵" 섹션이 파일럿 잔여 기간(10주) 동안 이어서 붙여갈 것.
- 이 미팅의 목적은 "다음에 무엇을 먼저 만들지"를 관장님 피드백으로 정하는 것입니다.

---

## 1. 랜딩페이지 카피

### 한 줄 소개

**BET — PT의 "보이지 않는 성장"을 눈에 보이게 만드는 AI 트레이너**

### 서브 카피

- 인바디 수치 한 장으로 끝나던 회원 성과를, 다차원 그래프로 잠재회원에게 증명하세요.
- 회원의 PT 외 6일 24시간을 AI 트레이너가 관리합니다. 생활습관 데이터가 쌓일수록 트레이너의 피드백은 더 날카로워집니다.
- 헬스장 단위 월 구독. 회원 1인당 월 9,900원부터. (헬스장이 패키지화해서 회원에게 전가하는 것도 가능)

### 핵심 한 줄

> "PT 품질의 증거를, 트레이너가 아닌 데이터가 말하게 합니다."

### 랜딩 CTA

- "[무료] 3개월 파일럿 신청" → 12주 간 3개 회원 계정 무료 제공, 이후 성과 확인 후 정식 계약.

---

## 2. 해결하려는 문제 (Pain Statement)

### 트레이너·관장 관점

1. **"우리 PT 좋아요"를 증명할 자료가 빈약함.** 상담 테이블에서 인바디 수치 하나만 올려놓고 설득해야 하는데, 인바디는 회원의 식단·수면에 크게 흔들리는 표면 지표라 PT 품질 증명력이 낮음.
2. **회원 발전 추이 가시화가 기존 도구에서 제공되지 않음.** Rappo 등 공유 캘린더·채팅 일지 도구에는 이 기능이 없어, 회원이 실제로 얼마나 변했는지를 누구도 눈으로 확인하지 못함.
3. **PT 외 6일을 방치**. 주 1회 PT만으로 성과가 결정되지 않음을 트레이너 본인도 알지만, PT 외 시간 회원 습관을 직접 관리할 리소스가 없음.
4. **리텐션 고민**. 회원이 "3개월 하고 빠지는 패턴"을 끊고 싶지만, 지속적 동기부여 장치가 부재.

### 회원(downstream) 관점

1. PT 받는 날만 운동에 집중하고 나머지 6일은 무방비 상태.
2. 내가 발전하고 있는지가 애매 — 인바디 외에는 피드백이 산발적 채팅 일지에 묻혀있음.
3. 트레이너 퇴직·이직 시 축적된 내 운동 히스토리가 증발.

---

## 3. 현재 동작하는 것 (iteration 1, 라이브)

관장님이 지금 URL 열어서 바로 쓸 수 있는 기능:

### A. 세션 기록 입력 폼 (`/trainers/:tid/members/:mid/log`)

- PT 세션 종료 직후, 한 화면에서 **세트 단위**로 `운동 / 중량(kg) / 횟수`를 입력.
- HTMX 기반이라 "세트 행 추가" 버튼 하나로 세트 수만큼 행을 늘릴 수 있고, 제출도 페이지 리로드 없이.
- 운동 종목은 10종 고정: 스쿼트 / 벤치프레스 / 데드리프트 / 오버헤드프레스 / 바벨로우 / 풀업 / 레그프레스 / 랫풀다운 / 레그컬 / 덤벨컬.
- 입력 자체가 기록이 되고 즉시 대시보드에 반영.

### B. 회원별 진행 대시보드 (`/trainers/:tid/members/:mid/dashboard`)

회원 1명에 대해 꺾은선 그래프 2개가 한 화면에 있음:

1. **운동 종목별 최대 중량 추이** — 해당 회원이 실제로 수행한 종목만 선으로. 세션마다 그 종목의 최대 중량이 찍힘.
2. **세션당 총 볼륨 추이** — Σ(중량 × 횟수). 그날 전체 운동량의 대리지표.

잠재회원 상담 시, 관장님이 이 화면을 태블릿으로 열어 "이 회원은 12주간 이렇게 찍어왔습니다" 라고 보여주는 것이 현 단계의 사용 시나리오입니다.

### C. 인증·운영 (최소)

- 관장님 계정 1개 (하드코딩 어드민). 환경변수로 주입.
- Fly.io 단일 서버에 배포. 데이터는 영속 볼륨의 SQLite.

### D. 현 시점의 명시적 한계

아래는 **아직 없음**. 이번 미팅에서 우선순위 피드백이 필요합니다.

- 자세 교정 기록, 컨디션/수면/식단 자가보고, 인바디 연동 → **볼륨 외 지표 없음**.
- AI 트레이너 (PT 외 시간 대화) → **PT 외 6일 코칭 기능 없음**.
- PDF 리포트 내보내기 → **상담장에서 인쇄물로 주기 불가**.
- Rappo CSV/API 연동 → **회원 명단은 seed 스크립트로 관장님이 요청 시 BET 측이 넣어드리는 구조**.
- 회원용 UI → **회원은 자기 대시보드 직접 접근 불가** (관장님이 대면 공유).
- 다중 트레이너 / 다중 헬스장 → **관장님 계정 1개 전제**.

---

## 4. 파일럿 잔여 10주 로드맵 (우선순위 미확정 — 오늘 함께 정할 것)

아래 6개 기능 중 한 번에 1개씩 붙일 계획. 순서는 관장님 피드백으로 정합니다.

### R1. PDF "12주 성장 리포트" 출력

- 대시보드 화면을 A4 1~2장 PDF로 내려받기. 상담 테이블에 바로 올릴 수 있는 인쇄물.
- 그래프 + 회원 이름 + 기간 요약 + 트레이너 서명란.
- **가치**: 파일럿 DoD에 걸려있는 "12주 성장 리포트 PDF" 약속 자체가 여기서 이행됨.

### R2. 컨디션·수면·식단 자가보고 (회원용 최소 UI)

- 회원에게 하루 1회 30초짜리 카카오톡/SMS 링크 발송 → 간단 체크리스트.
- 대시보드에 "생활습관 일관성 점수" 선 1개 추가 → 볼륨/중량과 중첩해서 볼 수 있음.
- **가치**: "PT 외 6일 방치" pain의 1단계 해소 + 발전 곡선의 다차원화(인바디 의존도 탈출).

### R3. AI 트레이너 카카오톡 채널 (MVP 수준)

- 회원이 카카오톡 채널에 식단 사진/컨디션/자가영상을 보내면 AI가 당일 가벼운 피드백 제공.
- AI는 해당 회원 PT 기록 + 관장님이 설정한 "프로토콜(자세·강도·어조)"을 컨텍스트로 사용.
- 이상 신호(과훈련, 급격한 체중 변화 서술 등) 감지 시 관장님에게 알림.
- **가치**: pain 3(PT 외 6일 방치) 본격 해소. BET의 핵심 차별화.

### R4. Rappo 연동 (CSV import 우선, API 추후)

- 관장님이 Rappo에서 회원 목록 CSV 내보내기 → BET 관리화면에 업로드 → 자동 동기화.
- 연락처 기준으로 중복 방지 + 신규/삭제/수정 diff 표시.
- **가치**: "이중 운영 부담" reject_trigger 직접 해소. 회원 DB 단일 소스.

### R5. 회원용 자가 대시보드 + 트레이너 IP 가드레일

- 회원이 개인 URL로 자기 대시보드만 열람 가능.
- 동시에: 관장이 "회원 평균 발전 곡선"을 소속 트레이너 평가·방출 근거로 쓰지 못하도록 **용도 고지 배너 + 관장 뷰에서 개별 트레이너 평균 곡선 비노출**.
- **가치**: pain 4(리텐션) + 소속 트레이너 drop 리스크(이전 시뮬에서 drop→accept 전환 핵심 조건) 선제 해소.

### R6. 자세 교정 태그 입력 (트레이너용 quick action)

- 세션 입력 폼 옆에 "교정 포인트" 태그 3~5개 선택 가능 (예: 스쿼트 depth, 벤치 아치, 데드 힙힌지).
- 대시보드에 "교정 빈도 감소 추이" 한 줄 추가.
- **가치**: "자세 교정은 대체 불가" 라는 우리 포지션과 일치 + 트레이너의 고유 노하우가 데이터로 남음(IP 보호 명분).

---

## 5. 가격 플랜 (세일즈 미팅 단계에서만 공개)

- **파일럿 (12주)**: 무료. 회원 3명까지. 정식 계약 전환 시 조건 없음. **이미 시작됨(2주차)**.
- **스탠다드**: **회원 1인당 월 9,900원**. 최소 10명부터.
- **엔터프라이즈** (50명 이상): 월 인당 8,000원.
- **연 일시불 결제 시 10% 할인.**
- 헬스장이 회원에게 요금을 어떻게 전가할지(패키지 판매, 무료 제공)는 자율. BET은 헬스장에만 청구.

---

## 6. 자주 받는 질문 (세일즈 미팅용 FAQ)

### Q1. Rappo를 해지해야 하나요?

아니요. 현재 회원 명단은 관장님이 알려주시면 BET 측이 seed 스크립트로 넣어드리는 수동 방식입니다(회원 3명 기준이라 부담 없음). R4(Rappo CSV 연동)가 붙으면 이 수동 과정도 사라집니다. 캘린더·운영관리는 계속 Rappo를 쓰셔도 됩니다.

### Q2. 회원이 앱 설치·매일 기록을 귀찮아하면요?

현 iteration 1 기준 **회원은 아무것도 설치/입력하지 않습니다** — 대시보드는 관장님이 대면으로 보여주는 용도. R2/R3가 붙는 시점에도 카카오톡 채널로 동작하므로 앱 설치는 필수 아님.

### Q3. 소속 트레이너들이 "내 방식대로 못 한다"며 반대하면요?

R3 AI 트레이너가 붙는 시점에 트레이너별 프로토콜(운동 설계 규칙, 자세 교정 중점, AI의 어조·강도) 커스터마이즈를 제공할 계획. 현 단계에서는 관장님 담당 회원 3명만 대상이라 소속 트레이너 영향 범위 밖입니다.

### Q4. 데이터가 우리 회원 데이터인가, BET 데이터인가?

헬스장 소유. 계약 해지 시 전체 CSV/PDF 내보내기 제공(R1 PDF 기능이 이 약속의 실물). BET은 익명화된 집계 데이터만 제품 개선에 활용.

### Q5. 트레이너가 퇴사하면 쌓인 AI 컨텍스트는?

R3가 붙으면 회원 단위로 귀속. 트레이너 교체 시 새 트레이너가 해당 회원의 컨텍스트를 그대로 승계.

### Q6. 지금까지 2주 써 보니 어떻습니까? 관장님 피드백이 우선순위 결정의 유일한 근거입니다.

(오늘 미팅의 본 논의 지점)

---

## 7. 오늘 미팅의 구체적 요청

관장님께 다음 3개 질문을 드립니다:

1. **지난 2주 실제 사용성** — 입력 폼 UX, 대시보드가 상담에 실제로 쓸 만한가?
2. **다음 10주 동안 R1~R6 중 가장 먼저 붙이고 싶은 1개**. 선택 이유가 핵심.
3. **시뮬되지 않은 소속 트레이너 걱정** — 이 로드맵 중 "다른 트레이너가 강하게 반대할 것 같은" 항목이 있다면 어느 것?

---

## 8. BET이 약속하지 않는 것 (리스크 솔직 고지)

- 인바디 수치의 **단기** 개선을 약속하지 않음. AI가 하는 건 "생활습관 일관성"이지 "빠른 결과"가 아님.
- 트레이너의 자세 교정을 대체하지 않음. BET은 그 시간을 확보해 주는 도구.
- 헬스장 매출을 직접 올리는 마케팅 도구 아님. "상담 전환율"을 올릴 자료를 제공하는 도구.
- iteration 1 단계의 대시보드는 **세션 중량/볼륨만**을 보여줌. 더 풍부한 다차원 그래프는 R2 이후에 가능.

## 채택된 요구사항

- **run_id**: `pt-trainer-owner-01_20260424_034244`
- **title**: 소속 트레이너별 로그인 계정 + 세션 기록의 "입력자 트레이너" 귀속 + 관장 전용 트레이너별 CSV 내보내기

### 유래한 고객 pain + 근거 인용

유래한 페르소나: `pt-trainer-owner-01` (50명 규모 동네 헬스장 관장 겸 트레이너) + 직접 stakeholder `sh-other-trainers` (소속 트레이너).

시뮬 최종 판정: **실패 / stakeholders_persist_drop** — 3라운드 재설득 끝에도 소속 트레이너 drop 유지(confidence 65, 70선 미달).

해소하는 pain (report.md 직접 인용):

- **개선점 3 — 개별 트레이너 계정·데이터 귀속 설계의 부재** (`report.md` / 3개 세션 반복 언급, 02·04-r2·04-r3)
  > "iteration 1은 '관장님 계정 1개 하드코딩'이다. 내 담당 회원 기록이 관장 계정으로 들어가는 구조 같은데, 내 입력과 관장 입력이 구분되는지, 내가 퇴사 시 내 입력분이 따라 나올 수 있는지 불분명." (`02_stakeholder_sh-other-trainers.md`)

  개선 방향: *"로그인 분리 + 세션 로그 입력자 귀속 + 퇴사 시 CSV 분리 권한 + R6 교정 태그 IP 처리까지 포함한 계정 설계 초안을 정식 계약 전제로 선제 제출."*

- **round 3 drop 지속 조건 — stakeholder가 70선 돌파 조건으로 명시한 3종 실물 중 1종**
  > "(2)(3)(7)에 직결된 BET 실물 스펙 3종(R5 UI/API 차단, R3 오버라이드 데모, **개별 계정 설계 초안**)은 여전히 대기 상태다. 내가 round 2에서 '70선을 넘으려면 3종 세트 실물'이라고 못박은 조건이 아직 절반만 채워진 셈." (`04_stakeholder_recheck_sh-other-trainers_round3.md`)

  다른 2종(R5, R3)은 BET 로드맵 타임라인·AI 트레이너 구현 전제에 묶여 이번 스프린트 즉시 착수 불가. 개별 계정 설계만 iteration 1 DB 스키마 직선 연장선으로 즉시 착수 가능한 3종 중 1종.

- **실행 리스크 축 1 (최우선 블로커)**
  > "소속 트레이너가 3라운드 내내 drop을 유지했고, 정식 계약 50명 규모 전환 시점에 R5/R3/개별 계정 3종 실물이 없으면 사내 분위기 악화가 현실화. 키맨 본인이 초기 판단에 이미 적어둔 걱정이 그대로 살아 있음." (`report.md` 실행 리스크)

- **개선점 4 — IP 보호 vs IP 이관 양날** (3개 세션 언급, 02·04-r3)
  > "내가 퇴사해도 내 교정 패턴이 DB로 남고 후임에게 승계되는 구조 — IP 보호가 아니라 IP 이관이다." (`02_stakeholder_sh-other-trainers.md`)

  개선 방향: *"귀속 주체를 '헬스장 단독'에서 '트레이너·헬스장 공동, 퇴사 시 트레이너 본인이 export 가능'으로 설계 변경 검토."* — 이번 스프린트는 "입력자 기록 + 관장 전용 트레이너별 CSV export"로 중간 지점까지만 구현, 트레이너 본인 export는 다음 스프린트 첫 티켓으로 예약.

- **페르소나 `profile.md` current_pains + reject_triggers 매핑**
  - `sh-other-trainers.personality_notes: unknown` 상태에서도 "입력 노동 매몰비용 + 퇴사 후 IP 승계 이면"이 3라운드 내내 반복 제기된 프레임이므로, 해당 프레임의 구조적 전제인 "입력 귀속 trail 부재"를 이번 티켓이 직접 해소한다.

### 구현 스케치

**스택**: 현 iteration 1 그대로 (FastAPI + SQLite + HTMX + Jinja2, Fly.io 단일 VM). ORM 도입 금지 유지.

#### DDL 변경 (`app/db.py`)

```sql
ALTER TABLE trainers ADD COLUMN username TEXT UNIQUE;
ALTER TABLE trainers ADD COLUMN password_hash TEXT;
ALTER TABLE trainers ADD COLUMN is_owner INTEGER NOT NULL DEFAULT 0;
ALTER TABLE pt_sessions ADD COLUMN input_trainer_id INTEGER REFERENCES trainers(id);  -- NULL 허용, 구 로우 호환
```

마이그레이션은 `init_db()`가 컬럼 존재 여부를 PRAGMA `table_info`로 체크 후 `ALTER TABLE ADD COLUMN`을 idempotent 적용. 별도 버전 테이블 없음.

#### 인증 구조 (`app/auth.py`, `app/routes.py`)

- `ADMIN_USERNAME` / `ADMIN_PASSWORD` env는 **관장 시드용**으로만 사용. 부팅 시 `trainers` 테이블에 해당 username이 없으면 `is_owner=1`로 1건 자동 생성 (해시 처리된 password_hash와 함께). 이후 로그인 매칭은 **DB의 trainers 테이블**에서만.
- `verify_credentials(username, password)` → trainers 테이블에서 username 조회 + `hashlib.scrypt` 또는 `hashlib.pbkdf2_hmac` (표준 라이브러리 only, bcrypt 의존 추가 금지 — 조건 4) 비교.
- 세션 쿠키: `request.session["user"] = {"trainer_id": int, "is_owner": bool}`. 기존 `["admin"] = True`는 삭제.
- 로그인 실패 UI는 현 iteration 1과 동일 (unified 에러 메시지, rate limit 없음 — spec 유지).

#### 세션 기록에 입력자 귀속

- `POST /trainers/:tid/members/:mid/log`: `request.session["user"]["trainer_id"]`를 `pt_sessions.input_trainer_id`에 기록.
- 기본 대시보드 그래프에는 영향 없음. 세션 목록 뷰 / 세션 상세가 있다면 "입력: {trainer.name}" 한 줄 표시.

#### 트레이너 계정 생성 (seed 스크립트 only)

- 기존 `scripts/seed.py` 확장 혹은 신규 `scripts/seed_trainer.py`: `uv run python -m scripts.seed_trainer --name X --username u --password p [--owner]`. 해싱은 스크립트 내부.
- 웹 UI 계정 CRUD 금지 — `docs/spec.md`의 "회원 CRUD 웹 UI (seed 스크립트 only)" 원칙을 계정 CRUD에도 동일 적용.

#### 관장 전용 CSV export

- `GET /admin/export/sessions.csv?trainer_id=<int>` (trainer_id 쿼리 파라미터 optional).
- auth 검사: `session["user"]["is_owner"] == True`가 아니면 303 → `/`.
- 응답: `text/csv`. 컬럼 = `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`.
- `trainer_id` 쿼리 파라미터 있으면 `pt_sessions.input_trainer_id == trainer_id`만 export.
- 최소 감사 흔적: 요청마다 `stdout`에 `[export] owner_id=X target_trainer_id=Y rows=N` 로그 출력 (조건 5).
- 심플 rate limit: 같은 세션에서 60초 내 2회 이상 요청 시 429 (조건 5).
- 트레이너 본인의 "내 입력분 export" 기능은 이번 스프린트 외 — **다음 스프린트 첫 티켓으로 예약** (조건 6).

#### 백필 스크립트 (`scripts/backfill_input_trainer.py`)

- 기존 `pt_sessions` 로우 중 `input_trainer_id IS NULL`인 것을 관장 계정의 trainer_id로 UPDATE 일회 실행.
- Fly.io 환경에서 `fly ssh console` 후 `uv run python -m scripts.backfill_input_trainer` 실행 (조건 3, `docs/user-intervention.md`에 운영 절차 추가).

#### 테스트 (`docs/testing.md` 준수 — mock 금지, tmp_path SQLite)

- `tests/test_auth.py` 확장: env 어드민 부팅 시드 검증 + DB 트레이너 로그인 + owner vs non-owner 권한 분기.
- `tests/test_log_routes.py` 확장: 로그인한 trainer_id가 `pt_sessions.input_trainer_id`에 기록되는지 검증.
- 신규 `tests/test_export.py`: CSV export 권한(owner only) + `trainer_id` 필터링 + rate limit 동작 + stdout 감사 로그 출력 검증.
- Playwright e2e는 이번 스프린트 scope 외 (iteration 1 대시보드 스크린샷 AC는 이미 달성됨).

#### 인간 개입 지점

- 트레이너 계정 생성·비밀번호 리셋: 관장이 서버 콘솔에서 `uv run python -m scripts.seed_trainer ...` 실행. Fly.io는 `fly ssh console`. 웹 UI 없음.
- 관장 교체 시나리오: `UPDATE trainers SET is_owner=0` 후 다른 계정에 `is_owner=1` 부여. `fly ssh` + `sqlite3` CLI로 직접. 운영 절차를 `docs/user-intervention.md`에 1줄 명시 (조건 2).
- CSV export 다운로드: 관장이 브라우저로 직접 수행.
- 백필 스크립트 최초 실행: 관장이 `fly ssh console`에서 수동 실행 (조건 3).

### CTO 승인 조건부 조건

`tech-critic-lead` 결재에서 **승인 / 신뢰도 72**로 통과. 부과된 6개 조건:

1. **`docs/spec.md` 선(先) 개정**: "명시적 제외 항목"의 "다중 트레이너 / 다중 헬스장" 및 "권한 분리 / 다중 유저" 조항을 iteration 2 전에 개정. iteration 2는 "**단일 헬스장 내 다중 트레이너 로그인 + 관장(is_owner) 단일 권한 분기**"까지만 허용하고, 다중 헬스장 / 복잡 RBAC는 여전히 금지로 명시. spec 개정 없이 구현 진입 금지 (문서-코드 드리프트 방지).

2. **관장 교체 운영 절차를 `docs/user-intervention.md`에 기재**: 짧은 주석 1줄로 `UPDATE trainers SET is_owner=0/1 WHERE ...` SQL 예시를 `fly ssh console`에서 실행하는 절차 명시. 웹 UI 만들지 말 것.

3. **백필 스크립트 동봉 필수**: `pt_sessions.input_trainer_id` NULL 허용은 유지하되, 기존 row를 관장 계정 trainer_id로 일회 UPDATE하는 `scripts/backfill_input_trainer.py` 필수 작성. NULL 상태 영속화는 퇴사 시 IP export 논리를 깨뜨린다.

4. **bcrypt 의존 추가 금지, 표준 라이브러리 우선**: `hashlib.scrypt` 또는 `hashlib.pbkdf2_hmac`로 해싱. passlib/bcrypt 추가는 CI·Docker 이미지 비대화 리스크가 있어 관장 1명 + 트레이너 5~10명 규모에 부적절. 표준 라이브러리로 충분. 외부 의존 추가가 꼭 필요하다고 판단되면 pyproject.toml 변경 + Dockerfile 빌드 테스트 CI 통과 후에만 머지.

5. **CSV export 최소 감사 흔적**: 심플 rate limit (같은 세션에서 60초 내 2회 이상 요청 거부) 혹은 최소한 접근 로그 stdout 출력 추가. `docs/spec.md`는 brute-force 방지 제외지만 CSV는 IP 자산 유출 경로 → 최소 감사 흔적 필수.

6. **트레이너 본인 export는 다음 스프린트 첫 티켓으로 예약 명시**: 관장 export만 있는 상태는 중간 산출물이며 stakeholder가 "결국 관장이 임의로 뺀다"로 해석 가능. 이번 티켓 본문에 "다음 스프린트 첫 티켓: 트레이너 본인의 '내 입력분 CSV export' 라우트" 예약 문구를 못박아 둘 것.

### 검토한 더 싼 대안들 (CTO에 함께 제출·기각)

1. ~~`pt_sessions.input_trainer_name TEXT` 자유입력 필드만 추가, 로그인 분리 없이 드롭다운~~
   → "관장이 내 이름으로 덮어쓰기" 우려 해소 못함. stakeholder 70선 돌파 조건은 위변조 불가능한 "설계 초안"이며 자유입력은 초안이 아님.

2. ~~전체 CSV export만 추가하고 트레이너 필터 생략~~
   → "퇴사 시 내 입력분 분리" 우려를 관장 엑셀 필터링에 의존시키는 구조 → stakeholder가 요구한 "트레이너 본인이 export 가능" 개선 방향과 정반대.

3. ~~R5 가드레일(집계 API의 trainer_id 필드 차단)만 만들기~~
   → 현 iteration 1은 "관장 집계 뷰" 자체가 없어 차단할 대상이 존재하지 않음. 트레이너 귀속 필드가 먼저 존재해야 "차단"이라는 개념 성립.

4. ~~protocols 오버라이드 매트릭스 (개선점 2)~~
   → AI 트레이너 기능 자체가 이번 스프린트 범위 밖 → 전제부터 부재. "오버라이드할 기본 프로토콜"이 없는 상태에서 매트릭스만 만드는 것은 앞길.

### 다음 스프린트 예약 티켓 (CTO 조건 6에 따라 명문화)

- **트레이너 본인의 "내 입력분 CSV export" 라우트**: `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 `input_trainer_id`만 필터링하여 다운로드. 관장 허가 불요. 이 기능이 붙어야 시뮬 개선점 4("트레이너·헬스장 공동 소유, 퇴사 시 트레이너 본인이 export 가능")의 해소가 완성된다.
