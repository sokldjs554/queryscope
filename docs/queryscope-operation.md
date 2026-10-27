# QueryScope 운영과 재현

최신 v2 검사·배포 범위는 [v2 운영 기록](verification/queryscope-v2/OPERATIONS.md), 현재 모델 평가 준비는 [새 승인 계획](verification/queryscope-v2/PAID-EVALUATION-PROPOSAL.md)을 따른다. 아래 초기 공개 배포 정보는 v1 시점 기록이다.

## 기본 실행

README의 `pip install -e '.[api]'` 후 `python -m searchclinic.api.explanation_api`.
서버는 127.0.0.1:8000, 데모는 /demo/, 새 평가는 /demo/evaluation.html이다.
정적 화면만 보려면 `python -m http.server 8001 --bind 127.0.0.1 --directory src/searchclinic/web` 후 http://127.0.0.1:8001/.

정적 배포는 HTML/JS/저장 JSON만 제공한다. API 키·운영 토큰·생성 서버를 배포하지 않는다. 새 API 생성 선택지는 상태 API가 live 활성임을 반환할 때만 열린다. 원본 PR의 저장 응답과 새 오프라인 결과를 서로 다른 화면으로 표시한다.

## 공개 정적 데모의 확인 범위

- 주소: https://queryscope-zwia.onrender.com/ (새 평가: `/evaluation.html`).
- 사용자 선택 작업공간 `my2 workspace`, 새 Render 정적 사이트 `queryscope`. 기존 서비스는 변경하지 않았다.
- 배포 코드 `714600fb3eec47bcef9f983c96dbf79278bc1916`, Render 상태 `live`, 완료 시각 2026-10-27 09:25:28 UTC.
- 게시 디렉터리 `src/searchclinic/web`, 빌드 명령 `true`, `SKIP_INSTALL_DEPS=true`. 자동 배포는 꺼 두어 검증한 코드 버전을 유지한다.
- 공개 주소의 직접 HTTP 확인은 실행 환경 프록시에서 CONNECT 403으로 차단됐고 웹 연결 도구도 접근 불가였다. Render 배포 성공을 공개 접속 검사나 가용성 측정으로 간주하지 않는다. 로컬 브라우저 검사 기록은 별도로 보존한다.
- 같은 코드의 GitHub Actions Ubuntu·Windows 테스트와 검색 품질 게이트가 모두 성공했다. 이후 링크·배포 기록만 추가한 문서 커밋은 이 배포에 포함되지 않는다.

[배포 기록](verification/queryscope-v1/deployment.json) · [CI 기록](https://github.com/sokldjs554/queryscope/actions/runs/40480583240).

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
