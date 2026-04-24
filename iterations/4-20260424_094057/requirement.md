# Requirement

## 가치제안

# BET (Best Training) — PT 트레이너·헬스장 관장용 가치제안 (iteration 4 기준)

> 전달 모드: landing_plus_meeting
> 배포 상태: **MVP v3 라이브** (iteration 1 + iteration 2 + iteration 3 배포 완료). iteration 3에서 트레이너 본인 "내 입력분 CSV export"(`GET /my/export/sessions.csv`)가 추가됨 — 직전 시뮬에서 stakeholder 최상위 우려였던 "트레이너 IP 가드레일 roadmap→live 전환"이 이행됨.
> 대상: 중소 동네 헬스장 관장 겸 트레이너 (회원 ~50명 규모)
> 기존 도구: Rappo 병행 사용 전제

---

## 0. 이번 미팅의 맥락

지난 미팅에서 합의한 12주 무료 파일럿의 **6주차 진입 시점** 기준 후속 미팅입니다.

- 지난 미팅(4주차) 때 관장·소속트레이너 양측이 1순위로 요구한 **R0 트레이너 본인 CSV export**가 5주차에 live로 붙었습니다.
- 따라서 지난 미팅의 **"감시 메커니즘은 live, 방어장치는 roadmap"**이라는 비대칭은 기술적으로 해소됐습니다 (관장이 `/admin/export/sessions.csv?trainer_id=<id>`로 트레이너 입력분을 필터 추출할 수 있듯, 트레이너도 `/my/export/sessions.csv`로 본인 입력분 전체를 자기 권한으로 가져갈 수 있음).
- 이번 미팅의 목적은 **남은 7주 동안 붙일 다음 기능 1개**를 관장님 + 소속 트레이너 피드백으로 정하는 것.

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

- "[무료] 3개월 파일럿 신청" → 12주 간 3개 회원 계정 무료 제공, 이후 성과 확인 후 정식 계약. **현재 6주차 진행 중**.

---

## 2. 해결하려는 문제 (Pain Statement)

### 트레이너·관장 관점

1. **"우리 PT 좋아요"를 증명할 자료가 빈약함.** 상담 테이블에서 인바디 수치 하나만으로 설득.
2. **회원 발전 추이 가시화 부재.** Rappo 등 기존 도구에 없는 기능.
3. **PT 외 6일 방치.** 주 1회 PT만으로 결과를 책임지는 구조적 한계.
4. **리텐션 고민.** 3개월 이탈 패턴.
5. **(iteration 2+3에서 추가 인식된 축) 트레이너 IP 소유권 갈등**. 세션 데이터를 누가 보유하고, 퇴사 시 누구의 자산인가. — **R0 live로 1차 완화**, 단 "관장이 언제 내 입력분을 뽑았는지 트레이너가 확인할 수단"은 아직 stdout 로그 수준.

### 회원(downstream) 관점

1. PT 받는 날만 운동, 나머지 6일 무방비.
2. 발전 여부 애매, 인바디 외 피드백 산발.
3. 트레이너 이직 시 운동 히스토리 증발.

---

## 3. 현재 동작하는 것 (iteration 1 + 2 + 3, 라이브)

관장·트레이너가 지금 URL 열어서 쓸 수 있는 기능.

### A. 세션 기록 입력 (`/trainers/:tid/members/:mid/log`)

- 세트 단위 `운동 / 중량(kg) / 횟수` 입력. HTMX "세트 행 추가" 버튼.
- 운동 종목 10종 고정: 스쿼트 / 벤치프레스 / 데드리프트 / 오버헤드프레스 / 바벨로우 / 풀업 / 레그프레스 / 랫풀다운 / 레그컬 / 덤벨컬.
- 저장 시 로그인한 트레이너의 ID가 `input_trainer_id`로 함께 기록 → 퇴사 후 "누가 입력했는가" 영구 trail.

### B. 회원별 진행 대시보드 (`/trainers/:tid/members/:mid/dashboard`)

- 꺾은선 그래프 2개: **운동 종목별 최대 중량 추이** + **세션당 총 볼륨 추이**(Σ중량×횟수).
- 실제 수행한 종목만 선으로. 세션 0건 회원은 빈 그래프.

### C. 다중 트레이너 로그인 + 관장 권한 분기 (iteration 2)

- 소속 트레이너마다 개별 `username`/`password` 계정.
- 관장(`is_owner=1`) 1명만 존재. `is_owner=1`만 `/admin/export/sessions.csv` 접근.
- 계정 CRUD는 웹 UI 없음 — `scripts.seed_trainer` CLI(관장이 서버 콘솔 수행).
- 비밀번호 해싱: `hashlib.scrypt` 표준라이브러리만.

### D. 관장 전용 CSV export (iteration 2)

- `GET /admin/export/sessions.csv[?trainer_id=<id>]`. 전체 또는 특정 트레이너 필터.
- 컬럼: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`. UTF-8 BOM.
- 60초 rate limit + stdout 감사 로그 `[export] owner_id=X target_trainer_id=Y rows=N`.

### E. **(iteration 3) 트레이너 본인 CSV export — `GET /my/export/sessions.csv`**

- **auth**: 로그인만 필요. `is_owner` 체크 **없음**. 관장도 본인 자격으로 호출 시 본인 trainer_id row만 반환 (bypass 없음).
- **필터 고정**: `pt_sessions.input_trainer_id = session["user"]["trainer_id"]`. 쿼리 파라미터 없음.
- **응답**: 관장 export와 **bit-exact 동일 컬럼** (공통 헬퍼 `_write_sessions_csv` + 상수 tuple `_SESSIONS_CSV_COLUMNS`로 코드 레벨 drift 차단). UTF-8 BOM.
- **Rate limit**: 관장 export와 **별도 dict**(`my_export_last_ts`). 양 라우트 간 상호 영향 0.
- **감사 로그**: `[my-export] trainer_id=X rows=N` (관장 `[export]`와 prefix 구분).
- **회귀 테스트**: 같은 DB에서 관장 `/admin/export?trainer_id=X` ↔ X로 로그인 `/my/export` 본문 bit-exact 동치 검증 CI 통과.

### F. 트레이너간 회원 접근 — **permissive** (의도적)

- 트레이너A가 트레이너B 담당 회원 URL 직접 입력 시 접근 가능 (유효 tid/mid 조합만).
- 완전 격리 + 회원 자가 대시보드는 R5에서 다룸.

### G. 인프라 (최소)

- Fly.io 단일 VM (region `nrt`) + 1GB 영속 볼륨 SQLite.
- 관측은 stdout + Fly 기본 로그만. 외부 관측 의존 없음.

### H. 현 시점의 명시적 한계

아래는 **아직 없음**. 이번 미팅에서 우선순위 피드백이 필요합니다.

- **감사 로그 능동 조회 뷰어 없음.** 관장/본인 export trail은 stdout에만. 트레이너가 "관장이 언제 내 입력분을 뽑아갔는가"를 **앱 안에서** 능동 조회할 수단 부재.
- 자세 교정 기록 / 컨디션·수면·식단 자가보고 / 인바디 연동 — **볼륨 외 지표 없음**.
- AI 트레이너 카카오톡 채널 — **PT 외 6일 코칭 기능 없음**.
- PDF 12주 성장 리포트 — **상담장에서 인쇄물로 배포 불가**.
- Rappo CSV/API 연동 — **회원 명단은 seed 스크립트로 BET 측이 수동 주입**.
- 회원용 UI — **회원은 자기 대시보드 직접 접근 불가**.
- 다중 헬스장 — 단일 헬스장 전제 유지.

---

## 4. 파일럿 잔여 7주 로드맵 (우선순위 미확정 — 오늘 함께 정할 것)

아래 7개 후보 중 **한 번에 1개씩** 붙일 계획. 다음 1순위를 오늘 확정합니다.

### N0. 감사 로그 능동 조회 뷰어 (`GET /my/audit-log`) — **직전 시뮬 5/6 언급**

- 트레이너 본인이 **"누가(관장 vs 본인) 언제 내 입력분을 export 했는가"**를 앱 안에서 조회.
- DB에 `export_audit` 테이블 추가 (기존 stdout 로그 병행). `/admin/export` + `/my/export` 성공 시 1 row INSERT.
- 뷰어는 본인 것만 조회. 관장이 다른 트레이너의 audit log를 엿보는 경로 없음.
- **가치**: R0로 "데이터 자산 권리"는 해소됐으나 "감시 투명성"은 여전히 비대칭. stdout은 트레이너가 읽을 수단 無. 이 뷰어가 "감시 메커니즘 live, 방어장치 live"의 진짜 대칭을 완성.

### R1. PDF "12주 성장 리포트" 출력

- 대시보드 화면을 A4 1~2장 PDF로 내려받기. 상담 테이블에 올릴 인쇄물.
- 그래프 + 회원 이름 + 기간 요약 + 트레이너 서명란.
- **가치**: 파일럿 DoD 약속의 이행 + 잠재회원 상담 자료 물리화.

### R2. 컨디션·수면·식단 자가보고 (회원용 최소 UI)

- 회원 하루 1회 30초 카카오톡/SMS 링크 체크리스트.
- 대시보드에 "생활습관 일관성 점수" 1개 추가 → 중량/볼륨과 중첩.
- **가치**: pain 3(PT 외 6일 방치) 1단계 해소 + 카피의 "다차원 그래프" 실기능 gap 해소.

### R3. AI 트레이너 카카오톡 채널 (MVP)

- 회원이 채널에 식단 사진·컨디션·자가영상 전송 → AI가 당일 가벼운 피드백.
- 컨텍스트: 해당 회원 PT 기록 + 관장이 설정한 "프로토콜(자세·강도·어조)". 이상 신호 시 관장 알림.
- **가치**: pain 3 본격 해소 + BET 핵심 차별화. 단 "트레이너 시간 프리미엄 희석" 우려(직전 시뮬 3/6)를 "프로토콜 편집권 트레이너 귀속"으로 완화 필요.

### R4. Rappo 연동 (CSV import 우선)

- 관장이 Rappo에서 회원 CSV 내보내기 → BET 관리화면 업로드 → 동기화. 연락처 기준 중복 방지.
- **가치**: 이중 운영 부담 reject_trigger 직접 해소.

### R5. 회원용 자가 대시보드 + 트레이너간 완전 격리

- 회원이 개인 URL로 자기 대시보드만 열람 (트레이너간 완전 격리 포함).
- 관장 뷰에서 "개별 트레이너 평균 발전 곡선" UI/API 레벨 차단 + 용도 고지 배너.
- **가치**: 트레이너 평가·방출 도구화 리스크 선제 해소 + 회원 리텐션 장치.

### R6. 자세 교정 태그 (트레이너용 quick action)

- 세션 입력 폼 옆 "교정 포인트" 태그 3~5개 선택 가능.
- 대시보드에 "교정 빈도 감소 추이" 1줄 추가.
- **가치**: "자세 교정은 대체 불가" 포지션 강화 + 트레이너 노하우 데이터화. 태그는 `input_trainer_id` trail로 이미 귀속됨.

---

## 5. 가격 플랜 (세일즈 미팅 단계에서만 공개)

- **파일럿 (12주)**: 무료. 회원 3명까지. **현재 6주차**.
- **스탠다드**: **회원 1인당 월 9,900원**. 최소 10명부터.
- **엔터프라이즈** (50명 이상): 월 인당 8,000원.
- **연 일시불 결제 시 10% 할인.**
- 회원 요금 전가(패키지화/무료 제공)는 헬스장 자율. BET은 헬스장에만 청구.

---

## 6. 자주 받는 질문 (세일즈 미팅용 FAQ)

### Q1. Rappo를 해지해야 하나요?

아니요. 캘린더·운영관리는 Rappo 유지. R4가 붙으면 회원 명단은 자동 동기화.

### Q2. 회원이 앱 설치·매일 기록을 귀찮아하면요?

**현 시점에서 회원은 아무것도 설치/입력하지 않습니다** — 대시보드는 관장님/트레이너가 대면으로 보여주는 용도. R2/R3가 붙는 시점에도 카카오톡 채널로 동작.

### Q3. 소속 트레이너들이 "내 방식대로 못 한다"며 반대하면요?

iteration 2에서 **트레이너별 개별 로그인 + 입력자 귀속** trail 구축 완료. iteration 3에서 **트레이너 본인이 본인 입력분 CSV export를 자기 권한으로 수행**하는 경로(`/my/export/sessions.csv`)가 live. "관장이 내 입력분을 못 가져가게 한다"는 시나리오는 기술적으로 원천 차단됐습니다 (관장이 뽑아도 트레이너가 동일 분량을 뽑아갈 수 있음).

### Q4. 데이터가 우리 회원 데이터인가, BET 데이터인가?

헬스장 소유. **개별 트레이너 본인의 입력분에 한해서는 트레이너도 export 권한을 보유** (iteration 3부터 live). 계약 해지 시 전체 CSV/PDF 내보내기 제공. BET은 익명화 집계 데이터만 제품 개선에 활용.

### Q5. 관장이 언제 내 입력분을 export 했는지 확인하려면?

현재는 **서버 stdout 로그**(`[export] owner_id=X target_trainer_id=Y rows=N`)에 남지만 트레이너가 직접 확인할 수단이 없습니다. N0(감사 로그 뷰어)가 붙으면 본인이 앱 안에서 "관장이 언제, 몇 건을 뽑았는가"를 능동 조회할 수 있습니다.

### Q6. 트레이너가 퇴사하면 쌓인 AI 컨텍스트는?

R3가 붙으면 회원 단위로 귀속. 트레이너 교체 시 새 트레이너가 해당 회원의 컨텍스트를 그대로 승계. 퇴사 트레이너 본인은 자기 입력분 원본을 `/my/export/sessions.csv`로 이미 export 가능 (iteration 3 live).

### Q7. 지난 4주(파일럿 초기) + 이후 2주(R0 배포 후) 실사용은 어떠셨습니까?

(오늘 미팅의 본 논의 지점)

---

## 7. 오늘 미팅의 구체적 요청

관장님께 다음 3개 질문을 드립니다:

1. **R0 (트레이너 본인 CSV export) 실사용 피드백** — 소속 트레이너들이 실제로 본인 export를 사용해봤는지, 사용성 / 사용 빈도 / 예상치 못한 사용 양상이 있었는지.
2. **남은 7주 1순위 기능** — N0 / R1 / R2 / R3 / R4 / R5 / R6 중 가장 먼저 붙이고 싶은 1개 + 선택 이유.
3. **직전 미팅에서 미해소된 우려 재점검** — (a) 감사 로그 능동 조회 수단 부재, (b) "다차원 그래프" 카피 vs 실기능 gap, (c) R3 AI 트레이너가 트레이너 시간 프리미엄을 희석할 우려, (d) 회원 downstream 미검증 — 이 중 여전히 심각하다고 느끼시는 항목은?

---

## 8. BET이 약속하지 않는 것 (리스크 솔직 고지)

- 인바디 수치의 **단기** 개선을 약속하지 않음. AI가 하는 건 "생활습관 일관성"이지 "빠른 결과"가 아님.
- 트레이너의 자세 교정을 대체하지 않음. BET은 그 시간을 확보해 주는 도구.
- 헬스장 매출을 직접 올리는 마케팅 도구 아님. "상담 전환율"을 올릴 자료를 제공하는 도구.
- 현 시점의 대시보드는 **세션 중량/볼륨만**을 보여줌. 다차원 그래프는 R2 이후에 가능.
- 트레이너간 회원 접근 완전 격리는 **R5**에서만 완성됨. 그 전까지는 URL 직접 입력으로 다른 트레이너 회원 접근 가능 (의도적 미완).
- **감사 로그 투명성**은 iteration 3 기준 "stdout 로그만". 트레이너 본인 앱 내 조회는 N0가 붙어야 완성.

## 채택된 요구사항

- **run_id**: `pt-trainer-owner-01_20260424_094206`
- **title**: 트레이너 본인 감사 로그 뷰어 (`GET /my/audit-log`) — export 이력을 앱 안에서 능동 조회 가능하게 구현 (로드맵의 N0)

### 유래한 고객 pain + 근거 인용

유래한 페르소나: `pt-trainer-owner-01` (동네 소규모 헬스장 관장 겸 트레이너, 소속 트레이너 약 2~3명, PT 회원 ~50명 규모) + 직접 stakeholder `sh-other-trainers` (소속 트레이너, influence 40 거부권 성격).

시뮬 최종 판정: **실패 / keyman_gives_up** — 3라운드 재설득 후에도 stakeholder가 drop 45→65→68로 동의선 70을 끝내 돌파하지 않음. stakeholder가 Round 2에서 명시한 "70 돌파 5개 조건" 중 **기술 구현이 필요한 단 1개 항목**이 바로 이 N0.

해소하는 pain (`persuasion-data/runs/pt-trainer-owner-01_20260424_094206/report.md` 직접 인용):

- **`report.md` 가치제안 개선 포인트 1순위 — 언급 세션 수 6/7 (전 세션)**
  > "트레이너→관장 방향 감시 비대칭 (N0 미live). 대표 발화: *'관장은 원하면 지금이라도 내 입력분을 언제든 수집·대조 가능하지만 나는 그 사실을 뒤늦게도 알 수 없다'* (02_stakeholder, 17줄). N0(감사 로그 능동 조회 뷰어)의 live 시점이 재설득 전 라운드의 게이트로 작동."

- **직접 stakeholder 인용 (`02_stakeholder_sh-other-trainers.md`)**
  > "iteration 3의 `/my/export` 라우트는 확인했다. 이걸로 내 입력분 원본을 자력으로 가져갈 수 있는 건 인정. 그런데 **관장이 `/admin/export/sessions.csv?trainer_id=<내id>`를 언제 호출했는지는 stdout 로그에만 남고 내가 읽을 수단이 없다.** 기술적으로 대칭이 아니다."

  > "`[export] owner_id=X target_trainer_id=Y rows=N` 이 로그 포맷 자체는 훌륭하다 — 문제는 이게 `fly logs` 켜야 읽을 수 있는 서버 stdout이란 점이다. 트레이너가 매일 fly auth 해서 로그 뒤지는 시나리오는 현실성 0."

- **stakeholder 70 돌파 조건 (Round 2 recheck, `04_stakeholder_recheck_sh-other-trainers_round2.md` 36~42줄)**
  > "70 돌파 조건 5개 중 N0 live가 유일한 기술 건. 나머지 4개(의사록 서명·계약서 공동 서명란·R3 거부권 명문화·BET CC 실수신)는 문서·절차 영역으로 당신들 쪽 즉시 이행 가능. 즉 **N0만 붙으면 5주 안에 재설득 자리 열어도 된다는 게 내 입장.**"

- **iteration 3 공식 예약 (`docs/spec.md` "다음 스프린트 예약 티켓")**
  > "**트레이너 본인 감사 로그 뷰어** — `GET /my/audit-log` — 트레이너가 '누가 언제 내 입력분을 export 했는가'를 능동 조회하는 페이지. 현재 `[export]` / `[my-export]` stdout 감사 흔적은 트레이너가 직접 볼 수 없으므로, DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다. 시뮬 5/6 언급 2순위 우려(트레이너가 '감시 메커니즘이 live, 방어장치는 roadmap'이라고 판단하는 비대칭성 해소)에 대응."

- **iteration 3 CTO 결재 조건 4번 (`iterations/3-20260424_075811/requirement.md`)**
  > "`docs/spec.md` '다음 스프린트 예약 티켓' 섹션을 감사 로그 뷰어 페이지 후보로 교체 기술: 이 스프린트 범위 외 명시는 맞지만, 시뮬 5/6 언급 2순위 우려(`GET /my/audit-log` — 트레이너 본인이 '누가 언제 내 입력분을 export 했는가'를 능동 조회)이므로 다음 스프린트 후보로 남겨둘 것."

즉 이번 티켓은 (i) 직전 시뮬의 1순위 stakeholder 블로커(6/7 언급), (ii) stakeholder가 명시한 다음 설득 자리 "유일한 기술 전제", (iii) iteration 3에서 spec + CTO 조건 양쪽으로 **예약 명기된 경로**의 이행이며, 기술적으로는 iteration 3의 `_write_sessions_csv` 공통 헬퍼 + `input_trainer_id` trail을 전제로 테이블 1개 + 라우트 1개 + 템플릿 1개를 얇게 추가하는 스코프.

### 구현 스케치

**스택**: 현 iteration 3 그대로 (FastAPI + SQLite + HTMX + Jinja2, Fly.io 단일 VM, `sqlite3` 표준 라이브러리 only). ORM 도입 금지 유지. 외부 의존 추가 0.

#### 신규 DB 테이블 `export_audit`

```sql
CREATE TABLE IF NOT EXISTS export_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  occurred_at TEXT NOT NULL,       -- ISO8601, datetime.now(UTC).isoformat()
  action TEXT NOT NULL CHECK(action IN ('owner_export','my_export')),
  actor_trainer_id INTEGER NOT NULL REFERENCES trainers(id),
  target_trainer_id INTEGER REFERENCES trainers(id),
  rows_count INTEGER NOT NULL CHECK(rows_count >= 0)
);
CREATE INDEX IF NOT EXISTS ix_export_audit_target ON export_audit(target_trainer_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_export_audit_actor  ON export_audit(actor_trainer_id,  occurred_at DESC);
```

- `init_db()`에 idempotent CREATE + ALTER 추가 (기존 패턴 준수).
- 데이터 백필 없음: stdout 로그가 문서 증거로 존재하므로 과거는 stdout 스캔으로만 재구성. 미래분부터 기록.

#### export 라우트 계측 (신규 INSERT 2곳)

- `/admin/export/sessions.csv` 성공 응답 직전: `INSERT INTO export_audit(occurred_at, action, actor_trainer_id, target_trainer_id, rows_count) VALUES(?, 'owner_export', <owner_trainer_id>, <trainer_id query or NULL>, <rows>)`.
- `/my/export/sessions.csv` 성공 응답 직전: `INSERT ... VALUES(?, 'my_export', <session_trainer_id>, <session_trainer_id>, <rows>)`.
- 기존 stdout 로그는 그대로 유지 (병행). 로그 drift 예방 + 관장이 `fly logs`로 여전히 볼 수 있음.
- **DB INSERT 실패 시 처리 (CTO 조건 1)**: try/except로 잡아 stdout `[audit-insert-failed] action=<x> actor=<y> target=<z> rows=<n> err=<err_type>` 한 줄 + 응답은 200 그대로 반환. `err_type`은 예외 클래스명 한 토큰(`IntegrityError`·`OperationalError` 등) 필수.

#### 신규 라우트 `GET /my/audit-log`

- **auth**: 로그인만. `is_authenticated(request) == True` 아니면 303 → `/login`. is_owner 체크 없음.
- **쿼리**: 없음. 최근 `MY_AUDIT_LOG_LIMIT = 100`건만 DESC로 반환 (**CTO 조건 3**: 하드코딩 금지, `app/routes.py` 상단 상수로 추출).
- **필터 SQL (CTO 조건 2)**: 관장이 `trainer_id` 필터 없이 전체 export한 row는 `target_trainer_id IS NULL`이므로 단순 `OR`로는 누락됨 → 다음 쿼리 사용:
  ```sql
  SELECT id, occurred_at, action, actor_trainer_id, target_trainer_id, rows_count
    FROM export_audit
   WHERE actor_trainer_id = :me
      OR target_trainer_id = :me
      OR (action = 'owner_export' AND target_trainer_id IS NULL)
   ORDER BY occurred_at DESC
   LIMIT :limit
  ```
- **응답**: Jinja2 HTML 템플릿 `my_audit_log.html` 1개 추가 (CTO 조건 5: **HTMX/Chart.js 불필요, 순수 Jinja2 + 표 1개**. 스타일링 yak-shaving 금지). 표 컬럼: `일시 / 행위 / 호출자 / 대상 / rows`.
  - `action='owner_export'` + `target_trainer_id IS NULL` → "전체 대상(본인 포함)"으로 표기.
  - `action='owner_export'` + `target_trainer_id=본인` → "관장이 본인 대상 export".
  - `action='my_export'` → "본인 내보내기".
- **Rate limit**: 없음 (read-only 뷰 + 로그인 게이트만으로 충분).
- **감사 로그**: stdout 출력 없음 (뷰어 자체는 읽기, 기록할 감사 의미 낮음).

#### 공통 헬퍼 재사용

- 기존 `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int`는 이미 rows 반환. audit INSERT는 라우트 레벨에서 헬퍼 반환값 사용 → 헬퍼 시그니처 변경 불필요. 드리프트 없음.

#### 테스트 (`docs/testing.md` 준수: mock 금지, tmp_path SQLite)

`tests/test_audit_log.py` 신규:
1. `/admin/export` 성공 시 `export_audit` row 1건 INSERT 확인. `action='owner_export'`, actor=owner_id, target=쿼리값(or NULL), rows 일치.
2. `/my/export` 성공 시 `export_audit` row 1건 INSERT 확인. `action='my_export'`, actor=session_tid, target=session_tid.
3. 트레이너 B로 로그인해 `/my/audit-log` 호출 시: B가 target인 `owner_export` row + B가 actor인 `my_export` row + **관장이 trainer_id 필터 없이 전체 export한 row(target=NULL) 가 '전체 대상(본인 포함)' 표기로 노출**되는지 (CTO 조건 2의 필수 검증).
4. `/my/audit-log` 미로그인: 303 → /login.
5. 관장 자격으로 `/my/audit-log` 호출: 관장이 target/actor인 row만 + `target IS NULL` 전체 export row. 다른 트레이너 actor/target row 미포함. **is_owner bypass 없음**.
6. `MY_AUDIT_LOG_LIMIT=100` limit 검증: 150건 INSERT 후 100건만 반환 + DESC 정렬 검증.
7. DB INSERT 실패 스모크 테스트 (예: `export_audit` 테이블을 fixture에서 drop 후 export 호출): export 자체 200 OK + body 온전 + stdout에 `[audit-insert-failed] action=owner_export actor=... target=... rows=... err=OperationalError` (or 유사한 err token) 포맷 확인 (capsys).

Playwright e2e 테스트는 이번 스프린트 범위 외.

#### 문서 수정

- `docs/spec.md`:
  - "데이터 모델" 섹션에 `export_audit` 테이블 추가.
  - "라우트 목록"에 `GET /my/audit-log` 1줄 추가.
  - 신규 섹션 `## 감사 로그` — `export_audit` 스키마, INSERT 시점, 뷰어 계약, `MY_AUDIT_LOG_LIMIT` 상수 명시.
  - 기존 "CSV Export" 섹션에 "성공 시 `export_audit` 테이블에 1 row INSERT (실패 시 export는 성공 유지 + stdout `[audit-insert-failed] err=<type>`)" 문구 삽입.
  - "다음 스프린트 예약 티켓" 섹션을 **R5 부분 구현 — 트레이너간 회원 접근 격리 hardening** 후보로 교체 (CTO 조건 4):
    - **범위 확정**: `members.owner_trainer_id` 기준 본인 회원만 조회 가능한 미들웨어 추가. 404 대신 403 반환. 관장은 여전히 전체 접근 가능(is_owner bypass 유지). **UI 비가시화(URL 목록 제거 등)는 범위 외.** 회원 자가 대시보드는 R5 풀버전에서 다룸.
    - **실행 트리거 조건**: 다음 시뮬 run에서 "트레이너 비교지표 도구화 + R3 위협 (R5 미live)"가 재차 상위 3개 언급 (≥ 5/7) + stakeholder drop confidence가 본 run(68)보다 하락할 경우 즉시 실행. 그 외엔 R1/R2 등과 재경쟁.
- `docs/testing.md`:
  - "테스트 구성"에 `tests/test_audit_log.py` 추가 + 신규 7 시나리오 요약.
- `docs/user-intervention.md`:
  - 변경 없음. 새 env/secret/수동 스크립트 없음.

#### 인간 개입 지점

- **없음**. `fly deploy`만 관장이 실행 (iteration 1/2/3과 동일, `docs/user-intervention.md` 기존 절차).
- DB 스키마 변경은 `init_db()`의 idempotent CREATE + ALTER TABLE 패턴 — 자동.
- 백필 스크립트 불요 (미래분부터 기록).

### CTO 승인 조건부 조건

`tech-critic-lead` 결재에서 **승인 / 신뢰도 82**로 통과. 부과된 5개 조건:

1. **INSERT 실패 시 stdout 포맷 명시**: `[audit-insert-failed] action=... actor=... target=... rows=... err=<type>` — `err` 토큰 1개(예외 클래스명) 필수 포함. 테스트 7번이 이 포맷을 검증할 것.

2. **`target_trainer_id IS NULL` 전체 export row 누락 방지**: 뷰어 쿼리는 `WHERE actor_trainer_id = :me OR target_trainer_id = :me OR (action='owner_export' AND target_trainer_id IS NULL)`로 확장. 테스트 3번에 "관장이 trainer_id 필터 없이 전체 export한 row가 타 트레이너의 `/my/audit-log`에 '전체 대상(본인 포함)'으로 노출되는가" 필수 추가. 이 누락은 stakeholder pain ("관장이 언제 호출했는지")을 정면으로 비껴감.

3. **100건 LIMIT 상수 추출**: `app/routes.py` 상단에 `MY_AUDIT_LOG_LIMIT = 100` 상수로 추출. 파일럿 피드백 시 1줄 수정으로 튜닝 가능하게.

4. **"다음 스프린트 예약 티켓" 섹션 교체**: R5 부분 구현의 범위를 **지금** 확정("`members.owner_trainer_id` 기준 미들웨어, UI 비가시화는 범위 외"). 실행 트리거 조건("다음 시뮬에서 R5 우려 재상위 + stakeholder drop confidence 하락") 명시. 예약만 덩그러니 남기지 말 것.

5. **템플릿 스타일링 최소화**: `my_audit_log.html`은 HTMX/Chart.js 불필요. 순수 Jinja2 HTML + `<table>` 1개로 제한. 스타일링 yak-shaving 금지.

### 검토한 더 싼 대안들 (CTO에 함께 제출·기각)

1. ~~stdout 로그를 파일로 rotate 후 트레이너에게 SCP 권한 부여~~
   → 서버 접근 권한 오남용 + OS 계정 관리 필요. 운영 부담 급증. 스코프 폭증.

2. ~~이메일/슬랙 알림 (export 발생 시 트레이너에게 통보)~~
   → 외부 의존 추가(Sentry 등 금지 정책과 결). 과거 이력 "능동 조회" 요구를 해소하지 못함.

3. ~~audit 테이블만 만들고 뷰어는 다음 스프린트로~~
   → report.md 핵심 요구가 "앱 안에서 능동 조회 가능"이므로 DB만으로는 pain 해소 불가. "선언 vs 이행" 원칙 상 stakeholder가 다시 drop.

4. ~~`fly logs`를 관장이 주 1회 export → 메일 송부 운영 프로세스~~
   → 운영 부담 + "관장 경유" 구도를 재생산 (stakeholder 본 uneasy의 핵심 = 관장 경유 불필요한 자체 확인).

5. ~~뷰어에 페이지네이션·필터·CSV export까지 모두 추가~~
   → 스코프 폭증. 100건 LIMIT + 최근순만으로 MVP pain 해소 가능. 추가 기능은 실사용 후 요청 시 재평가.

6. ~~R5 부분 구현(트레이너간 접근 격리)을 먼저~~
   → 시뮬 2순위(6/7)이나 구현 범위가 미들웨어 + 회원 소유권 정책 + UI 영향 커서 스프린트 초과 리스크. N0이 더 명확한 단일 블로커이고 1순위 언급(6/7)으로 가치도 최소 동급. R5는 다음 스프린트 후보로 명시 예약 (CTO 조건 4 반영).
