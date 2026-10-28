# 지원 문서 수정 기록

2026-10-29(Asia/Seoul). 승인 후 완료된 QueryScope v4 실제 48응답과 기존 24응답의 AI 의미 평가를 지원 문서에 반영했다. 실제 결과를 원자료에서 확인하고 기준선·같은 응답 재검사·새 생성 직접 비교·추가 사례를 구분했다. 사용자 첨부 원본과 과거 사람 검토 기록은 변경하지 않았다.

| 최초 첨부 원본 | SHA-256 | 현재 수정본 |
|---|---|---|
| Yoon_Gihyeok_Alba_CoverLetter.md | `e456a5f94f4884c6679e59f339f74621e798517a5a3570f4fb50c9cf9e690f46` | [자기소개서](https://github.com/sokldjs554/queryscope/blob/main/docs/application/cover-letter.md) |
| Yoon_Gihyeok_KoSearch_Portfolio.md | `1321118486e1013ad84e46191ac888681d20e9e58c0ea0232f2cb0f8b6afdb35` | [포트폴리오](https://github.com/sokldjs554/queryscope/blob/main/docs/application/portfolio.md) |

## 유지한 구성과 표현

- 자기소개서의 지원동기·직무역량·문제 해결 경험·입사 후 포부 4개 항목과 포트폴리오의 개발 배경부터 검증 자료까지 9개 항목 및 순서를 유지했다.
- 제목은 ‘윤기혁 자기소개서’, ‘QueryScope 프로젝트 포트폴리오’를 유지했다. 지원 기업·직무·이름과 기업 서비스에 관한 동기는 기존 원문을 따랐다. 기업의 최신 상태를 이번 문서 수정에서 재조사한 것은 아니다.
- 개인 프로젝트의 방향·평가 범위를 정하고 코드 구현·실험 자동화·문서 정리에 Codex의 지원을 받았다는 역할을 유지했다. 새 경력·학력·기여 비율·고객 데이터·고객 성과는 추가하지 않았다.

## 실제 생성과 재검사 구분

| 범위 | 통과 / 보류 / 차단 | 근거와 해석 |
|---|---|---|
| v3 최초 실제 24응답 | 7 / 9 / 8 | [v3 실제 평가](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/ACTUAL-API.md). 당시 판정 보존. |
| 같은 v3 저장 응답의 v4 재검사 | 6 / 9 / 9 | [재검사 원자료](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/run-v1/audit.json). 새 응답이 아닌 검사 기준 보완. |
| v4 새 생성 직접 비교 24응답 | 7 / 13 / 4 | 이전 12사례 × 힌트 유무. 입력과 검사 규칙을 보완한 같은 개발 사례 비교. |
| v4 새 생성 추가 24응답 | 1 / 18 / 5 | 추가 12사례 × 힌트 유무. 같은 v3 개발 묶음이며 독립 새 평가셋이 아님. |
| v4 새 생성 전체 48응답 | 8 / 31 / 9 | [실제 원자료](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/actual-api-v1/results.json). supported는 의미 정답이 아님. |

실제 48회는 사용자 승인 48회·최대 $0.60 범위에서 완료됐다. 48시도·48응답·API 오류 0건·요청/응답 출처 무결성 오류 0건이며 사용량 기준 비용 추정은 $0.08442375다. v3의 $0.0385605와 분리했고 청구 금액 확정값으로 표현하지 않았다. 원격 원본 커밋은 `6febc3eddde6a00bbb8454d29d482ee0049d4bbd`이며 전달받은 실제 원자료는 104개 파일이다.

## 반영한 성과와 남은 실패

| 반영 내용 | 표현 범위 |
|---|---|
| 직접 비교의 보류 계약 8/12→11/12 | 보류·무패치·검증 통과 계약이며 보류 이유의 의미적 정답률이 아님. |
| 새 8후보 중 7채택·1기각 | 직접 비교에서 6채택(4질의)·1기각, 추가에서는 측정기 무힌트 1채택. 전체 고유 질의는 5개. |
| 각 후보의 효과 | 채택 후보의 표적 nDCG는 각각 0→1, 박자기 힌트는 0→0. 기존 36질의와 개발 정답 있는 16질의의 측정 지표 하락 0건. 개별 후보 적용이며 결합 성능이 아님. |
| 상품 ID의 운영 지식 인용 출처 사용 0 | 이번 원응답에서 해당 오류가 없다는 뜻이며 인용 오류 전체 해결이 아님. |
| 인용 전수 대조 90구절 중 87일치·3불일치 | 고유 3응답에 불일치 존재. 최초 차단 사유가 인용 오류인 것은 2응답이며, T15 hint는 형식 검사가 먼저 차단해 문구 불일치가 일차 사유에 드러나지 않음. |
| 잘못된 분해·대표어 형식·상태 오류 | 접착제 힌트의 중복·빈 항목, 색인 복합어 대신 질의를 분해한 후보, microscope의 여러 단어 대표어, 정상 응답 상태 오류를 남김. |
| 박자기의 의미와 효과 | 무힌트는 미확인 대응으로 보류했으나 힌트는 다시 박자와 연결해 미개선. 라벨 변화만으로 해결됐다고 쓰지 않음. |

세부 근거는 [v4 실제 평가 보고서](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/ACTUAL-API.md)와 [전수 대조·효과·출처 분석](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/actual-api-analysis-v1/analysis.json)에 연결한다. 단일 배치이고 입력·검사 변경이 함께 반영됐으므로 개별 변경의 인과 효과, 반복 재현성, 새 상품 일반화로 표현하지 않는다.

## AI 의미 평가와 사람 검토

[AI 의미 평가](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/AI-SEMANTIC-REVIEW.md)는 **기존 v3 24응답**의 5축 120개 판정·이유·근거·불확실성을 완결한 사후 AI 평가다. 기존 메모·작성 qrels·게이트 결과를 본 같은 작업 세션의 AI가 작성했으며 독립적인 사람의 평가가 아니다. 이를 새 v4 48응답의 의미 평가로 옮겨 계산하지 않았다. 기존 사람 필드의 null/pending 상태를 유지했고 새 48응답의 사람 평가도 없다.

‘48개 준비·새 응답 없음·추가 호출 0회’와 ‘AI 사전 검토만 준비’라는 이전 문장을 현재 실행·평가 상태에 맞게 교체했다. 이 표현의 과거 시점과 근거는 Git 이력에 남긴다.

## 분량·화면·검증 이력

자기소개서는 약 2,700자(공백·제목 포함)로 핵심 흐름을 유지했다. 포트폴리오는 과거 v1/v2 세부 실험을 링크로 압축하고 최신 실제 비교와 실패를 중심으로 정리했다. 모든 근거 링크는 단독 Markdown·PDF에서 열 수 있는 웹 주소로 유지했다. 최종 PDF는 자소서2쪽·포트폴리오5쪽이며, 한글 글꼴 내장과 전체7쪽의 시각 검사를 마쳤다. 문단을 페이지 경계에서 나누지 않고 비교표 열 폭을 조정했다. 포트폴리오 링크33개와 파일 해시는 [산출물 확인](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/live-execution-checks/application-files.json)에 남겼다.

새 실제 결과 화면은 `/generation-v4.html`, 과거 실제 응답 화면은 `/generation-v3.html`, 저장 응답의 새 검사 비교는 `/review-v4.html`로 구분한다. 이 문안 작성 시 새 화면은 준비 중이며 최종 CI·공개 배포·접속 검증 완료를 주장하지 않는다. 기존 코드 검사 결과를 새 화면의 검사 성공으로 사용하지 않았다.

과거 개선과 한계는 [v1](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v1/README.md)·[v2](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v2/README.md)·[v3](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/README.md)에 보존한다. 최초 159개 파일의 [보존 대조](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/preservation.json)와 2026-10-27 [공개 데모 사용자 확인](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/USER-ACCEPTANCE.md)도 해당 시점의 기록으로 유지한다. 미제공 기기·브라우저·세부 테스트·고객 효과를 새로 추가하지 않았다.
