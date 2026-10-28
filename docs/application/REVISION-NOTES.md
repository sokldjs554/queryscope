# 지원 문서 수정 기록

2026-10-28. 현재 지원 문서에 QueryScope v4의 실제 후속 분석을 반영하고 분량을 줄였다. 사용자 첨부 원본과 과거 평가 기록은 변경하지 않았다. 이번 작업은 문서 수정이며 새 모델 호출이나 사람의 의미 평가를 수행하지 않았다.

| 최초 첨부 원본 | SHA-256 | 현재 수정본 |
|---|---|---|
| Yoon_Gihyeok_Alba_CoverLetter.md | `e456a5f94f4884c6679e59f339f74621e798517a5a3570f4fb50c9cf9e690f46` | [자기소개서](https://github.com/sokldjs554/queryscope/blob/main/docs/application/cover-letter.md) |
| Yoon_Gihyeok_KoSearch_Portfolio.md | `1321118486e1013ad84e46191ac888681d20e9e58c0ea0232f2cb0f8b6afdb35` | [포트폴리오](https://github.com/sokldjs554/queryscope/blob/main/docs/application/portfolio.md) |

## 유지한 구성과 표현

- 자기소개서의 지원동기·직무역량·문제 해결 경험·입사 후 포부 4개 항목과 순서를 유지했다. 제목은 ‘윤기혁 자기소개서’로 정리했다.
- 포트폴리오의 개발 배경부터 검증 자료까지 9개 항목과 순서를 유지했다. 제목은 ‘QueryScope 프로젝트 포트폴리오’로 정리했다.
- 지원 기업·직무·이름과 기업 서비스에 대한 지원동기는 기존 원문을 따랐다. 최신 채용 공고나 기업 서비스를 이번 문서 수정에서 재조사한 것은 아니다.
- 개인 프로젝트의 방향·평가 범위를 정하고 코드 구현·실험 자동화·문서 정리에 Codex의 지원을 받았다는 역할을 명시했다. 새 경력·학력·기여 비율·고객 데이터·고객 성과는 추가하지 않았다.

## v4 반영 내용과 근거

| 반영 내용 | 근거와 해석 범위 |
|---|---|
| 최초 24응답의 통과 7·보류 9·차단 8 보존 | [v3 실제 평가](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/ACTUAL-API.md). supported를 의미적 정답으로 표현하지 않는다. |
| 같은 응답의 새 적용 검사: 6·9·9 | [v4 원자료](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/run-v1/audit.json). 원응답·원문맥 재검사이며 최초 판정을 변경하지 않는다. |
| microscope 힌트 응답 추가 차단 | 색인에 없는 대표어 마이크로스코프를 `canonical_not_in_index`로 효과 평가 전에 차단. 카탈로그 표현은 광학 현미경이다. |
| 남은 6응답 중 4채택·2기각 | 팔래트·파스탤의 각 조건 4응답이 nDCG 0→1. 서로 다른 질의로는 2개다. 박자기의 2응답은 0→0으로 기각. |
| 측정한 회귀 저하 0 | 각 후보를 따로 적용한 기존 36질의와 v3 정답 있는 16질의의 결과. 평가셋 밖의 무회귀를 보장하지 않는다. |
| 설명 기반 후보 보완 | 0건일 때 일반 안내 표현을 제외한 단서가 둘 이상 겹치는 후보만 제시. 의미 대응을 확정하지 않는다. |
| 원칙 검색 7/8→8/8 | 이미 개선에 사용한 v3 개발 자료의 무힌트 결과. 힌트는 8/8 유지. 새 모델 정확도·독립 평가 성과가 아니다. |
| 새 입력 48개 준비·모델 응답 0 | 최대 요청 본문 7,444바이트, 제한 11,000바이트 이내. v4 유료 호출 0회. 과거 실제 비용은 토큰 기준 추정 $0.0385605. |
| 역사적 기록 보존 | [보존 대조](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/preservation.json)의 159개 파일과 기존 준비 입력 48개의 문맥·요청 재현. |
| 사람 평가 24건 미완료 | [검토 안내](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/HUMAN-REVIEW-GUIDE.md)와 [AI 사전 검토](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/AI-REVIEW.md)를 준비. AI 메모는 독립 사람의 평가가 아니다. |
| 화면 경로 | `/review-v4.html`을 후속 검토 화면으로, `/generation-v3.html`을 원래 실제 응답 재생으로 구분. 이번 문서에서 최신 배포·접속 성공을 확정하지 않는다. |

## 분량 조정과 과거 이력

자기소개서는 핵심 문제 해결 흐름을 중심으로 2,549자(공백·제목 포함)로 줄였다. 포트폴리오는 중복 설명과 과거 실험 세부 표를 압축했다. 최종 PDF는 자기소개서 2쪽·포트폴리오 4쪽이며, 한국어 글꼴을 포함하고 모든 쪽을 이미지로 렌더링해 글자 잘림·표 겹침·쪽 나눔을 확인했다. PDF에 포함된 링크는 웹 주소로 연결하고, 편집 가능한 Markdown과 본문을 일치시켰다.

2026-10-27의 v1·v2·v3 수정 내용은 Git 이력과 아래 원자료에 보존한다. 개발 개선과 별도 작성 자료, 근거 검색과 실제 생성, 인용 일치와 의미 판단을 계속 구분한다.

- [v1 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v1/README.md): 아답터·백팩 수동 후보, 초기 개발 평가, 과거 응답 재검증.
- [v2 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v2/README.md): 개발 근거 검색 개선과 별도 18상품·24질의의 미개선 결과·작성 가설 한계.
- [v3 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/README.md): 정상 오신호 보완, 강제 통짜 색인 결함, 별도 16상품·24질의 구성.
- [v3 실제 API](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/ACTUAL-API.md): 승인 후 24회 실제 호출, 최초 판정, 비용·실패 분석.
- [공개 데모 사용자 확인](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/USER-ACCEPTANCE.md): 2026-10-27 접속·수동 테스트 완료 보고. 미제공 기기·브라우저·세부 항목이나 장기 운영 성과는 추가하지 않는다.

최신 문서는 전체 테스트 수나 최신 CI·배포 성공을 앞선 기록에서 그대로 옮기지 않았다. 이번 로컬 전체 검증은 419 passed·1 skipped·2 deselected이며, 실제 브라우저에서 24응답과 4개 화면 너비를 검사했다. 과거 검사 결과는 해당 버전의 증거로 남겼으며, 현재의 상세 검증 범위는 [v4 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/README.md)에 연결한다.
