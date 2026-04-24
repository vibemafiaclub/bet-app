# Requirement

## 가치제안

# BET (Best Training) — PT 트레이너·헬스장 관장용 가치제안 (iteration 5 기준)

> 전달 모드: landing_plus_meeting
> 배포 상태: **MVP v4 라이브** (iteration 1 + 2 + 3 + 4 배포 완료). iteration 4에서 **N0 — 트레이너 본인 감사 로그 뷰어(`GET /my/audit-log`)**가 live로 붙음. 직전 시뮬(094206)의 stakeholder 1순위 블로커(감시 비대칭)가 해소됨.
> 대상: 중소 동네 헬스장 관장 겸 트레이너 (회원 ~50명 규모)
> 기존 도구: Rappo 병행 사용 전제

---

## 0. 이번 미팅의 맥락

지난 미팅에서 합의한 12주 무료 파일럿의 **8주차 진입 시점** 기준 후속 미팅입니다.

- 지난 미팅(6주차)에서 stakeholder가 명시한 "70 돌파 5개 조건" 중 유일한 기술 건인 **N0 감사 로그 뷰어**가 7주차에 live로 붙었습니다. 나머지 4개(의사록 서명본·계약서 공동 서명란·R3 post-contract 거부권 명문화·BET CC 실수신)도 문서/절차 영역으로 관장·BET 간 합의서 초안으로 병행 이행 중.
- 이번 미팅의 목적은 **남은 5주 동안 붙일 다음 기능 1개**를 관장님 + 소속 트레이너 피드백으로 정하는 것. 후보는 지난번 로드맵의 R1/R2/R3/R4/R5/R6 및 새로 떠오른 보조 후보들.

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

- "[무료] 3개월 파일럿 신청" → 12주 간 3개 회원 계정 무료 제공, 이후 성과 확인 후 정식 계약. **현재 8주차 진행 중**.

---

## 2. 해결하려는 문제 (Pain Statement)

### 트레이너·관장 관점

1. **"우리 PT 좋아요"를 증명할 자료가 빈약함.** 상담 테이블에서 인바디 수치 하나만으로 설득.
2. **회원 발전 추이 가시화 부재.** Rappo 등 기존 도구에 없는 기능.
3. **PT 외 6일 방치.** 주 1회 PT만으로 결과를 책임지는 구조적 한계.
4. **리텐션 고민.** 3개월 이탈 패턴.
5. **트레이너 IP 소유권 + 감시 투명성** — iteration 3(본인 CSV export) + iteration 4(audit log 뷰어) live로 1차 완화. 단 "트레이너 비교지표 도구화 우려"는 R5가 오기 전까지 구조적으로 상존.

### 회원(downstream) 관점

1. PT 받는 날만 운동, 나머지 6일 무방비.
2. 발전 여부 애매, 인바디 외 피드백 산발.
3. 트레이너 이직 시 운동 히스토리 증발.

---

## 3. 현재 동작하는 것 (iteration 1~4, 라이브)

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
- 60초 rate limit + stdout 감사 로그 + `export_audit` row INSERT.

### E. 트레이너 본인 CSV export — `GET /my/export/sessions.csv`

- 로그인만 필요. `is_owner` 체크 없음. 관장도 본인 자격 한정.
- 필터 고정: `pt_sessions.input_trainer_id = session_trainer_id`. 쿼리 파라미터 없음.
- 관장 export와 **bit-exact 동일 컬럼**(공통 헬퍼 `_write_sessions_csv`). UTF-8 BOM.
- 별도 rate limit dict + `[my-export]` prefix 감사 로그 + `export_audit` row INSERT.

### F. **(iteration 4) 트레이너 본인 감사 로그 뷰어 — `GET /my/audit-log`**

- **auth**: 로그인만. is_owner 체크 없음.
- **쿼리 동작**: 본인이 actor이거나 target인 `export_audit` row + 관장이 `trainer_id` 필터 없이 전체 export한 `target IS NULL` row까지 포함해 DESC/최근 100건 표시.
- **표**: `일시 / 행위 / 호출자 / 대상 / rows`. `action='owner_export' AND target IS NULL` → "전체 대상(본인 포함)"으로 표기.
- **의미**: 직전 시뮬 1순위 블로커였던 "관장 감시 비대칭" 해소 — 트레이너가 앱 안에서 "관장이 언제·몇 건 내 입력분을 가져갔는가"를 능동 조회 가능.
- **제약**: 페이지네이션·필터·CSV export 없음. 100건 LIMIT + 최근순만(파일럿 피드백 시 `MY_AUDIT_LOG_LIMIT` 상수 1줄 수정).

### G. 트레이너간 회원 접근 — **여전히 permissive** (의도적)

- 트레이너A가 트레이너B 담당 회원 URL 직접 입력 시 접근 가능 (유효 tid/mid 조합만).
- 완전 격리 + 회원 자가 대시보드는 **R5**에서 다룸 (이번 스프린트 후보 중 하나).

### H. 인프라 (최소)

- Fly.io 단일 VM (region `nrt`) + 1GB 영속 볼륨 SQLite.
- 관측은 stdout + Fly 기본 로그만. 외부 관측 의존 없음.

### I. 현 시점의 명시적 한계

아래는 **아직 없음**. 이번 미팅에서 우선순위 피드백이 필요합니다.

- **자세 교정 기록 / 컨디션·수면·식단 자가보고 / 인바디 연동 — 볼륨 외 지표 없음.**
- **AI 트레이너 카카오톡 채널 — PT 외 6일 코칭 기능 없음.**
- **PDF 12주 성장 리포트 — 상담장에서 인쇄물로 배포 불가.**
- **Rappo CSV/API 연동 — 회원 명단은 seed 스크립트로 BET 측이 수동 주입.**
- **회원용 UI — 회원은 자기 대시보드 직접 접근 불가.**
- **트레이너간 회원 접근 완전 격리 — permissive 유지.**
- **트레이너 프로토콜/태그 구조 이관 무대응** — `/my/export`가 원시 세트만 내려주고, 설계한 프로토콜·태그는 못 가져감 (직전 시뮬 5순위 지적).
- **10종 고정 운동 한계** — 코어·컨디셔닝·기능성 세션 기록 구조 진입 불가 (직전 시뮬 4순위 지적).
- **ROI 증거 계측 부재** — 상담 전환율/리텐션 변화를 숫자로 환원할 수단 없음. 가격 상한 상향 조정 근거 없음 (직전 시뮬 7순위 지적).
- **다중 헬스장** — 단일 헬스장 전제 유지.

---

## 4. 파일럿 잔여 5주 로드맵 (우선순위 미확정 — 오늘 함께 정할 것)

아래 후보 중 **한 번에 1개씩** 붙일 계획. 다음 1순위를 오늘 확정합니다.

### R1. PDF "12주 성장 리포트" 출력

- 대시보드 화면을 A4 1~2장 PDF로 내려받기. 상담 테이블에 올릴 인쇄물.
- 그래프 + 회원 이름 + 기간 요약 + 트레이너 서명란.
- **가치**: 파일럿 DoD 약속의 이행 + 잠재회원 상담 자료 물리화.
- **구현 스케치**: `weasyprint` 또는 `pyppeteer` 기반 서버사이드 렌더 → `/trainers/:tid/members/:mid/report.pdf`. Chart.js 대시보드 HTML을 해당 라이브러리가 읽어 A4로 굽기.

### R2. 컨디션·수면·식단 자가보고 (회원용 최소 UI)

- 회원 하루 1회 30초 체크리스트. 카카오톡/SMS 링크 또는 간소 웹 UI.
- 대시보드에 "생활습관 일관성 점수" 1개 추가 → 중량/볼륨과 중첩.
- **가치**: pain 3(PT 외 6일 방치) 1단계 해소 + "다차원 그래프" 카피의 실기능 gap 해소.
- **구현 스케치**: `/m/<token>/daily` (토큰 링크 인증) → 체크리스트 POST → `daily_logs` 테이블. 대시보드에 일관성 점수 꺾은선 1개 추가.

### R3. AI 트레이너 카카오톡 채널 (MVP)

- 회원이 채널에 식단 사진·컨디션·자가영상 전송 → AI가 당일 가벼운 피드백.
- 컨텍스트: 해당 회원 PT 기록 + 관장이 설정한 "프로토콜(자세·강도·어조)".
- **가치**: pain 3 본격 해소 + BET 핵심 차별화.
- **리스크**: "트레이너 시간 프리미엄 희석" stakeholder 우려(직전 시뮬 2순위 6/7). "post-contract 거부권 명문화"가 계약서에 들어가지 않는 한 stakeholder 재설득 어려움.

### R4. Rappo 연동 (CSV import 우선)

- 관장이 Rappo에서 회원 CSV 내보내기 → BET 관리화면 업로드 → 동기화. 연락처 기준 중복 방지.
- **가치**: 이중 운영 부담 reject_trigger 직접 해소.
- **구현 스케치**: `GET/POST /admin/import/members.csv`. 업로드된 CSV 파싱 → `members` 테이블 upsert. 이미 있는 연락처는 no-op.

### R5. 트레이너간 회원 접근 격리 — **부분 구현 가능**

- `members.owner_trainer_id` 기준 본인 회원만 조회 가능한 미들웨어. 404 대신 403 반환. 관장은 is_owner bypass 유지.
- 회원 자가 대시보드 + UI 비가시화는 풀버전(R5-full)에서 다룸. 이번은 서버 사이드 가드레일만.
- **가치**: stakeholder 직전 시뮬 2순위(6/7 언급) 우려 "트레이너 비교지표 도구화"의 구조적 차단.
- **구현 스케치**: `members` 테이블에 `owner_trainer_id INTEGER FK` ADD (idempotent, 기존 `trainer_id` 컬럼을 owner로 승격 or 신규 컬럼). `require_member_access` 미들웨어 → 미소유 + 비관장이면 403.

### R6. 자세 교정 태그 (트레이너용 quick action)

- 세션 입력 폼 옆 "교정 포인트" 태그 3~5개 선택 가능.
- 대시보드에 "교정 빈도 감소 추이" 1줄 추가.
- **가치**: "자세 교정은 대체 불가" 포지션 강화 + 트레이너 노하우 데이터화.

### R7 (신규). 트레이너 프로토콜/태그 이관 번들 export

- `/my/export/protocol.json` — 트레이너 본인이 설계한 프로토콜·태그·노트 구조를 JSON 번들로 자가 export.
- **가치**: 직전 시뮬 5순위(3회 언급) "퇴사 시 프로토콜 이관 무대응" 해소. stakeholder가 "신규 구조 양보 카드 소진"을 drop 사유로 든 잔여 항목.
- **제약**: 현재 코드에 "프로토콜·태그" 자체가 없음. R6(자세 교정 태그)가 선행되지 않으면 export할 내용 없음 → R6 + R7 묶음 구성이 자연스러움.

### R8 (신규). 운동 종목 확장 — 11~15종 추가 (코어·컨디셔닝 커버)

- 현재 10종 고정 → 15~20종으로 확장. 코어(플랭크·크런치), 컨디셔닝(버피·마운틴클라이머), 기능성(터키시겟업 등) 포함.
- **가치**: 직전 시뮬 4순위(4회 언급) "세션 입력 UX 부담 + 10종 고정이 Rappo 대비 즉시 열위" 해소. 트레이너의 실제 커리큘럼 중 데이터화 안 되던 영역 흡수.
- **구현 스케치**: `exercises.py`의 `ALLOWED_EXERCISES` 상수 확장 + CHECK 제약 마이그레이션. 표준 라이브러리 sqlite3 `ALTER TABLE ... CHECK` 재적용 idempotent 스크립트.

### R9 (신규). 상담 전환율·리텐션 지표 관장 대시보드 (ROI 증거 계측)

- 관장 전용 `/admin/roi-dashboard` — 회원 등록 후 PT 지속 기간, 상담→계약 전환율(수동 입력) 추이 시각화.
- **가치**: 직전 시뮬 7순위(3회 언급) "ROI 증거 부재로 가격 상한 상향 조정 근거 無" 해소. 가격 탄력성 확보.
- **제약**: "상담 전환율"의 원천 데이터가 현재 시스템에 없음 → 관장이 월 1회 수동 입력하는 최소 UI 필요. 자동화는 R4(Rappo 연동) 이후 가능.

---

## 5. 가격 플랜 (세일즈 미팅 단계에서만 공개)

- **파일럿 (12주)**: 무료. 회원 3명까지. **현재 8주차**.
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
- iteration 4 **트레이너 본인 감사 로그 뷰어**(`/my/audit-log`) live → "관장이 언제 내 입력분을 뽑았는가"를 트레이너가 앱 안에서 능동 조회.
- "관장이 내 입력분을 못 가져가게 한다" + "몰래 가져간다"는 시나리오 둘 다 기술적으로 차단됨.

### Q4. 데이터가 우리 회원 데이터인가, BET 데이터인가?

헬스장 소유. **개별 트레이너 본인의 입력분에 한해서는 트레이너도 export 권한 + export 이력 능동 조회 권한 보유**. 계약 해지 시 전체 CSV/PDF 내보내기 제공. BET은 익명화 집계 데이터만 제품 개선에 활용.

### Q5. 트레이너 비교지표 도구화가 우려됩니다.

현재는 관장이 대시보드에서 트레이너별 평균치를 비교할 가능성이 구조적으로 존재합니다 (permissive). **R5 부분 구현**이 붙으면 서버 사이드에서 미소유 회원 접근 시 403, 관장도 `?trainer_id=` 비교 API를 재설계하게 됩니다. R5 풀버전은 회원 자가 대시보드 + 관장 UI 비가시화까지 포함.

### Q6. 트레이너가 퇴사하면 쌓인 프로토콜은?

**현재는 세트 원시 데이터만** `/my/export`로 가져갈 수 있습니다. 트레이너가 설계한 프로토콜·태그·메모 구조 이관은 **R7 후보**로 남아있습니다. R6(태그 도입) 선행 조건.

### Q7. 운동 종목이 10종밖에 없어서 기록 못 하는 커리큘럼이 많습니다.

**현재 10종 고정**(스쿼트·벤치·데드·OHP·바벨로우·풀업·레그프레스·랫풀다운·레그컬·덤벨컬). **R8 후보**로 15~20종 확장이 올라가 있습니다. 관장님 실제 커리큘럼에서 빠져서 가장 아쉬운 종목을 알려주시면 R8 범위에 우선 반영하겠습니다.

### Q8. 파일럿 8주차 — ROI는 얼마나 잡혔습니까?

현재 BET이 자체 계측하는 ROI 지표는 없습니다. 관장님이 상담 테이블에서 대시보드를 얼마나 활용하셨고, 상담→계약 전환이 어떻게 움직였는지는 **관장님 체감**에만 의존. **R9 후보**(관장용 ROI 대시보드)가 이 공백을 메우는 자리입니다.

---

## 7. 오늘 미팅의 구체적 요청

관장님께 다음 3개 질문을 드립니다:

1. **N0 (트레이너 본인 감사 로그 뷰어) 실사용 피드백** — 7주차 live 후 소속 트레이너들이 실제로 `/my/audit-log`를 조회해봤는지, 조회 빈도 / 사용성 / 100건 LIMIT 불편 / "전체 대상(본인 포함)" 표기가 의심/안도 중 어느 쪽을 불러일으켰는지.
2. **남은 5주 1순위 기능** — R1 PDF / R2 자가보고 / R3 AI 채널 / R4 Rappo / R5 격리부분구현 / R6 태그 / R7 프로토콜이관 / R8 종목확장 / R9 ROI대시보드 중 가장 먼저 붙이고 싶은 1개 + 선택 이유.
3. **직전 미팅에서 미해소된 우려 재점검** — (a) 트레이너 비교지표 도구화(R5 미live), (b) R3 AI 트레이너의 프리미엄 희석, (c) 프로토콜 이관 미대응, (d) 10종 고정 한계, (e) ROI 증거 부재 — 이 중 여전히 심각하다고 느끼시는 항목은?

---

## 8. BET이 약속하지 않는 것 (리스크 솔직 고지)

- 인바디 수치의 **단기** 개선을 약속하지 않음. AI가 하는 건 "생활습관 일관성"이지 "빠른 결과"가 아님.
- 트레이너의 자세 교정을 대체하지 않음. BET은 그 시간을 확보해 주는 도구.
- 헬스장 매출을 직접 올리는 마케팅 도구 아님. "상담 전환율"을 올릴 자료를 제공하는 도구.
- 현 시점의 대시보드는 **세션 중량/볼륨만**을 보여줌. 다차원 그래프는 R2 이후에 가능.
- 트레이너간 회원 접근 완전 격리는 **R5**에서만 완성됨. 그 전까지는 URL 직접 입력으로 다른 트레이너 회원 접근 가능.
- 프로토콜/태그 이관은 **R6+R7**에서만 완성됨. 그 전까지는 세트 원시 데이터만 `/my/export` 대상.
- 10종 고정 운동은 **R8**에서만 확장됨. 그 전까지는 코어·컨디셔닝 커버 불가.
- ROI 증거(상담 전환·리텐션 숫자)는 **R9**에서만 계측됨. 그 전까지는 관장 체감치에 의존.

## 채택된 요구사항

- **run_id**: `pt-trainer-owner-01_20260424_104537`
- **title**: **R5 부분 구현 — 트레이너간 회원 접근 서버사이드 격리 + `/`·회원 접근 경로 UI 비가시화** (`require_member_access` 미들웨어 도입, 미소유 + 비관장 접근 시 403)

### 유래한 고객 pain + 근거 인용

유래한 페르소나: `pt-trainer-owner-01` (동네 소규모 헬스장 관장 겸 트레이너, 소속 트레이너 2~3명, PT 회원 ~50명) + 직접 stakeholder `sh-other-trainers` (소속 트레이너, influence 40, 거부권 성격).

시뮬 최종 판정: **실패 / stakeholders_persist_drop** — stakeholder가 3라운드 재설득 후에도 drop 52 → 60 → 68 → 69로 70 라인을 단 한 번도 넘지 않음. stakeholder 본인이 70 돌파 게이트 3개를 못박았고 그 중 **#2가 이번 티켓(R5 부분 구현 PR)**.

#### 해소하는 pain (`persuasion-data/runs/pt-trainer-owner-01_20260424_104537/report.md` 직접 인용)

- **`report.md` §가치제안 개선 포인트 1 — 언급 세션 수 6/8 (가장 지배적 쟁점, 58행)**
  > "**R5(트레이너간 회원 접근 격리)의 선행 live화** — 언급한 세션 수: 6 (01, 02, 04×3, 03×2). 가장 지배적 쟁점. 대표 발화: *'R5가 R1보다 선행되어야 하는데, 결정 권한은 내게 없고 관장님에게 있다'* (02), *'관장 대시보드 `?trainer_id=` 비교 API 재설계 + UI 트레이너별 평균치 비가시화까지'* (04_round2). 현 구조는 '서버 사이드 403만'으로 스코프가 축소돼 도구화 차단이 절반만 되는 설계."

- **stakeholder 초기 발화 (`02_stakeholder_sh-other-trainers.md` 17~18행)**
  > "N0(감사 로그 뷰어)의 한계. '관장이 언제 뽑아갔는가'를 사후 가시화할 뿐, 애초에 관장이 `?trainer_id=` 필터로 내 입력분만 골라서 뽑거나, 관장 대시보드에서 트레이너별 평균치를 비교하는 행위 자체를 막지는 못한다. … '감시 비대칭 1차 완화'는 맞지만 '해소'는 과장."

  > "R5(트레이너간 회원 접근 격리)가 아직 미live인데, 파일럿 5주 남은 동안 관장님이 1순위로 고를 후보는 PDF(R1)로 보인다. … 그러면 내 우려 1순위인 '트레이너 비교지표 도구화'는 본계약 이후로 밀리고, 그때부터 내가 반대해도 관장님은 이미 BET에 계약 묶여 있어서 내 영향력 효용이 급락한다. **순서가 바뀐 상태에서 accept하는 게 내 최대 손실 구간.**"

- **stakeholder 70 돌파 게이트 #2 명시 (`04_stakeholder_recheck_sh-other-trainers_round3.md` 37~40행)**
  > "**라운드4 즉시 72~75 전환 조건**: 1) 오늘 의사록 서명본 실물 확보 … 2) **iteration 5 kickoff PR 공개 약속 의사록 문구에 PR 수락 기준 명시 — '`members.owner_trainer_id` FK ADD 마이그레이션 스크립트 + `require_member_access` 미들웨어 초안 코드 + CI green'까지 의사록에 박히면 스텁 placeholder 방지.** 3) 계약서 조항 초안 10주차 제출 약속에 'stakeholder 수정 요구 반영권' 명시"

- **keyman의 R1 철회 + R5 swap 수용 (5c 3라운드 전반)** — `03_keyman_response_sh-other-trainers_round1~3.md`에 걸쳐 keyman이 본인 1순위 buy_trigger였던 R1(PDF)을 R5로 swap 수용. 즉 관장(decision_authority: full) + 소속 트레이너(거부권) **양측의 1순위 일치**.

- **이번 이행은 stakeholder가 "결과물 0개" 감점의 경계를 풀기 위한 필수 전제** (`04_stakeholder_recheck_sh-other-trainers_round3.md` 17행)
  > "3개 조건 전부 '경로 구체화'로 받았지만, 결과물은 아직 0개. (1)의사록 서명본 → '오늘 미팅 현장에서 받아오겠다', (2)iteration 5 kickoff PR → '9주차 시작일(1주 뒤)에 공개 브랜치', (3)계약서 조항 초안 → '10주차까지 제출 요구'. … **경로 구체화만으로 70을 주면 라운드2 판정 논리 자체가 무너진다**."

즉 이번 티켓은 (i) 시뮬 **1순위 블로커 (6/8 언급, 가장 지배적 쟁점)**, (ii) stakeholder가 명시한 **70 돌파 게이트 3개 중 유일한 기술 건**, (iii) keyman + stakeholder **양측 1순위 합치**, (iv) "약속 vs 이행 0건" 감점을 뚫기 위한 **iteration 5 kickoff PR 공개 약속의 실물 증거**. 구현은 `members.trainer_id`(iter 1부터 기보유)를 owner FK로 활용해 마이그레이션 불요, 헬퍼 1개 + 라우트 4개 가드 + `GET /` redirect 수정 + 테스트 11개로 스코프 명확.

### 구현 스케치

**스택**: 현 iteration 1~4 그대로 (FastAPI + SQLite + HTMX + Jinja2, Fly.io 단일 VM, `sqlite3` 표준 라이브러리 only). ORM 도입 금지 유지. 외부 의존 추가 0. **DB 마이그레이션 불요** (`members.trainer_id`가 iter 1부터 이미 owner FK로 작동).

#### 1. `app/auth.py` — 접근 체크 헬퍼 추가

```python
def require_member_access(request: Request, conn, mid: int) -> tuple[bool, int | None]:
    """(ok, status_code) 반환.
    - 미로그인 → (False, None): 호출측이 login_required_redirect() 사용.
    - 관장 → (True, None): is_owner=1 bypass 유지.
    - 회원 존재 + 소유 트레이너가 로그인 사용자 → (True, None).
    - 회원 부존재 → (False, 404).
    - 회원 존재 + 미소유 + 비관장 → (False, 403).
    """
    if not is_authenticated(request):
        return False, None
    if is_owner(request):
        return True, None
    user = current_user(request)
    row = conn.execute("SELECT trainer_id FROM members WHERE id=?", (mid,)).fetchone()
    if row is None:
        return False, 404
    if row["trainer_id"] == user["trainer_id"]:
        return True, None
    return False, 403
```

#### 2. `app/routes.py` — 4개 라우트에 가드 적용

대상: `GET /trainers/{tid}/members/{mid}/log`, `POST .../log`, `GET .../chart-data.json`, `GET .../dashboard`. 각 라우트 **진입 최전방**(폼 파싱·DB INSERT 전)에 다음 분기 삽입:

```python
with get_connection() as conn:
    ok, status = require_member_access(request, conn, mid)
    if not ok and status is None:
        return login_required_redirect()
    if not ok and status == 403:
        return PlainTextResponse("forbidden", status_code=403)
    if not ok and status == 404:
        return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
    # URL의 tid도 유효성 검증 (URL 위조 방지: tid가 소유 트레이너 ID와 불일치면 404 유지)
    member = conn.execute(
        "SELECT id, name FROM members WHERE id=? AND trainer_id=?", (mid, tid)
    ).fetchone()
    if not member:
        return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
```

- `POST /log`는 **폼 파싱·검증 전**에 가드. INSERT 시도 0건이 반드시 보장되어야 함(CTO 조건 4).
- 관장 bypass(`is_owner=True`)는 `require_member_access`에서 자동 처리.

#### 3. `GET /` — 로그인 트레이너의 첫 회원으로 redirect

- 현재: DB의 첫 트레이너 + 첫 회원으로 redirect → 타 트레이너 회원 ID 유출.
- 변경 동작:
  - 미로그인 → 기존대로 `/login`.
  - 관장 로그인(`is_owner=True`) → 기존과 동일(전체 첫 회원).
  - 일반 트레이너 → `members WHERE trainer_id=본인` 중 첫 회원으로 redirect.
  - 일반 트레이너 + 담당 회원 0건 → `HTMLResponse("<p>담당 회원이 아직 없습니다. 관장에게 요청하세요.</p>", status_code=200)`.

#### 4. `docs/spec.md` 개정 (CTO 조건 2)

- 99~103행 "트레이너간 회원 접근 격리" 섹션을 **"partial isolation (iter 5, live)"**으로 재작성. 주요 내용:
  - 비관장 트레이너는 본인 소유 회원만 `/trainers/{tid}/members/{mid}/*` 4개 라우트 접근 가능.
  - 미소유 시 **403** (존재 여부 은폐 안 함 — 감사 가시성 목적).
  - 존재하지 않는 mid는 **404**(기존 동작 유지, 403과 구분).
  - 관장은 is_owner bypass로 전체 접근 유지.
  - `GET /`는 로그인 트레이너의 첫 회원으로 redirect (관장만 전체 첫 회원).
  - **풀버전(R5-full)**: 회원 자가 대시보드 + 관장 UI 비가시화 구조 재설계 → **다음 스프린트 예약**.
- 113행 "명시적 제외 항목"에서 "R5에서 다룸"을 **"R5-full(풀버전)에서 다룸"**으로 정밀화.
- "라우트 목록"에는 신규 라우트 없음(기존 4개에 가드만 추가).
- "다음 스프린트 예약 티켓" 섹션 갱신 (CTO 조건 6):
  - **R5-full — 회원 자가 대시보드 + 관장 트레이너별 비교 UI 비가시화 구조**.
  - 주: **향후 관장 대시보드에 "트레이너별 평균치 비교" UI를 신규 도입할 때는 R5-full 게이트가 선행되어야 한다** — stakeholder 개선 포인트 #1의 "UI 비가시화" 축은 현재 "비교 UI 부재" 상태로 satisfy되어 있으므로, 비교 UI 신규 도입 자체가 stakeholder 재설득 이슈를 재활성화한다.

#### 5. 테스트 (`tests/test_member_access.py` 신규, mock 금지, tmp_path SQLite)

1. 트레이너A 로그인 → 트레이너B 회원의 `/log` GET → **403** (body `"forbidden"`).
2. 트레이너A 로그인 → 트레이너B 회원의 `/log` POST → **403** (+ `pt_sessions` / `session_sets` INSERT 0건 검증, **CTO 조건 4**).
3. 트레이너A 로그인 → 트레이너B 회원의 `/chart-data.json` → **403**.
4. 트레이너A 로그인 → 트레이너B 회원의 `/dashboard` → **403**.
5. 트레이너A 로그인 → 트레이너A 본인 회원 → **200** (regression).
6. 관장 로그인 → 타 트레이너 회원 모든 4개 라우트 → **200** (bypass 유지, regression).
7. 미로그인 → **303 → /login** (기존 동작, 모든 4개 라우트).
8. 존재하지 않는 mid → **404** (기존 동작, **403과 구분**, **CTO 조건 1**).
9. `GET /` 트레이너A 로그인 → A의 첫 회원 URL로 redirect(타 트레이너 회원 ID 미노출).
10. `GET /` 관장 로그인 → 전체 첫 회원으로 redirect (기존 동작 유지).
11. `GET /` 회원 0건 트레이너 로그인 → "담당 회원이 아직 없습니다" 안내 페이지 200.

Playwright e2e 테스트는 이번 스프린트 범위 외.

#### 6. 문서 수정

- `docs/spec.md` — 위 4번 참조.
- `docs/testing.md` — "테스트 구성"에 `tests/test_member_access.py` 추가 + 11 시나리오 요약.
- `docs/user-intervention.md` — **변경 없음**. 새 env/secret/수동 스크립트 없음.

#### 7. 인간 개입 지점

**없음.** `fly deploy`만 관장이 실행 (기존 절차). DB 마이그레이션 불요 (`members.trainer_id` 이미 존재).

### CTO 승인 조건부 조건

`tech-critic-lead` 결재에서 **승인 / 신뢰도 88**로 통과. 부과된 6개 조건:

1. **404 vs 403 구분 엄격 유지** — 존재하지 않는 mid는 404, 존재하나 타 트레이너 소유는 403. **테스트 #8이 이 구분을 반드시 검증**.

2. **`docs/spec.md` 99-103행 + 113행 동기 갱신 필수** (R5 → R5-full 재명명 포함). 코드만 고치고 spec이 permissive로 남으면 stakeholder가 "문서-코드 불일치"로 재감점할 수 있음.

3. **`require_member_access` 반환 패턴 일관성** — `(bool, int|None)` 튜플 반환으로 최초 구현. 호출측 4곳에서 동일 분기 블록이 **3줄 넘게 복제되면** PR 리뷰 시점에 헬퍼가 Response를 직접 반환하도록(또는 `raise HTTPException`) 리팩터 고려. 최초 구현은 순수 반환 패턴으로 통과 가능.

4. **POST /log 403 시 DB 변경 0건 엄격 검증** — 가드는 **폼 파싱/검증 전 라우트 진입부**에 두어야 함. `pt_sessions`·`session_sets` INSERT 0건을 테스트 #2가 COUNT 쿼리로 검증.

5. **PR description 문구** — stakeholder가 04_round3 39행에서 명시 요구한 문구 "`members.owner_trainer_id` FK ADD 마이그레이션"은 **현 DB상 이미 `members.trainer_id`로 기보유**이므로, PR 본문에 `"마이그레이션 불요 — 기존 members.trainer_id가 owner FK로 기 작동(iter 1부터)"`을 명시해 스텁 의심을 차단. 의사록에도 동일 근거 적시.

6. **R5-full 예약 조건 명문화** — 관장 bypass(is_owner) 경로 유지의 부작용으로, 현재 "UI 비가시화" 축은 **"관장 비교 UI 부재로 satisfy"** 상태. 향후 관장 대시보드에 "트레이너별 평균치 비교" UI를 신규 도입할 때 **R5-full 게이트가 선행되어야 함**을 `docs/spec.md` "다음 스프린트 예약 티켓" 섹션에 추가.
