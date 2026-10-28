# v4 실제 평가와 새 결과 화면의 운영 검증

2026-10-29(Asia/Seoul). [실제 분석](ACTUAL-API.md), [원응답](actual-api-v1/results.json), [AI 의미 평가](AI-SEMANTIC-REVIEW.md)를 서로 구분합니다. 이 문서는 이번 승인 실행과 후속 공개 화면의 확인 범위를 기록합니다. 이전24응답 재검사 화면의 배포는 [이전 운영 기록](OPERATIONS.md)에 보존했습니다.

## 승인된 실제 실행

사용자는 고정 입력48건, 모델 `gpt-5.4-mini-2026-03-17`, 최대48회·예약 상한$0.60·자동 재시도 없음의 범위를 승인했습니다. [승인 커밋](https://github.com/sokldjs554/queryscope/commit/a961c5aac0e747fd504f1e3902b83d7afb90aeda)과 [승인 파일](live-approval.json)을 보존합니다.

[실행40723946171](https://github.com/sokldjs554/queryscope/actions/runs/40723946171)은 첫 실행에서 성공했습니다.48시도·48응답, API 오류0·출처 연결 오류0, 모든 응답의 사용량 수신을 확인했습니다. 사용량에 공식 단가를 적용한 비용 추정은$0.08442375이며 실제 청구서 확정 금액은 아닙니다. 두 원장은 각각24회를 예약해 합계48회·$0.60입니다. 원격 표식과 원장을 삭제하거나 재실행하지 않았습니다. [워크플로 메타데이터](live-execution-checks/workflow.json).

원자료104개는 별도 결과 커밋 `6febc3eddde6a00bbb8454d29d482ee0049d4bbd`에 보존했습니다. 로컬로 가져오는 과정에서0바이트였던 복사본3개는 원격 원본 Git blob에서 복원하고104개 전체의 바이트 일치를 확인했습니다. 원래 모델 응답과 원격 결과 커밋은 수정하지 않았습니다. [수집 사본 대조 기록](live-execution-checks/raw-preservation.json).

## 무료 코드·화면 검증

새 exporter는 저장 원자료를 읽어 정적 JSON을 만들며 공급자와 수정 게이트를 실행하지 않습니다. 실제 응답48건, 기존과 대응하는24건, 추가24건을 구분하고 원인용을 최초 validator 오류와 독립적으로 대조합니다. UI도 저장 JSON만 읽으며 API 키나 생성 경로를 게시하지 않습니다.

- Exporter9개 테스트를 실패 재현 후 통과시켰습니다. 추가 인용 검사에서는 schema로 먼저 차단된 응답의 원문 불일치가 가려지지 않음을 확인했습니다.
- 실제48슬롯의 입력·원응답·응답 ID·인용·효과·개발16/기존36 회귀·과거24대응·요약표를 화면과 대조했습니다.1440/320/390/650px에서 문서 가로 넘침이 없었고, HTTP503·잘못된 JSON 오류 표시, JavaScript 오류0, 외부 요청0을 확인했습니다. [검사 JSON](live-browser-v1/checks.json), [1440px](live-browser-v1/generation-v4-1440.png), [320px](live-browser-v1/generation-v4-320.png).
- 별도 AI 코드 검토에서 Critical·Important 문제는 없었고,48슬롯의 projection을 독립적으로 다시 생성해 전체 필드 일치를 확인했습니다. 이전 준비 페이지의 상태 문구는 당시 시점을 명시했습니다. [검토 범위와 판단](live-execution-checks/code-review.md).
- 전체 테스트가 새 테스트 코드의 UTF-8 인코딩 누락1건을 찾아 수정했습니다. 기존 이식성 검사로 실패를 재현한 뒤 관련16검사가 통과했고, 최종 전체 검사는 **477 passed, 1 skipped, 2 deselected**,114.52초였습니다. [수정 전 전체](live-execution-checks/pytest-initial.txt), [최종 전체](live-execution-checks/pytest-final.txt). 실제 모델을 호출하는 테스트는 아닙니다.
- 기존159파일, 이전 공급자·캠페인·워크플로, 고정48입력의 해시는 그대로입니다. [최종 보존 대조](live-execution-checks/preservation.json).

브라우저 검사는 Google 공식 배포본 Chrome141과 Noto 한국어 글꼴을 사용한 로컬 정적 서버 검사입니다. 공개 접속 확인과 동일한 검사로 간주하지 않습니다.

## 공개 배포와 지원 문서

새 `generation-v4.html` 화면의 배포와 공개 파일 대조는 코드 검증 후 진행합니다. 기존 Render 서비스·저장소·main 브랜치를 사용하며 새 유료 서비스를 만들지 않습니다. 배포 ID, 실제 코드 SHA, 공개 HTML·JS·JSON의 응답과 바이트 일치는 확인 후 기록합니다.

자소서·포트폴리오의 본문을 새 실제 결과로 갱신했습니다. 자소서는2쪽, 포트폴리오는5쪽이며 한글 글꼴을 내장했습니다. 전체7쪽을 이미지로 확인했고, 문단이 페이지 경계에서 갈라지지 않도록 조정했습니다. 비교표의 열 폭도 다듬었으며 포트폴리오의 링크 주석33개를 확인했습니다. Markdown은 저장소 원문과 바이트가 같고 PDF/Markdown의 SHA-256을 [산출물 확인 기록](live-execution-checks/application-files.json)에 남겼습니다.
