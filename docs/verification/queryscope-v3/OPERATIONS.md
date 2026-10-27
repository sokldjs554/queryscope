# v3 운영 확인 범위

2026-10-27 한국 시각. 로컬 검증과 실제 공개 운영을 구분한다.

- 전체 pytest: **378 passed, 1 skipped, 2 deselected**, 84.83초. [기록](checks/pytest.txt).
- 기본 검색 평균 nDCG0.5839 유지. [기록](checks/baseline.txt).
- 기존 v1/v2/실제 API와 재생 원자료83파일의 바이트를 base `e8f967c`와 비교해 모두 동일. [보존 해시](preservation.json).
- v2 오프라인 실험을 재실행했고 검색·순위·수정·novelty·과거 응답 사후검증 6개 결과 영역이 모두 동일. [비교](v2-reproduction.json). v2 무료 준비물24개의 입력·컨텍스트·요청 payload·해시도 동일하게 재현했다([기록](prepared-v2-reproduction.json)).
- 1440/320/390/650px에서 [v3 비교](browser/checks.json)와 [기존 재생](browser-replay/checks.json)을 검사했다. 입력24개 선택 목록, 5계열(n=0 포함), 순위24행, 원문 펼침, 근거 없는 경우, 범위 밖, 다운로드·취소·로딩 실패·가로 넘침·JS 오류를 확인했다. 실제 생성 화면 상태 전환에 한해 명시적 테스트 응답을 사용했으며 모델 성능에 포함하지 않았다.
- 실제 loopback HTTP: 준비2264.32ms, 준비 후 GET120회 모두200, p50 0.892ms / p95 **1.822ms** / 최대4.154ms. 기본 생성 요청503, 빈 입력422, 생성 요청 집계0. [원자료](operations/operations.json). 정적 자료·상태 조회이며 모델 지연이나 공개 SLA가 아니다.

## 근거 검색 계산 지연

발췌 후보 구간의 분석 토큰을 최대512항목으로 캐시한다. 동일본문·동일분석기에서만 재사용하며 발췌와 원문 위치가 변하지 않는지 검사했다. 개발24질의를 각 전략에서 한번씩 실행 순서를 번갈아 총48회 측정했다. v2 p50 12.081ms / p95 287.680ms / 최대290.940ms, v3 p50 11.912ms / p95 **90.661ms** / 최대163.792ms. [원자료](latency/context-latency.json).

이 비교는 관측 신호 수정과 캐시를 합친 결과로 캐시 단독 효과가 아니다. 단일 로컬 프로세스·72상품·각 질의1회이며 실행 시 다른 로컬 HTTP 검사가 겹쳤다. 반복 독립 측정·동시 부하·공개 생성 지연으로 일반화하지 않는다. 초기화와 캐시 워밍의 영향이 포함된다.

## 공개 주소 접근 및 배포

- https://queryscope-zwia.onrender.com/ (과거 실제 API 응답 재생)
- https://queryscope-zwia.onrender.com/evaluation-v3.html (이번 오프라인 비교)
- v1/v2 비교 주소와 저장 결과는 보존한다.

21:22:56 한국 시각에 기존 공개 v2 주소로 실제 HTTPS 접속을 시도했지만 실행 환경 프록시가 CONNECT403을 반환했다. 공개 서버의 HTTP403을 확인한 것이 아니라 서버 연결 전 프록시 거부이다. v3 주소도 같은 프록시 거부였고 웹 도구도 해당 URL 접근 불가를 보고했다. [접속 기록](checks/public-access-before-deploy.txt). 제한을 우회하지 않았다. 외부 브라우저 접근·HTTP200·가용성을 검증한 것으로 표시하지 않는다.

Render는 사용자 지정 `my2 workspace` (`tea-db9hb2dg1s2s738nd1a0`), 정적 서비스 `srv-dbg6rtflk1mc73cok690`이다. 자동배포는 꺼져 있다. 저장 HTML/JS/JSON만 게시하며 API 키·생성 서버는 게시하지 않는다. 최종 CI·배포 ID/상태는 아래에 기록한다.

[최종 코드 검토](REVIEW.md)에서는 차단 이슈0건이며 별도 집중 테스트17개와 원자료 대조를 통과했다. 독립 인간 의미 평가와는 다르다.

## 미실행

추가 유료 호출0, 새 모델 답0. [v3 준비물](llm-prepared-v1/requests.json)은24개 null/not_run이고 승인 템플릿은false이다. 독립 인간 의미/정답 평가, 실제 모델 진단/보류/잘못된 수정률, 실제 공급자 오류·지연, 고객 데이터·공개 장기 운영은 미확인이다. [별도 승인 전 실행 금지인 계획](PAID-EVALUATION-PROPOSAL.md)을 참고한다.

## 원격 CI에서 발견한 문서 회귀

첫 원격 실행 [40504609166](https://github.com/sokldjs554/queryscope/actions/runs/40504609166)의 Ubuntu·Windows 테스트가 같은 문서 계약 검사에서 실패했다. README를 v3 결과 중심으로 다시 쓰면서 기존 카탈로그72건·평가36질의(건강20+실패16) 규모 문장을 빠뜨렸다. 검색 코드 실패가 아니라 문서 계약 검사 실패이다. 로컬 전체 검사 이후 문서 수정에 해당 검사를 다시 실행하지 않은 검증 공백이었다.

같은 테스트를 로컬에서 재현([RED](checks/readme-red.txt))하고 README에 기존 개발·회귀 자료 규모를 다시 명시했다. 테스트를 약화하거나 과거/신규 평가를 합치지 않았다. 수정 뒤 전체 검사 **378 passed, 1 skipped, 2 deselected (84.32초)**를 확인했다([최종 로컬 로그](checks/pytest-final.txt)). 원격 CI도 다시 실행해 아래와 같이 통과했다. 초기 통과 로그와 실패 이력을 지우지 않는다.

Render 배포 `dep-dbg9k5ek1f9s73boe6b0`는 코드 `b3cc7b8`에서 21:33:38 한국 시각에 **live**였다([배포 기록](deployment.json)). 그 뒤 수정한 README 규모 설명은 정적 게시 폴더 밖이며 데모·소스·저장 결과는 동일하다. 배포 후 v3 HTTPS 접근도 CONNECT403으로 실패했다([기록](checks/public-access-after-deploy.txt)). 배포 live를 공개 HTTP 정상 동작으로 해석하지 않는다.

## 최종 CI 및 공개 버전

수정 커밋 `652f38d1afda215e9ccad19683f70cac4113e617`의 [CI40505257938](https://github.com/sokldjs554/queryscope/actions/runs/40505257938)는 Ubuntu·Windows 테스트와 검색 품질 게이트가 모두 성공했다(21:39:57 한국 시각). 각 OS 테스트359 passed, 2 skipped; CI는 api/mcp/dev만 설치하며 로컬 선택 의존성 구성과 달라 테스트 수를 합산하지 않는다. [최종 CI 원자료](ci-final.json).

Render가 게시한 `b3cc7b8`과 최종 CI `652f38d`의 src/tests/scripts/.github/web 차이는 없다. 이후 CI/배포 확인을 문서에 추가한 커밋은 실행 코드와 공개 정적 자료를 바꾸지 않으며 자동배포도 꺼져 있다. 최종 공개 접속은 여전히 프록시 제한으로 확인하지 못했다. 로컬 스크린샷과 Render live/CI success를 외부 HTTP200으로 대체하지 않는다.
