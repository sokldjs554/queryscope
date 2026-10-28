# v4 모델 재평가 준비 검증

**후속 상태:** 이 문서는 승인 전 무료 검증 당시의 기록입니다. 이후 사용자가 승인한48회 실행을 완료했으며, [실제 결과](ACTUAL-API.md)와 [새 결과 화면의 검증](LIVE-OPERATIONS.md)은 별도로 기록합니다.

2026-10-29(Asia/Seoul). **무료 준비·모의 응답 검증만 수행했으며 새 유료 API 호출은 0회**입니다. 이 문서의 테스트 통과는 실제 모델의 새 진단 성능을 뜻하지 않습니다. 실행할 모델·입력·비용은 [실행 직전 계획](LIVE-EVALUATION-PROPOSAL.md)에 고정했습니다.

## 준비된 결과

- 기존 실제 24응답을 원인 근거·원문 인용·의미 지지·수정 의미와 효과·진단/보류 선택의 다섯 축으로 [AI 평가](AI-SEMANTIC-REVIEW.md)했습니다. 120개 판정에 이유·원자료 위치·불확실성을 기록했습니다. 실제 사람 검토 필드는 그대로입니다.
- 새 입력 48건의 모델·payload·사례·조건·해시를 고정했습니다. [승인 양식](live-prepared-v1/approval-template.json)은 `approved=false`이며 실제 승인 파일과 새 실제 응답 폴더는 없습니다.
- 과거 원자료 159파일과 기존 공급자·캠페인·실행 워크플로를 보존했습니다. [보존 기록](live-preparation-checks/preservation.json).

## 별도 AI 코드 검토와 수정

실제 호출 전 별도 AI 코드 검토에서 중요도 Important인 문제 세 가지가 나왔습니다. 아래 문제를 재현하는 11개 검사를 먼저 실패시킨 뒤 수정했습니다. 이 검토 역시 사람의 독립 검토로 계산하지 않습니다.

| 발견한 문제 | 수정한 동작 |
|---|---|
| 원격 실행 표식이 워크플로의 선택적 단계에 있어 다른 환경의 직접 실행이 중복 호출 가능 | 실제 실행 함수 안에서 원격 표식의 원자적 생성에 성공해야만 호출. 새 로컬 상태에서도 기존 표식이면 중단 |
| 불완전 응답·거부·잘못된 JSON·사용량 누락·HTTP 오류에서 원문 유실 가능 | 기존 공급자 앞의 수신 기록 계층이 해석 전에 HTTP 본문과 메타데이터 저장. 인증 헤더 제외, 키 반사 시 제거 사실 기록 |
| 관측 모델명과 응답 ID의 누락·불일치·중복을 채점 전에 차단하지 않음 | 관측한 모델과 고유 ID를 확인. 실패는 출처 연결 오류로 보존하고 채점 없이 중단 |

[수정 전 실패 11건](live-preparation-checks/review-red.txt) · [수정 후 관련 검사 56건 통과](live-preparation-checks/review-green.txt). 재현에는 `httpx.MockTransport`와 가짜 키를 사용했고 외부 모델을 호출하지 않았습니다.

## 검증 결과

| 검증 | 결과 |
|---|---|
| 최초 실행 모듈과 과거 캠페인·이식성 검사 | 58 passed — [로그](live-preparation-checks/runtime-green.txt) |
| CLI와 원격 실행 표식 검사 | 11 passed — [로그](live-preparation-checks/cli-green.txt) |
| 세 가지 코드 검토 수정 후 관련 검사 | 56 passed — [로그](live-preparation-checks/review-green.txt) |
| 최종 로컬 전체 테스트 | **468 passed, 1 skipped, 2 deselected**, 120.22초 — [로그](live-preparation-checks/pytest-final.txt) |
| 워크플로 구문 검사 | actionlint v1.7.7 통과, 종료 코드 0 — [출력](live-preparation-checks/actionlint.txt) |
| 고정 입력 준비·검증 | 48건 준비 및 검증, API 호출 0회 — [로그](live-preparation-checks/preparation.txt) |
| 원격 CI | Ubuntu·Windows 각각 **449 passed, 2 skipped**, 검색 품질 게이트 통과 — [CI 실행](https://github.com/sokldjs554/queryscope/actions/runs/40721662846), [결과 기록](live-preparation-checks/ci.json) |

최종 전체 테스트는 코드 검토 세 가지 수정이 모두 반영된 상태에서 실행했습니다. 공개 사이트 파일은 이번 준비 작업에서 변경하지 않았으며 이전 [배포 기록](OPERATIONS.md)의 범위를 그대로 유지합니다.

CI가 검사한 코드 커밋은 `0df20cbd4108570fbba4090972b2c8693fcd8ea4`입니다. 해당 커밋에서 실행된 워크플로는 일반 CI뿐이며 유료 평가 워크플로는 시작되지 않았습니다. 검색 품질 게이트의 평균 nDCG는 0.5839를 유지했습니다. 로컬 전체 검사는 선택 의존성 `scale`을 포함했고 기존 CI는 `api,mcp,dev` 구성으로 실행했습니다.

## 실행 전 남아 있는 확인 범위

기존 시크릿의 현재 유효성과 GitHub 태그 생성 권한은 승인된 실제 워크플로에서 확인합니다. 값이 없거나 원격 실행 표식을 만들지 못하면 모델 호출 전에 중단합니다. 별도 유료 탐색 호출은 하지 않았습니다.

공식 가격을 확인해 예상 비용과 예약 한도를 계산했지만 계정 전체 결제액을 제한하는 기능은 아닙니다. 원격 표식은 정상 실행 경로의 중복 호출을 막으며 저장소 소유자가 직접 표식을 지우거나 코드를 변경하는 경우까지 보장하지 않습니다.

AI 의미 평가의 원자료 연결과 형식은 확인했지만 의미 판단의 외부 타당성·평가자 간 일치·사람 검토 완료를 입증한 것은 아닙니다. 새 모델 결과가 없으므로 보완된 입력이 생성 오류를 줄였다는 결론도 아직 없습니다.
