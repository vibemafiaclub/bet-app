# Phase 3: 대시보드 뷰 + chart-data.json 엔드포인트

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` — 특히 "차트 데이터 계약" 섹션 (JSON 스키마 정확히 이 형태여야 함)
- `/docs/testing.md` — 빈 member 케이스 처리 요구사항
- `/tasks/0-pt-mvp/docs-diff.md` — 이번 task의 문서 변경 기록

이전 phase 산출물 (반드시 코드를 읽고 이해하라):
- `/app/main.py`, `/app/auth.py`, `/app/routes.py`
- `/app/aggregates.py` (Phase 1에 구현된 `max_weight_per_session`, `total_volume_per_session`)
- `/app/templates/base.html`, `/app/templates/log.html`
- `/tests/conftest.py` (client / authed_client fixture)

`app/aggregates.py`의 두 함수 시그니처와 반환 포맷을 정확히 읽고 그걸 JSON으로 변환하는 얇은 층만 작성하라.

## 작업 내용

### 1. chart-data JSON 엔드포인트

`app/routes.py`에 추가 (또는 `app/chart.py`로 분리 — 판단은 짧게):

- `GET /trainers/{tid}/members/{mid}/chart-data.json` (인증 필요)
- 응답 스키마 — `/docs/spec.md` "차트 데이터 계약" 섹션과 **한 글자도 다르지 않게**:
  ```json
  {
    "member": {"id": 1, "name": "회원A"},
    "max_weight": {
      "labels": ["2026-03-27", "2026-03-30", ...],
      "datasets": [
        {"label": "스쿼트", "data": [60, 62.5, 65, ...]},
        {"label": "벤치프레스", "data": [50, 52.5, null, ...]}
      ]
    },
    "total_volume": {
      "labels": ["2026-03-27", "2026-03-30", ...],
      "data": [1200.0, 1400.0, ...]
    }
  }
  ```
- 처리 로직:
  1. member 존재 안 하면 404.
  2. `max_weight_per_session(conn, mid)` 결과를 그룹핑 → pivot:
     - 모든 session_date를 오름차순 distinct list로 뽑아 `max_weight.labels`
     - 각 운동(해당 회원이 기록한 운동만)에 대해, 각 label 날짜에 그 운동의 max_weight 값 또는 `null`
     - `datasets`는 운동명 오름차순으로 정렬
  3. `total_volume_per_session(conn, mid)` 결과는 동일 labels 순서로 값 추출. 해당 날짜에 총 볼륨이 여러 번(같은 날 세션 2개)이면 **합산**해서 1개 값으로.
  4. `max_weight.labels`와 `total_volume.labels`는 항상 동일해야 한다 (같은 session_date 집합).
  5. **세션 0건 회원**: `labels: []`, `datasets: []`, `data: []`. 예외 던지지 마라.

### 2. 대시보드 HTML — `app/templates/dashboard.html`

`extends base.html`. 내용:
- 상단: 회원 이름 + "이 회원 로그 입력" 링크
- `<canvas id="max-weight-chart" width="800" height="400"></canvas>`
- `<canvas id="total-volume-chart" width="800" height="400"></canvas>`
- Chart.js CDN script (버전 pin — 예: `https://cdn.jsdelivr.net/npm/chart.js@4.4.9/dist/chart.umd.min.js`). 정확한 URL은 `app/templates/dashboard.html` 내부에 상수처럼 하드코딩. 버전 숫자 패치까지 찍어라.
- 페이지 로드 inline script:
  ```js
  fetch(window.location.pathname.replace('/dashboard', '/chart-data.json'))
    .then(r => r.json())
    .then(d => {
      new Chart(document.getElementById('max-weight-chart'), {
        type: 'line',
        data: { labels: d.max_weight.labels, datasets: d.max_weight.datasets },
        options: { responsive: false, plugins: { title: { display: true, text: '운동별 최대 중량 추이 (kg)' }}}
      });
      new Chart(document.getElementById('total-volume-chart'), {
        type: 'line',
        data: { labels: d.total_volume.labels, datasets: [{ label: '세션당 총 볼륨', data: d.total_volume.data }]},
        options: { responsive: false, plugins: { title: { display: true, text: '세션당 총 볼륨 (kg × reps)' }}}
      });
    });
  ```
- 빈 member면 `fetch` 결과 labels가 빈 배열 → Chart.js는 빈 차트를 그린다(터지지 않음). 그대로 둔다.

라우트: `GET /trainers/{tid}/members/{mid}/dashboard` (인증 필요)
- member 존재 확인(없으면 404), 템플릿 렌더.

### 3. log.html 연동

Phase 2에서 만든 `log.html`의 상단 링크가 `/trainers/{tid}/members/{mid}/dashboard` 로 이어지도록 되어 있는지 확인. 없으면 추가.

### 4. 테스트

`tests/test_dashboard.py` 신규 — `authed_client` + `temp_db` 기반:

CTO 조건부 조건 #3: 빈 member 케이스 반드시 포함.

케이스:
1. `test_empty_member_returns_empty_contract` — 방금 만든 member(세션 0건) → GET chart-data.json → 200 + 정확히 `{"member":{"id":M,"name":"..."}, "max_weight":{"labels":[],"datasets":[]}, "total_volume":{"labels":[],"data":[]}}`
2. `test_chart_data_pivot_shape` — 2개 세션(날짜 다름)에 2개 운동씩 세팅 → labels 2개, datasets 2개, 각 dataset.data 길이 2
3. `test_chart_data_labels_match` — `max_weight.labels == total_volume.labels`
4. `test_chart_data_max_weight_is_max_of_sets` — 한 세션에 스쿼트 60x5, 70x3 → dataset["스쿼트"].data[0] == 70
5. `test_chart_data_volume_sums_reps` — 스쿼트 60x5, 70x3 → total_volume.data[0] == 60·5 + 70·3 == 510
6. `test_chart_data_missing_exercise_yields_null` — 운동 A만 세션1, B만 세션2 → datasets[A].data = [값, null], datasets[B].data = [null, 값]
7. `test_dashboard_html_renders_canvases` — GET dashboard → 200 + HTML에 `id="max-weight-chart"` 및 `id="total-volume-chart"` 포함
8. `test_dashboard_includes_chartjs_cdn` — HTML에 `chart.js@4.` 문자열 포함 (버전 pin 확인)
9. `test_unknown_member_returns_404` — GET /trainers/1/members/99999/chart-data.json → 404
10. `test_protected_route_requires_auth` — 미인증 → 303 /login

## Acceptance Criteria

```bash
$RUN="uv run"; command -v uv >/dev/null 2>&1 || RUN=""

$RUN pytest tests/test_dashboard.py -v

# 기존 테스트 여전히 통과
$RUN pytest tests/test_aggregates.py tests/test_auth.py tests/test_log_routes.py -v
```

## AC 검증 방법

위 커맨드 모두 통과하면 `/tasks/0-pt-mvp/index.json`의 phase 3 status를 `"completed"`로 변경하라.
수정 3회 이상 실패 시 status `"error"` + `"error_message"` 기록.

## 주의사항

- **spec.md의 JSON 스키마와 한 글자도 달라지면 안 된다.** 키 이름(`max_weight`/`total_volume`/`labels`/`datasets`/`data`/`label`)을 camelCase나 다른 표기로 바꾸지 마라.
- **labels는 오름차순.** 내림차순 하지 마라.
- **같은 날짜에 세션 2개**: max_weight은 각 exercise별 해당 날짜 최대값 1개로, total_volume은 합산 1개로. 이 규칙은 테스트에서 강제되지 않더라도 지켜라 (운영 실수 방지).
- **null 처리.** 특정 운동이 특정 세션에 없으면 `null`. 0이나 빈 문자열로 대체하지 마라 (Chart.js가 null은 선을 끊어주는데, 0이면 0값으로 그려져서 오해 소지).
- **외부 http 호출 금지.** Chart.js는 CDN URL로 HTML에만 박아라. 서버에서 fetch하지 마라.
- **템플릿 디렉토리 변경 금지.** 계속 `app/templates/` 사용.
- **ORM 도입 금지.** `sqlite3` 표준 라이브러리만.
- 기존 테스트(`test_aggregates.py`, `test_auth.py`, `test_log_routes.py`)를 깨뜨리지 마라.
- 대시보드에서 seed 데이터가 아닌 **테스트 내에서 직접 INSERT한 데이터**로만 단언하라. seed 의존 금지.
