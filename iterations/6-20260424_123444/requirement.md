# Requirement

## 가치제안

# BET (Best Training) — PT 트레이너·헬스장 관장용 가치제안 (iteration 6 기준)

> 전달 모드: landing_plus_meeting
> 배포 상태: **MVP v5 라이브** (iteration 1 + 2 + 3 + 5 배포 완료). iteration 5에서 **R5 부분 구현 — 트레이너간 회원 접근 서버사이드 격리**가 라이브로 붙음. 직전 시뮬(104537)의 stakeholder 1순위 블로커(6/8 세션 언급, "트레이너 비교지표 도구화 구조적 차단 부재")가 서버 사이드 차원에서 해소됨.
> 대상: 중소 동네 헬스장 관장 겸 트레이너 (회원 ~50명 규모)
> 기존 도구: Rappo 병행 사용 전제

---

## 0. 이번 미팅의 맥락

지난 미팅에서 합의한 12주 무료 파일럿의 **9주차 진입 시점** 기준 후속 미팅입니다.

- 8주차 미팅에서 관장·stakeholder(소속 트레이너) **양측 1순위 일치**로 확정된 **R5 부분 구현**이 9주차 첫날 live로 붙었습니다. `require_member_access` 미들웨어 + `GET /` 본인 회원 redirect + 4개 라우트 서버사이드 403 가드 + 11개 테스트 green. PR 본문에 "마이그레이션 불요 — `members.trainer_id`가 iter 1부터 owner FK로 기 작동" 명시, 의사록에도 동일 근거 적시.
- stakeholder가 명시한 "70 돌파 5개 조건" 중 유일한 기술 건 이행 완료. 나머지 4개(의사록 서명본·계약서 공동 서명란·R3 post-contract 거부권 명문화·BET CC 실수신)는 문서/절차 영역으로 관장·BET 간 합의서 초안으로 병행 이행 중.
- 이번 미팅의 목적은 **남은 4주 동안 붙일 다음 기능 1개**를 관장님 + 소속 트레이너 피드백으로 정하는 것. 후보는 지난 로드맵의 N0/R1/R2/R3/R4/R5-full/R6/R7/R8/R9.

---

## 1. 랜딩페이지 카피

### 한 줄 소개

**BET — PT의 "보이지 않는 성장"을 눈에 보이게 만드는 AI 트레이너**

### 서브 카피

- 인바디 수치 한 장으로 끝나던 회원 성과를, 세션 단위로 누적되는 꺾은선 그래프로 잠재회원에게 증명하세요.
- 회원의 PT 외 6일 24시간을 AI 트레이너가 관리합니다. 생활습관 데이터가 쌓일수록 트레이너의 피드백은 더 날카로워집니다. *(AI 트레이너 카카오톡 채널은 R3 로드맵, 현재 대시보드는 세션 중량/볼륨 2축만 제공)*
- 헬스장 단위 월 구독. 회원 1인당 월 9,900원부터. (헬스장이 패키지화해서 회원에게 전가하는 것도 가능)

### 핵심 한 줄

> "PT 품질의 증거를, 트레이너가 아닌 데이터가 말하게 합니다."

### 랜딩 CTA

- "[무료] 3개월 파일럿 신청" → 12주 간 3개 회원 계정 무료 제공, 이후 성과 확인 후 정식 계약. **현재 9주차 진행 중**.

---

## 2. 해결하려는 문제 (Pain Statement)

### 트레이너·관장 관점

1. **"우리 PT 좋아요"를 증명할 자료가 빈약함.** 상담 테이블에서 인바디 수치 하나만으로 설득.
2. **회원 발전 추이 가시화 부재.** Rappo 등 기존 도구에 없는 기능.
3. **PT 외 6일 방치.** 주 1회 PT만으로 결과를 책임지는 구조적 한계.
4. **리텐션 고민.** 3개월 이탈 패턴.
5. **트레이너 IP 소유권 + 감시 투명성** — iteration 3(본인 CSV export) + iteration 5(서버사이드 접근 격리) live로 1·2차 완화. 단 "관장이 언제 내 입력분을 export 했는가" 능동 조회(N0)는 아직 미live.

### 회원(downstream) 관점

1. PT 받는 날만 운동, 나머지 6일 무방비.
2. 발전 여부 애매, 인바디 외 피드백 산발.
3. 트레이너 이직 시 운동 히스토리 증발.

---

## 3. 현재 동작하는 것 (iteration 1, 2, 3, 5 라이브)

관장·트레이너가 지금 URL 열어서 쓸 수 있는 기능.

### A. 세션 기록 입력 (`/trainers/:tid/members/:mid/log`)

- 세트 단위 `운동 / 중량(kg) / 횟수` 입력. HTMX "세트 행 추가" 버튼.
- 운동 종목 10종 고정: 스쿼트 / 벤치프레스 / 데드리프트 / 오버헤드프레스 / 바벨로우 / 풀업 / 레그프레스 / 랫풀다운 / 레그컬 / 덤벨컬.
- 저장 시 로그인한 트레이너의 ID가 `input_trainer_id`로 함께 기록 → 퇴사 후 "누가 입력했는가" 영구 trail.

### B. 회원별 진행 대시보드 (`/trainers/:tid/members/:mid/dashboard`)

- 꺾은선 그래프 2개: **운동 종목별 최대 중량 추이** + **세션당 총 볼륨 추이**(Σ중량×횟수).
- 실제 수행한 종목만 선으로. 세션 0건 회원은 빈 그래프.

### C. 다중 트레이너 로그인 + 관장 권한 분기

- 소속 트레이너마다 개별 `username`/`password` 계정.
- 관장(`is_owner=1`) 1명만 존재. `is_owner=1`만 `/admin/export/sessions.csv` 접근.
- 계정 CRUD는 웹 UI 없음 — `scripts.seed_trainer` CLI(관장이 서버 콘솔 수행).
- 비밀번호 해싱: `hashlib.scrypt` 표준라이브러리만.

### D. 관장 전용 CSV export

- `GET /admin/export/sessions.csv[?trainer_id=<id>]`. 전체 또는 특정 트레이너 필터.
- 컬럼: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`. UTF-8 BOM.
- 60초 rate limit + stdout 감사 로그.

### E. 트레이너 본인 CSV export — `GET /my/export/sessions.csv`

- 로그인만 필요. `is_owner` 체크 없음. 관장도 본인 자격 한정.
- 필터 고정: `pt_sessions.input_trainer_id = session_trainer_id`. 쿼리 파라미터 없음.
- 관장 export와 **bit-exact 동일 컬럼**(공통 헬퍼 `_write_sessions_csv`). UTF-8 BOM.
- 별도 rate limit dict + `[my-export]` prefix 감사 로그.

### F. **(iteration 5) R5 부분 구현 — 트레이너간 회원 접근 서버사이드 격리**

- **가드**: `require_member_access(request, conn, mid) -> (ok, status_code)` 헬퍼가 4개 라우트(GET/POST `/log`, `/chart-data.json`, `/dashboard`) 진입 최전방에서 호출.
  - 미로그인 → 303 `/login`.
  - 회원 부존재(`mid` 없음) → **404** HTMLResponse.
  - 회원 존재 + 타 트레이너 소유 + 비관장 → **403** PlainTextResponse `"forbidden"`. (존재 여부 은폐 안 함 — 감사 가시성 목적)
  - URL의 `tid`가 `members.trainer_id`와 불일치 → **404** (관장 포함, URL 위조 방지).
  - 관장(`is_owner=1`) + URL `tid` 일치 → bypass로 전체 접근.
- **`GET /` redirect**:
  - 비관장 로그인 → 본인 소유 첫 회원(`trainers` table 결과)으로 303 redirect (타 트레이너 회원 ID 유출 차단).
  - 관장 로그인 → 기존 동작 (DB 첫 트레이너 + 첫 회원).
  - 비관장 + 본인 회원 0건 → 200 안내 페이지(`담당 회원이 아직 없습니다. 관장에게 요청하세요.`).
- **DB 마이그레이션 불요** — `members.trainer_id`가 iter 1부터 owner FK로 기 작동.
- **의미**: 직전 시뮬 1순위 블로커(6/8 세션 언급) "트레이너 비교지표 도구화 구조적 차단 부재"가 서버 사이드 차원에서 해소. URL 직접 입력으로 타 트레이너 회원 데이터 조회하던 permissive 동작이 구조적으로 차단됨.

### G. 인프라 (최소)

- Fly.io 단일 VM (region `nrt`) + 1GB 영속 볼륨 SQLite.
- 관측은 stdout + Fly 기본 로그만. 외부 관측 의존 없음.

### H. 현 시점의 명시적 한계

아래는 **아직 없음**. 이번 미팅에서 우선순위 피드백이 필요합니다.

- **N0 트레이너 본인 감사 로그 뷰어 — `GET /my/audit-log` 미live.** "관장이 언제 내 입력분을 export 했는가"를 트레이너가 앱 안에서 능동 조회 불가. 현재 `[export]` / `[my-export]` stdout 로그는 트레이너가 직접 볼 수 없음.
- **R5-full 미live** — 회원 자가 대시보드 + 관장 "트레이너별 평균치 비교 UI" 비가시화 구조. 현재 "비교 UI 부재"로 satisfy된 상태이나, 관장이 `?trainer_id=` 쿼리로 트레이너별 CSV를 뽑아 외부에서 비교하는 것은 여전히 가능.
- **자세 교정 기록 / 컨디션·수면·식단 자가보고 / 인바디 연동 — 볼륨 외 지표 없음.**
- **AI 트레이너 카카오톡 채널 — PT 외 6일 코칭 기능 없음.**
- **PDF 12주 성장 리포트 — 상담장에서 인쇄물로 배포 불가.**
- **Rappo CSV/API 연동 — 회원 명단은 seed 스크립트로 BET 측이 수동 주입.**
- **회원용 UI — 회원은 자기 대시보드 직접 접근 불가.**
- **트레이너 프로토콜/태그 구조 이관 무대응** — `/my/export`가 원시 세트만 내려주고, 설계한 프로토콜·태그는 못 가져감.
- **10종 고정 운동 한계** — 코어·컨디셔닝·기능성 세션 기록 구조 진입 불가.
- **ROI 증거 계측 부재** — 상담 전환율/리텐션 변화를 숫자로 환원할 수단 없음.
- **다중 헬스장** — 단일 헬스장 전제 유지.

---

## 4. 파일럿 잔여 4주 로드맵 (우선순위 미확정 — 오늘 함께 정할 것)

아래 후보 중 **한 번에 1개씩** 붙일 계획. 다음 1순위를 오늘 확정합니다.

### N0. 트레이너 본인 감사 로그 뷰어 — `GET /my/audit-log`

- 트레이너가 "누가 언제 내 입력분을 export 했는가"를 앱 안에서 능동 조회.
- **가치**: 직전 시뮬 stakeholder 2순위 우려(감시 비대칭 — 감시 메커니즘은 live, 방어장치는 roadmap인 비대칭) 해소. R5 부분 구현의 "동일 축 보완".
- **구현 스케치**: `export_audit(id, created_at, actor_trainer_id, action TEXT, target_trainer_id INTEGER NULL, rows INTEGER)` 테이블 신규 + 관장/본인 export 시 1 row INSERT + `GET /my/audit-log` 페이지에서 본인 actor/target row 100건 표시.

### R5-full. 회원 자가 대시보드 + 관장 비교 UI 비가시화 구조

- 회원 자가 로그인 + 자기 대시보드 접근. 관장 대시보드에서 "트레이너별 평균치 비교" UI 구조적 비가시화.
- **가치**: R5 부분 구현에서 남긴 "UI 레이어 차단" 축 마무리. stakeholder 원안(04_round2) 요구.
- **구현 스케치**: `members.member_login_token`(일회성 URL 토큰) + `/m/<token>/dashboard` + 관장 대시보드에 비교 UI 도입 게이트(현재 UI 부재 상태 유지가 satisfy 조건이므로 게이트 문구만 명문화).

### R1. PDF "12주 성장 리포트" 출력

- 대시보드 화면을 A4 1~2장 PDF로 내려받기. 상담 테이블에 올릴 인쇄물.
- 그래프 + 회원 이름 + 기간 요약 + 트레이너 서명란.
- **가치**: 파일럿 DoD 약속의 이행 + 잠재회원 상담 자료 물리화. **keyman 본인 1순위 buy_trigger.**
- **구현 스케치**: `weasyprint` 서버사이드 렌더 → `/trainers/:tid/members/:mid/report.pdf`. Chart.js HTML을 A4로 구움.

### R2. 컨디션·수면·식단 자가보고 (회원용 최소 UI)

- 회원 하루 1회 30초 체크리스트. 토큰 링크 또는 간소 웹 UI.
- 대시보드에 "생활습관 일관성 점수" 1개 추가 → 중량/볼륨과 중첩.
- **가치**: pain 3(PT 외 6일 방치) 1단계 해소 + "다차원 그래프" 카피의 실기능 gap 해소.

### R3. AI 트레이너 카카오톡 채널 (MVP)

- 회원이 채널에 식단 사진·컨디션·자가영상 전송 → AI가 당일 가벼운 피드백.
- **가치**: pain 3 본격 해소 + BET 핵심 차별화.
- **리스크**: "트레이너 시간 프리미엄 희석" stakeholder 우려. "post-contract 거부권 명문화" 선결 조건.

### R4. Rappo 연동 (CSV import 우선)

- 관장이 Rappo에서 회원 CSV 내보내기 → BET 관리화면 업로드 → 동기화.
- **가치**: 이중 운영 부담 reject_trigger 직접 해소.
- **구현 스케치**: `GET/POST /admin/import/members.csv`. `members` 테이블 upsert.

### R6. 자세 교정 태그 (트레이너용 quick action)

- 세션 입력 폼 옆 "교정 포인트" 태그 3~5개 선택 가능.
- 대시보드에 "교정 빈도 감소 추이" 1줄 추가.
- **가치**: "자세 교정은 대체 불가" 포지션 강화 + 트레이너 노하우 데이터화.

### R7. 트레이너 프로토콜/태그 이관 번들 export

- `/my/export/protocol.json` — 트레이너 본인이 설계한 프로토콜·태그·노트 구조를 JSON 번들로 자가 export.
- **가치**: 직전 시뮬 "퇴사 시 프로토콜 이관 무대응" 해소.
- **제약**: R6(자세 교정 태그) 선행 필수 (export할 구조가 없음).

### R8. 운동 종목 확장 — 11~15종 추가 (코어·컨디셔닝 커버)

- 현재 10종 고정 → 15~20종으로 확장. 코어(플랭크·크런치), 컨디셔닝(버피·마운틴클라이머), 기능성 포함.
- **가치**: 직전 시뮬 4순위 "세션 입력 UX 부담 + 10종 고정이 Rappo 대비 즉시 열위" 해소.
- **구현 스케치**: `exercises.py`의 `ALLOWED_EXERCISES` 상수 확장 + CHECK 제약 재적용 idempotent 마이그레이션.

### R9. 상담 전환율·리텐션 지표 관장 대시보드 (ROI 증거 계측)

- 관장 전용 `/admin/roi-dashboard` — 회원 등록 후 PT 지속 기간, 상담→계약 전환율(수동 입력) 추이 시각화.
- **가치**: 직전 시뮬 7순위 "ROI 증거 부재로 가격 상한 상향 조정 근거 無" 해소. 가격 탄력성 확보.
- **제약**: "상담 전환율" 원천 데이터 현재 無 → 월 1회 수동 입력 UI 필요.

---

## 5. 가격 플랜 (세일즈 미팅 단계에서만 공개)

- **파일럿 (12주)**: 무료. 회원 3명까지. **현재 9주차**.
- **스탠다드**: **회원 1인당 월 9,900원**. 최소 10명부터.
- **엔터프라이즈** (50명 이상): 월 인당 8,000원.
- **연 일시불 결제 시 10% 할인.**
- 회원 요금 전가(패키지화/무료 제공)는 헬스장 자율. BET은 헬스장에만 청구.

---

## 6. 자주 받는 질문 (세일즈 미팅용 FAQ)

### Q1. Rappo를 해지해야 하나요?

아니요. 캘린더·운영관리는 Rappo 유지. R4가 붙으면 회원 명단은 자동 동기화.

### Q2. 회원이 앱 설치·매일 기록을 귀찮아하면요?

**현 시점에서 회원은 아무것도 설치/입력하지 않습니다** — 대시보드는 관장님/트레이너가 대면으로 보여주는 용도. R2/R3가 붙는 시점에도 카카오톡 채널·토큰 링크로 동작(앱 설치 불요).

### Q3. 소속 트레이너들이 "내 방식대로 못 한다"며 반대하면요?

- iteration 2 **트레이너별 개별 로그인 + 입력자 귀속** trail.
- iteration 3 **트레이너 본인이 본인 입력분 CSV export**(`/my/export/sessions.csv`) live.
- iteration 5 **트레이너간 회원 접근 서버사이드 격리**(403 가드 + `GET /` 본인 첫 회원 redirect) live → URL 직접 입력으로 타 트레이너 회원 데이터 조회 구조적 차단.
- 미해결: "관장이 언제 내 입력분을 export 했는가" 능동 조회(N0)는 아직 미live. 이번 미팅 후보 1순위 중 하나.

### Q4. 데이터가 우리 회원 데이터인가, BET 데이터인가?

헬스장 소유. **개별 트레이너 본인의 입력분에 한해서는 트레이너도 export 권한 보유**. 계약 해지 시 전체 CSV/PDF 내보내기 제공. BET은 익명화 집계 데이터만 제품 개선에 활용.

### Q5. 트레이너 비교지표 도구화가 우려됩니다.

iteration 5에서 **서버 사이드 접근 격리**가 라이브로 붙어, 관장이 대시보드 UI 레벨에서 트레이너별 평균치를 비교하는 기능은 구조적으로 부재합니다. 단 관장이 `?trainer_id=` 쿼리로 트레이너별 CSV를 뽑아 외부(Excel 등)에서 비교하는 것은 여전히 가능 — **R5-full**(회원 자가 대시보드 + 관장 UI 비가시화 구조)로 해당 축을 마무리할 예정.

### Q6. 트레이너가 퇴사하면 쌓인 프로토콜은?

**현재는 세트 원시 데이터만** `/my/export`로 가져갈 수 있습니다. 트레이너가 설계한 프로토콜·태그·메모 구조 이관은 **R7 후보**로 남아있습니다. R6(태그 도입) 선행 조건.

### Q7. 운동 종목이 10종밖에 없어서 기록 못 하는 커리큘럼이 많습니다.

**현재 10종 고정**(스쿼트·벤치·데드·OHP·바벨로우·풀업·레그프레스·랫풀다운·레그컬·덤벨컬). **R8 후보**로 15~20종 확장이 올라가 있습니다. 관장님 실제 커리큘럼에서 빠져서 가장 아쉬운 종목을 알려주시면 R8 범위에 우선 반영하겠습니다.

### Q8. 파일럿 9주차 — ROI는 얼마나 잡혔습니까?

현재 BET이 자체 계측하는 ROI 지표는 없습니다. 관장님이 상담 테이블에서 대시보드를 얼마나 활용하셨고, 상담→계약 전환이 어떻게 움직였는지는 **관장님 체감**에만 의존. **R9 후보**(관장용 ROI 대시보드)가 이 공백을 메우는 자리입니다.

---

## 7. 오늘 미팅의 구체적 요청

관장님께 다음 3개 질문을 드립니다:

1. **R5 부분 구현 실사용 피드백** — 9주차 첫날 live 후 소속 트레이너들이 실제로 URL 직접 입력으로 타 트레이너 회원 조회를 시도해봤는지(403 반응 체감), `GET /` redirect가 본인 첫 회원으로 바뀐 것이 일상 워크플로우에 불편한지, "forbidden" 평문 문구가 감시 가시성 목적으로 납득되는지.
2. **남은 4주 1순위 기능** — N0 감사 로그 / R5-full / R1 PDF / R2 자가보고 / R3 AI 채널 / R4 Rappo / R6 태그 / R7 프로토콜이관 / R8 종목확장 / R9 ROI대시보드 중 가장 먼저 붙이고 싶은 1개 + 선택 이유.
3. **직전 미팅에서 미해소된 우려 재점검** — (a) 감시 비대칭(N0 미live), (b) R5-full 미live로 관장이 CSV 외부 비교 여지 잔존, (c) R3 AI 트레이너의 프리미엄 희석, (d) 프로토콜 이관 미대응, (e) 10종 고정 한계, (f) ROI 증거 부재 — 이 중 여전히 심각하다고 느끼시는 항목은?

---

## 8. BET이 약속하지 않는 것 (리스크 솔직 고지)

- 인바디 수치의 **단기** 개선을 약속하지 않음. AI가 하는 건 "생활습관 일관성"이지 "빠른 결과"가 아님.
- 트레이너의 자세 교정을 대체하지 않음. BET은 그 시간을 확보해 주는 도구.
- 헬스장 매출을 직접 올리는 마케팅 도구 아님. "상담 전환율"을 올릴 자료를 제공하는 도구.
- 현 시점의 대시보드는 **세션 중량/볼륨만**을 보여줌. 다차원 그래프는 R2 이후에 가능.
- 트레이너간 회원 접근 격리는 **서버 사이드만 완성**. UI 레이어 비가시화 + 회원 자가 대시보드는 R5-full에서만.
- 감사 로그 능동 조회는 **N0**에서만 완성됨. 그 전까지는 stdout 로그만 존재 (트레이너 본인은 직접 볼 수 없음).
- 프로토콜/태그 이관은 **R6+R7**에서만 완성됨.
- 10종 고정 운동은 **R8**에서만 확장됨.
- ROI 증거(상담 전환·리텐션 숫자)는 **R9**에서만 계측됨.

## 채택된 요구사항

- **run_id**: `pt-trainer-owner-01_20260424_123444`
- **title**: **N0 — 트레이너 본인 감사 로그 뷰어** (`GET /my/audit-log` + `export_audit` 테이블 + 관장/본인 export 성공 시 1 row INSERT)

### 유래한 고객 pain + 근거 인용

유래한 페르소나: `pt-trainer-owner-01` (동네 소규모 헬스장 관장 겸 트레이너, 소속 트레이너 2~3명, PT 회원 ~50명). 영향 stakeholder: `sh-other-trainers` (소속 트레이너, influence 40, 거부권 성격).

시뮬 최종 판정: **성사 (조건부 패키지 accept) / 실행 리스크 낮음**. sh-other-trainers가 round 1에서 **drop@42 → accept@74**로 전환된 근간이 keyman의 5개 커밋 패키지이며, **N0 1순위 확정**이 그 패키지의 1번 카드.

#### 해소하는 pain (`persuasion-data/runs/pt-trainer-owner-01_20260424_123444/*.md` 직접 인용)

- **stakeholder 초기 drop 사유 상위 2대 축 중 하나** (`02_stakeholder_sh-other-trainers.md` 20~21행)
  > "N0 미live가 감시 비대칭을 그대로 남긴다 (-) — §3.H와 §6 Q3가 솔직히 고지한다: 관장의 `?trainer_id=` export는 `[export]` stdout 로그로만 남고, **트레이너 본인은 그 로그를 앱 안에서 볼 수 없다**. 관장이 언제 내 데이터를 뽑았는지를 내가 능동 조회할 수단이 0이다. 이번 4주에 1개만 붙는데, 키맨이 R1(본인 buy_trigger: PDF)을 1순위로 밀고 있다는 신호가 보이면 N0는 12주차 안에 안 붙는다. 파일럿이 정식 계약으로 전환되는 시점까지 방어장치가 없는 상태가 고착된다."

- **stakeholder 70 돌파 조건 (a) 단독 명시 항목** (`02_stakeholder_sh-other-trainers.md` 49행)
  > "관장이 내 confidence를 70 위로 올리려면 다음 중 최소 2개를 묶어야 한다: **(a) 남은 4주 1순위를 N0로 확정**, (b) R5-full을 N0 다음 순위로 문서 명시(관장이 스스로 CSV 외부비교 경로를 닫겠다는 합의), (c) R3 post-contract 거부권 서명본을 이번 미팅 전까지 교환."

- **keyman 5개 커밋 패키지의 1번 카드** (`report.md` 23행)
  > "stakeholder가 본문 말미에 적어둔 '70 돌파 2개 조건'에 정확히 1:1로 매칭한 5개 커밋 패키지(**N0 1순위 확정** / R5-full 합의서 명문화 / R3 서명본 교환 조건 / 실물 자료 / 계정 CRUD 보호) 제시."

- **accept 전환 조건부 찬성의 트리거** (`report.md` 16행)
  > "성사 형태는 **조건부 패키지 accept**다. 키맨이 본인 1순위 buy_trigger였던 R1 PDF를 12주차 이후로 자진 후순위화하고, R5-full 합의서 명문화, R3 post-contract 거부권 서명본, 실물 확인 자료, 계정 CRUD 보호조항 5개를 한 묶음으로 커밋한 대가로 stakeholder의 거부권 발동을 회피했다. stakeholder는 명시적으로 '5개 중 하나라도 미팅 밖으로 밀리면 confidence가 70 아래로 떨어진다'는 조건부 찬성 선을 남겼다."

- **spec.md 다음 스프린트 예약 티켓으로 이미 문서화** (`docs/spec.md` 136행)
  > "트레이너 본인 감사 로그 뷰어 — `GET /my/audit-log` — 트레이너가 '누가 언제 내 입력분을 export 했는가'를 능동 조회하는 페이지. … DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다."

즉 이번 티켓은 (i) stakeholder drop → accept 전환을 가른 5개 커밋 패키지의 **1번 카드**, (ii) stakeholder 70 돌파 조건 (a) 단독 명시 항목, (iii) spec.md 다음 스프린트 예약 티켓으로 이미 문서화(상상이 아닌 대기 티켓), (iv) iteration 5 R5 부분 구현이 완성한 "관장 측 경로 차단"과 대칭축으로 "트레이너 측 능동 확인"을 붙이는 동일 축 보완, (v) 구현 비용은 테이블 1개 + INSERT 2곳 + 라우트 1개 + 테스트 8개로 iter 5 R5 부분과 동급의 MVP slice. 인간 개입 0.

### 구현 스케치

**스택**: 현 iteration 1~5 그대로 (FastAPI + SQLite + HTMX + Jinja2, Fly.io 단일 VM, `sqlite3` 표준 라이브러리 only). ORM 도입 금지 유지. 외부 의존 추가 0.

#### 1. DB 마이그레이션 (`app/db.py` `init_db()` idempotent)

```sql
CREATE TABLE IF NOT EXISTS export_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,                  -- ISO8601 UTC
  action TEXT NOT NULL CHECK(action IN ('owner_export', 'my_export')),
  actor_trainer_id INTEGER NOT NULL REFERENCES trainers(id),
  target_trainer_id INTEGER REFERENCES trainers(id),  -- NULL = owner가 전체 대상으로 뽑음
  rows INTEGER NOT NULL
);
```

`init_db()`에 `CREATE TABLE IF NOT EXISTS` 1 블록 추가. ADD COLUMN 없음. 최초 배포 시 자동 생성.

#### 2. INSERT 트리거 (`app/routes.py` 기존 2개 export 라우트 수정)

- **`/admin/export/sessions.csv` 성공 응답 직전**: 1 row INSERT
  - `action='owner_export'`, `actor_trainer_id=session.user.trainer_id`
  - `target_trainer_id = trainer_id 쿼리 값(있으면) or NULL(없으면)`
  - `rows = _write_sessions_csv 반환값` (header 제외, data row 수)
- **`/my/export/sessions.csv` 성공 응답 직전**: 1 row INSERT
  - `action='my_export'`, `actor_trainer_id = target_trainer_id = session.user.trainer_id`
  - `rows = _write_sessions_csv 반환값`

stdout `[export]` / `[my-export]` 로그는 **유지** (관측 루트 다양성 — Fly.io 재시작 외 즉시 확인 경로로 필요, **CTO 조건 2**).

#### 3. 신규 라우트 `GET /my/audit-log`

- **auth**: `is_authenticated(request) == True`만 확인. is_owner 체크 없음 — 관장도 본인 자격으로 접근.
- **쿼리**:
  ```sql
  SELECT ea.id, ea.created_at, ea.action, ea.target_trainer_id, ea.rows,
         actor.name AS actor_name, target.name AS target_name
  FROM export_audit ea
  JOIN trainers actor ON ea.actor_trainer_id = actor.id
  LEFT JOIN trainers target ON ea.target_trainer_id = target.id
  WHERE ea.target_trainer_id = :self_tid
     OR ea.actor_trainer_id = :self_tid
     OR (ea.action = 'owner_export' AND ea.target_trainer_id IS NULL)
  ORDER BY ea.id DESC
  LIMIT 100;
  ```
  - 본인 target row + 본인 actor row + owner의 전체 대상 export(target NULL → 본인 포함 간주) row를 포함.
  - 페이지네이션·필터·CSV export **금지** (CTO 조건 1). `MY_AUDIT_LOG_LIMIT = 100` 상수만 유지.
- **응답**: Jinja2 템플릿 `templates/my_audit_log.html`. 표 컬럼: `일시 / 행위 / 호출자 / 대상 / rows`. `action='owner_export' AND target IS NULL` → "전체 대상(본인 포함)" 표기.
- **본인 조회는 감사 대상 아님** (조회 자체는 stdout/DB 로그 남기지 않음).

#### 4. 테스트 (`tests/test_my_audit_log.py` 신규, mock 금지, tmp_path SQLite)

1. 관장 `/admin/export?trainer_id=X` → `export_audit` row 1건 INSERT 검증 (action='owner_export', actor=owner_tid, target=X, rows=실데이터 수).
2. 관장 `/admin/export` (trainer_id 쿼리 없음) → row 1건 INSERT with target=NULL.
3. 트레이너 `/my/export` → row 1건 INSERT with action='my_export', actor=target=본인_tid.
4. **본인 로그인 → `/my/audit-log` → 본인 target row + 본인 actor row + target=NULL owner_export row 포함, 타 트레이너만 target/actor인 row 미포함** (**CTO 조건 4 — WHERE 절 회귀 방지**).
5. 미로그인 → `/my/audit-log` → 303 /login.
6. 관장 로그인 → `/my/audit-log` → 관장 본인의 owner_export + 관장이 `?trainer_id=<owner_self>`로 직접 target 지정해 뽑은 row 모두 포함 (**CTO 조건 6**).
7. 100건 초과 시 최신 100건만 반환 (`LIMIT` 검증).
8. **rows 컬럼 정확성**: `export_audit.rows` 값이 `_write_sessions_csv` 반환값(header 제외 data row 수)과 일치 (**CTO 조건 5**).

#### 5. 문서 수정 (CTO 조건 3)

- `docs/spec.md`:
  - "라우트 목록"에 `GET /my/audit-log` 추가 (line 38-39 부근).
  - "CSV Export" 섹션(line 74-97)에 `export_audit INSERT` 부수효과 각 라우트별로 명시.
  - **"다음 스프린트 예약 티켓" 섹션의 N0 라인 삭제** (line 136 — live 이행).
  - "R5-full" 예약 티켓은 유지.
- `docs/testing.md`: `tests/test_my_audit_log.py` 신규 8 시나리오 요약 추가 (기존 파일 8번째 항목으로).
- `docs/user-intervention.md`: **변경 없음** (env 추가 없음, 마이그레이션 자동).

#### 6. 인간 개입 지점

**없음**. `fly deploy`만 관장 실행 (기존 절차). env 추가 없음. 최초 배포 시 `init_db()`가 `export_audit` 테이블을 `IF NOT EXISTS`로 자동 생성.

### CTO 승인 조건부 조건

`tech-critic-lead` 결재에서 **승인 / 신뢰도 82**로 통과. 부과된 6개 조건:

1. **페이지네이션/필터/CSV export 금지를 코드 레벨에서 관철**. `MY_AUDIT_LOG_LIMIT = 100` 상수만. 첫 배포에서 기능 추가 금지.

2. **stdout `[export]` / `[my-export]` 로그 유지** — DB INSERT와 이중 기록. 관측 루트 다양성 담보 (Fly.io 재시작 외 즉시 확인 경로).

3. **`docs/spec.md` "다음 스프린트 예약 티켓" N0 라인 삭제 필수** — live 이행이 문서에 반영되지 않으면 다음 스프린트에서 중복 제안이 올라옴. `docs/user-intervention.md`는 변경 없음 유지.

4. **타 트레이너 row 노출 차단 테스트(test #4) 필수 포함** — WHERE 절 버그 1개가 감사 로그 뷰어를 "트레이너간 activity 누설 채널"로 뒤집을 수 있음. iter 5 R5 부분 구현이 live인 상황에서 이 회귀는 용납 불가.

5. **`rows` 컬럼은 data row 수 (header 제외)** — `_write_sessions_csv` 반환 규약 그대로 사용. 테스트 #8에서 "본문 줄 수 = data rows + header 1줄" 혼동 금지.

6. **관장이 자기 자신을 target으로 지정해 뽑은 row가 관장 `/my/audit-log`에 보이는지 test #6으로 커버** — 관장도 본인 자격으로 audit 확인 가능해야 함.
