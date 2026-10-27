# QueryScope 운영과 재현

## 기본 실행

README의 `pip install -e '.[api]'` 후 `python -m searchclinic.api.explanation_api`.
서버는 127.0.0.1:8000, 데모는 /demo/, 새 평가는 /demo/evaluation.html이다.
정적 화면만 보려면 `python -m http.server 8001 --bind 127.0.0.1 --directory src/searchclinic/web` 후 http://127.0.0.1:8001/.

정적 배포는 HTML/JS/저장 JSON만 제공한다. API 키·운영 토큰·생성 서버를 배포하지 않는다. 새 API 생성 선택지는 상태 API가 live 활성임을 반환할 때만 열린다. 원본 PR의 저장 응답과 새 오프라인 결과를 서로 다른 화면으로 표시한다.

## 비용

기존 승인 24회는 소진됐다. OpenAIExplainer의 기본 Budget은 0회이며 종료된 evaluate_alba.py --live는 요청 전 중단된다. 과거 유료 workflow는 실행 폴더에서 제거하고 기록으로 보존했다.

새 승인 전에는 CLINIC_ENABLE_LIVE를 활성화하거나 CLINIC_MAX_CALLS를 올리지 않는다. 추후 실제 생성은 서버의 OPENAI_API_KEY, CLINIC_ENABLE_LIVE=1, 최소 24자 CLINIC_LIVE_TOKEN, 별도 CLINIC_BUDGET_PATH, 승인된 CLINIC_MAX_CALLS가 필요하다. 새 기본값 0은 의도된 동작이다. 브라우저에 제공하는 것은 운영 토큰이며 API 키가 아니다.

## 검증

- `python -m pytest -q`: 기본 단위·통합 검사. 선택 패키지/slow 범위는 별도.
- `clinic baseline`: 기존 36개 평균 nDCG 0.5839 유지 확인.
- `python scripts/evaluate_queryscope.py --output work/run-2`: SHA 검증 후 새 무료 검색/히트 비교/기존 감사. 기존 결과 디렉터리 덮어쓰기 거절.
- `python scripts/verify_queryscope_operations.py --output work/ops-2`: 실제 로컬 HTTP 프로세스, 120회 GET 및 503/422. 포트 8766 사용.
- `node scripts/browser_queryscope.cjs`: Playwright 필요. 시스템 Chromium이면 CHROME_EXECUTABLE 지정. 포트 8765 사용. 화면 전환용 live 응답만 테스트 대역.

운영 지표 /explanation-status는 현재 프로세스의 생성 요청·응답 상태·오류·busy·게이트 요청 수와 최근 100회 지연 p95이다. 외부 요청을 받은 적 없는 기본 실행의 생성 p95는 null이 맞다. 로컬 HTTP 측정 수치와 섞지 않는다. 게이트 수는 중복 요청도 포함한 요청 단위이다.

다중 서버·사용자별 인증·외부 알림·분산 추적·공개 생성 API의 SLO를 구현/실증했다고 주장하지 않는다. 생성 실패/429 동시 요청/취소 전환은 로컬 fixture 검사이며 실제 공급자 장애 실험이 아니다.
