# v2 운영 확인 범위

2026-10-27 (한국 시각). 로컬과 공개 운영을 구분한다.

## 실제 실행한 로컬 검사

- 전체 pytest: 370 passed, 1 skipped, 2 deselected (79.59초). [기록](checks/pytest.txt).
- 기본 검색 기준선 평균 nDCG 0.5839 유지. [기록](checks/baseline.txt).
- 실제 loopback HTTP: 준비2573.65ms, 준비 이후 순차 GET120회 모두200, p50 1.204ms / p95 **3.010ms** / 최대6.097ms. 기본 생성 요청503, 빈 입력422. 생성 요청 집계0, 생성 지연 p95=null. [원자료](operations/operations.json).
- HTTP 수치는 정적 파일·상태 조회이다. 새 관측 검색 계산이나 실제 모델 응답·공개 서비스 SLA를 측정한 것이 아니다.
- 브라우저: 1440/320/390/650px에서 v2 24개 입력 비교·5개 계열·3개 개발 수정·24개 순위행·원문 펼침·자료 로딩 실패·가로 넘침·JS 오류를 검사했다. [v2](browser/checks.json), [기존 응답/취소/오류/내보내기](browser-replay/checks.json).
- 첫 v2 브라우저 검사에서 Playwright의 option `isDisabled` 판정 대신 실제 DOM `disabled` 속성을 확인하도록 검사 코드를 수정했다. 제품의 유료 생성 경로를 활성화하지 않았다. 실제 생성 상태 전환 테스트만 명시적 테스트 대역을 사용했다.

## 관측·근거 검색 계산의 로컬 지연

별도로 개발24질의를 각 방식에서1회씩, 실행 순서를 번갈아 총48회 context 생성했다. 모델과 네트워크는 사용하지 않았다. 기존 방식 p50 0.835ms / p95 2.072ms, 보완 방식 p50 13.871ms / p95 300.284ms이다. 모든48회가 완료됐다. 72상품의 단일 프로세스 수치이며 동시 부하나 공개 API 지연이 아니다. 근거 검색 보강에는 추가 계산 비용이 있음을 드러낸다. [원자료](operations/context-latency.json). 재현: `python scripts/measure_queryscope_context.py --output work/context-latency`.

## 공개 주소 접근

- https://queryscope-zwia.onrender.com/
- https://queryscope-zwia.onrender.com/evaluation.html (v1 보존)
- https://queryscope-zwia.onrender.com/evaluation-v2.html (v2)

이번에도 공개 주소를 직접 확인하려 했으나 실행 환경 프록시가 CONNECT 403을 반환했다. 웹 연결 도구도 root와 v1 경로에 접근하지 못했다. 네트워크 제한을 우회하지 않았으며 외부 브라우저 접속/HTTP200/가용성을 확인했다고 주장하지 않는다.

기존 Render 사이트는 사용자 지정 `my2 workspace`, service `srv-dbg6rtflk1mc73cok690`, 자동배포 꺼짐이다. 이번 v2의 배포·CI 상태는 작업 완료 후 이 문서에 추가한다. 정적 파일만 게시하며 API 키와 생성 서버는 배포하지 않는다. v1의 기존 배포 기록은 변경하지 않는다.

## 실제 모델 실행 제한

추가 호출0. 무료 준비물은 [llm-prepared-v1](llm-prepared-v1/)이며 모든 답변이 null/not_run이다. [별도 승인 계획](PAID-EVALUATION-PROPOSAL.md) 없이 유료 실행하지 않는다. 24회의 실행 코드에 대한 테스트는 임시 폴더의 공급자 대역으로만 수행됐으며 실제 모델 품질/장애/지연 성과가 아니다.

공개 생성 API 부하, 장기 운영, 분산 집계, 독립 인간 의미 평가와 실제 고객 성과는 여전히 미검증이다.
