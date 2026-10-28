# v4 검증·배포 확인

실행 코드 커밋은 `829d478d3cedce974251c3dcf77d0d8674e010ca`입니다. 2026-10-28 15:06 UTC(한국 시간 2026-10-29 00:06)에 기존 공개 정적 사이트로 배포하고 파일 응답을 확인했습니다. 아래 기록을 추가하는 후속 커밋은 운영 문서만 변경합니다. [구조화된 기록](operations.json).

## 검사 결과

| 범위 | 결과 | 근거 |
|---|---|---|
| 로컬 Python 3.12, scale 선택 의존성 포함 | 419 passed · 1 skipped · 2 deselected, 107.86초 | [전체 로그](checks/pytest-final.txt) |
| GitHub Ubuntu, Python 3.11 | 400 passed · 2 skipped, 86.54초 | [CI 실행](https://github.com/sokldjs554/queryscope/actions/runs/40711959844), job `122899308311` |
| GitHub Windows, Python 3.11 | 400 passed · 2 skipped, 86.64초 | 같은 CI, job `122899308363` |
| 검색 품질 게이트 | 통과, 기준선 평균 nDCG 0.5839 유지 | 같은 CI, job `122899307554`; [로컬 기준선](checks/baseline.txt) |
| 로컬 실제 브라우저 | 24응답·12검사·1440/320/390/650px 통과 | [검사 결과](browser-final/checks.json) |
| 과거 기록 | 159파일 보존 | [해시 대조](preservation.json) |

CI는 기존 설치 명령 `.[api,mcp,dev]`를 사용하며, 로컬 전체 검사는 선택적인 scale 의존성을 포함했습니다. 서로 다른 환경의 검사 수를 합산하지 않습니다. 최종 CI의 전체 상태는 `completed/success`이며, 원격에 게시된 Git 트리와 로컬 검증본의 바이트가 같음을 확인했습니다.

별도 AI 코드 검토에서 사후 평가 원본의 연결 검증 누락을 발견했습니다. 동결 준비 해시·문맥·사례쌍·원응답·응답ID 변조에 대한 실패를 먼저 확인하고 수정했습니다. 이후 전체 검사와 두 운영체제 CI가 통과했습니다. 이 코드 검토는 24응답의 독립적인 사람 의미 평가를 대신하지 않습니다.

## 공개 배포와 접속 확인

- 공개 화면: [v4 후속 검사](https://queryscope-zwia.onrender.com/review-v4.html).
- 기존 서비스: `queryscope`, 정적 게시 경로 `src/searchclinic/web`.
- Render 배포: `dep-dbh0uigu01pc73b8sjdg`, 상태 `live`, 코드 커밋 `829d478d3cedce974251c3dcf77d0d8674e010ca`.
- 자동 배포는 기존 설정대로 꺼져 있어 CI 통과 후 기존 서비스에 한 번 배포했습니다.
- 공개 HTML·JavaScript·JSON 세 파일이 정상 인증서 검증을 사용하는 HTTP 클라이언트에서 모두 **HTTP 200**을 반환했고, 로컬 검증 파일과 바이트가 일치했습니다. [응답·크기·SHA-256](public-http.json).

브라우저 동작 검사는 로컬 서버에서 수행했습니다. 새로 설치한 Chrome headless로 공개 URL을 여는 추가 검사는 `net::ERR_CERT_AUTHORITY_INVALID`로 중단되어 공개 브라우저 동작 통과로 계산하지 않았습니다. 인증서 검사를 끄지 않았습니다. 공개 파일 응답·바이트 일치와 로컬 화면 동작 확인의 범위를 구분합니다. 과거 사용자의 공개 접속 확인은 [2026-10-27 기록](../queryscope-v3/USER-ACCEPTANCE.md)에 별도로 남습니다.

공개 화면은 저장 결과 재생이며 모델 서버나 API 키를 배포하지 않습니다. 신규 API 호출·새 모델 응답은 0건입니다. 사람 의미 검토 24건은 계속 pending이며, 준비한 48입력에 대한 새 모델 생성도 실행하지 않았습니다.

## 지원 문서

자기소개서는 기존 4항목을 유지한 2쪽 PDF, 포트폴리오는 9항목을 유지한 4쪽 PDF로 편집했습니다. 한국어 글꼴을 포함하고 6쪽 전체를 이미지로 렌더링해 확인했습니다. 포트폴리오의 근거 링크 26개는 실제 웹 주소로 연결됩니다. 편집 가능한 Markdown과 본문이 일치하며, 문서의 수치·사람 검토 상태를 원자료와 별도로 대조했습니다. [자기소개서](../../application/cover-letter.md) · [포트폴리오](../../application/portfolio.md) · [수정 근거](../../application/REVISION-NOTES.md).
