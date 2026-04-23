---
persona_id: pt-trainer-owner-01
version: 1
created_at: 2026-04-24
updated_at: 2026-04-24
company_meta:
  industry: fitness / 개인 PT
  size: 1-5
  stage: 소규모 개인사업자
keyman:
  id: km
  role: 관장 겸 트레이너
  decision_authority: full
  budget_range_krw: "인당 월 ~1만원 (가치 미검증 현재)"
  tech_literacy: low-moderate
  risk_preference: conservative
  personality_notes: |
    회원 유치·리텐션을 사업의 핵심 관심사로 둔다. 성과 자료의 중요성을 인식하나,
    인바디 수치만으로는 PT 품질을 증명하기 어렵다는 구조적 한계를 스스로 인지.
    회원 생활습관 변화가 효과의 큰 부분이라는 인과에 공감대 형성이 쉬움.
    새 도구 적극 테스트형이 아님 — 회원에게 사용을 강요하는 번거로움이 심리적 저항.
    살세맨(사용자)에 대한 개인적 신뢰는 85점 수준이나, 이것이 무조건적 도입을
    뜻하지 않으며 "회원 시범 적용에 쓸만함"이 납득되어야 움직인다.
  current_pains:
    - "신규 회원 유치용 성과 자료 빈약 — 인바디 측정 결과뿐"
    - "인바디 수치 변화는 회원 생활습관에 크게 좌우되어 PT 품질을 제대로 대변 못함"
    - "Rappo: 회원 발전 추이 가시화 없음"
    - "Rappo: 채팅형 UI로 일지/기록이 누적만 되고 과거 열람이 어려움"
    - "회원 리텐션 향상 방법 고민"
  existing_alternatives:
    - "Rappo (현재 사용중) — 공유 캘린더 + 채팅 일지, 운영관리 도구 역할도 겸함"
  buy_triggers:
    - "회원 발전 그래프를 잠재고객에게 보여줄 수 있는 가시화 수단"
    - "PT 외 시간 회원 생활습관을 시스템이 대신 관리해 주는 도구"
    - "인바디 이상의 설득력 있는 다차원 성과 지표"
  reject_triggers:
    - "Rappo의 공유 캘린더 기능을 대체 못하면 이중 운영 부담"
    - "가격이 Rappo 대비 부담스러우면"
    - "회원에게 사용을 강요해야 하는 번거로운 UX"
  communication_style: "핵심 포인트만 요약해 전달"
trust_with_salesman: 85
stakeholders:
  - id: sh-other-trainers
    role: 소속 트레이너
    relation_to_keyman: direct
    influence: 40
    decision_weight_hint: |
      키맨 본인 회원만 시범 적용 시 우회 가능 → 일상 영향력은 낮음.
      그러나 강한 반대가 나오면 도입 자체를 블록할 수 있는 거부권 성격의 영향력.
    tech_literacy: unknown
    personality_notes: "unknown — 다음 인터뷰에서 확인 필요"
    trust_with_keyman: unknown
    connected_to: []
  - id: sh-members
    role: PT 회원 (end user)
    relation_to_keyman: downstream
    influence: 30
    tech_literacy: unknown
    personality_notes: |
      BET AI 트레이너의 실사용자. 생활습관 개입을 회원이 받아들일지가 downstream 리스크.
      개인 구매자는 아니지만 리텐션·만족도·시범 체감으로 키맨의 지속 도입 판단에 간접 영향.
    trust_with_keyman: unknown
    connected_to: []
competing_solutions:
  - name: Rappo
    usage: using
    strengths:
      - "PT 일정 공유 캘린더 + 회원 자가 취소 기능 (키맨의 Rappo 잔류 이유)"
      - "채팅 기반 일지 입력 UX 익숙함"
      - "운영관리 도구 역할도 겸함"
    weaknesses:
      - "회원 발전 추이 가시화 없음"
      - "채팅형 UI → 과거 기록 열람 어려움"
    switching_cost: high
---

# 키맨 배경

사용자의 PT 트레이너이자 동네 소규모 헬스장을 직접 운영하는 관장 겸 트레이너.
당장의 지불의사는 없으나, PT 서비스 디지털화에 대한 관심이 뚜렷하며 Rappo를
이미 도입해 운영관리·일정·일지 용도로 사용 중.

PT 회원 수는 **약 50명으로 가정** (실측 미확인 — `open-questions.md` 참조).

## Pain의 구조

키맨의 pain은 두 층위로 나뉜다.

1. **외부 소구 pain** — 잠재회원에게 "우리 PT 품질이 좋다"를 증명할 성과자료 부재.
   인바디 수치는 표면적이며, 실질 결과는 회원 생활습관 변화에 크게 좌우된다는
   인과관계의 왜곡이 현재 성과 자료의 한계.
2. **기존 도구 pain** — Rappo의 회원 데이터 표현 한계 (추이 가시화 없음,
   채팅형 이력의 과거 열람 불편). 단, 공유 캘린더는 Rappo 잔류의 강력한 이유.

## BET 가치제안과의 접점

- "발전 그래프 가시화" = 외부 소구 pain 정면 해소
- "AI 트레이너가 PT 외 시간 생활습관 관리" = 키맨이 스스로 진단한 "실질 효과의 큰 부분"을 시스템화
- "데이터 기반 개인화" = 인바디 이상의 다차원 성과지표 확보

## 리스크 / 반대 지점

- **Rappo의 캘린더 기능 부재**가 가장 큰 이탈 저항. BET이 캘린더를 제공하지
  않으면 "Rappo 유지 + BET 병행" 이중 부담 → 지불의사 약화.
- **지불 주체 구조**: BET 과금은 "등록 고객 1인당 월 과금" → 회원 수가 적은
  (a)형 소규모 관장에게는 고정비화 여부가 민감. 현재 체감 지불 상한은 인당 월
  1만원 수준 (가치 미검증 상태 기준).
- **회원 사용 강요 부담**: 키맨이 새 도구 적극 테스트형이 아닌 주된 이유.
  회원에게 앱 설치·로그·습관 입력을 강요해야 한다면 저항이 크다.
- **downstream 리스크**: 회원 생활습관 개입을 회원 본인이 받아들일지는 별도
  stakeholder 세션에서 검증 필요.

## 조직 역학 메모

- `decision_authority: full` — 재무·계약 결정권은 키맨 단독.
- 소속 트레이너는 **일상 영향력은 낮지만 거부권 성격의 영향력 보유**:
  키맨 본인 회원만 시범 적용할 경우 우회 가능하나, 다른 트레이너가 강하게
  반대하면 도입 자체가 블록될 수 있다.
- 회원 인원은 downstream 리스크의 규모를 가늠하는 지표이지 직접 의사결정자는 아님.
