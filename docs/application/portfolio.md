# QueryScope 프로젝트 포트폴리오

한국어 검색 진단과 수정안 검증 | 윤기혁

검색 품질을 점검하는 개발자를 위한 개인 프로젝트입니다. 실패한 검색어의 관찰·원문 근거·수정 후보를 연결하고, 실제 검색 효과를 검사합니다.

후속 개선·검증: 2026-10-29 | Codex 활용

Python · FastAPI · Kiwi · BM25 · OpenAI Responses API · Pydantic · GitHub Actions

[소스와 실행 안내](https://github.com/sokldjs554/queryscope) · [새 실제48응답](https://queryscope-zwia.onrender.com/generation-v4.html) · [기존24응답 재검사](https://queryscope-zwia.onrender.com/review-v4.html) · [기반 PR #2](https://github.com/sokldjs554/ko-search-clinic/pull/2)

## 개발 배경

검색 결과가 없을 때에는 문서 부재, 표기 차이, 형태소 분해, 복합어 처리 등 여러 원인을 생각할 수 있습니다. 필요한 수정도 서로 다릅니다. 동의어나 분석기 규칙은 여러 질의에 함께 적용되므로 한 질의를 개선한 변경이 다른 질의의 품질을 낮추는지도 확인해야 합니다.

QueryScope는 관찰을 모아 원인을 설명하는 단계부터 수정안의 적용 여부를 판단하는 단계까지 연결합니다. 형태소·검색 결과·운영 지식을 LLM에 제공하고, 원문 인용 검사와 검색 효과 평가를 분리했습니다. 자연스러운 설명이나 정확한 인용만으로 수정 효과가 입증되지는 않기 때문입니다.

자료는 직접 작성한 상품 카탈로그와 평가 질의입니다. 실제 고객 로그나 알바천국의 검색 데이터를 사용한 프로젝트가 아닙니다. 개발에 사용한 자료는 다음 평가의 새 자료로 계산하지 않고, 새로 작성한 자료도 같은 작성자·상품 도메인·운영 지식을 공유한다는 한계를 기록했습니다.

## 개발 범위

서비스 방향과 검증 범위를 정하고, 코드 작성·수정·실험 자동화·문서 정리에 Codex의 지원을 받았습니다. 코드와 결과를 확인하며 실패 사례를 정리한 개인 프로젝트입니다. 새 경력이나 고객 성과를 대신하는 자료로 소개하지 않습니다.

ko-search-clinic의 RAG 서비스와 검증을 포함한 PR #2 커밋 `493935f6`에서 새 저장소로 이어받았습니다. 전체 Git 이력과 기준 태그 `upstream-pr2`를 보존하고 기존 저장소는 변경하지 않았습니다. 검색 엔진·회귀 게이트·과거 실제 API 응답을 유지하면서 평가 분리, 수동 수정 후보, 생성 결과 검사와 데모를 보완했습니다.

후속 v4에서는 기존 실제 24응답의 재검사와 보완된 입력의 새 실제 생성을 분리했습니다. 새 생성은 기존 12사례×힌트 유무의 직접 비교 24회와 추가 12사례×힌트 유무의 24회입니다. 추가 사례도 같은 v3 개발 자료에 속하며 새 독립 평가셋이 아닙니다. 과거 기록 159개 파일과 기존 준비 입력 48개의 재현 이력도 보존했습니다. [출처](https://github.com/sokldjs554/queryscope/blob/main/docs/PROVENANCE.md) · [보존 대조](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/preservation.json)

## 기술 선택

| 선택 | 이유와 범위 |
|---|---|
| Kiwi 형태소 분석과 BM25 검색 | 질의 토큰, 상품 색인, 운영 문서의 검색 순위를 로컬에서 재현하고 비교하기 위해 선택했습니다. 벡터 검색보다 우수하다고 입증한 선택은 아닙니다. |
| 구조화된 생성과 Pydantic 검사 | 원인·인용·수정 후보의 형식을 제한하고 코드에서 검사합니다. 원문 일치와 의미적 지지는 별도로 다룹니다. |
| 수정 효과 게이트 | 엔진 사본에서 목표 질의 개선과 다른 질의의 순위·정밀도·재현율 변화를 확인합니다. |
| 이력과 현재 검사 경로 분리 | 원응답과 최초 판정을 보존한 채 새 규칙의 차이를 비교해 검증기 보완을 모델 향상으로 혼동하지 않도록 했습니다. |

## 검색 진단

질의와 요청 설명을 입력하면 실제 분석 토큰, 버려진 품사, 검색 상위 결과, 관련 운영 문서를 모읍니다. 상품 원문과 색인의 차이, 자모 유사 표기, 문자 체계 등의 관찰로 관련 지식을 검색하고 긴 문서는 연속 원문을 발췌해 위치를 남깁니다. 생성 입력에는 평가용 정답표나 검색에 사용한 원인 키워드를 넣지 않습니다.

정상 접미 표현이 부분어 누락으로 잘못 잡힌 사례는 실제 질의 토큰이 상품 색인에 모두 있는지 비교하도록 보완했습니다. v3 정상 검색 8개의 잘못된 누락 신호는 양 조건에서 8/8에서 0/8로 줄었습니다. 부분어 누락 4개는 통짜 색인을 강제해 만든 합성 결함으로, 자연 발생 고객 장애와 구분했습니다.

v4에서는 검색이 0건일 때 요청 설명과 상품 설명을 비교하는 보완 경로를 추가했습니다. 일반 안내 표현을 제외한 단서가 둘 이상 겹칠 때만 후보를 제시합니다. microscope의 요청 설명에서 광학 현미경을 찾을 수 있어도 후보가 곧 검증된 번역이나 동의어라는 뜻은 아닙니다. 의미 대응은 확인 대상으로 남겼습니다.

인용은 제공된 운영 지식의 ID와 본문을 대조합니다. 줄바꿈·연속 공백·짝이 맞는 강조 기호의 표시 차이는 정리하되 단어 경계와 문장부호는 보존합니다. 검색 결과의 상품 ID와 운영 지식의 인용 ID를 구분하고, 원문에 없는 표현이나 허용되지 않은 출처를 차단합니다. 원문에 실제로 존재하는 문장도 해당 원인을 지지하는지는 별도로 판단해야 합니다.

## 수정안 검증

수정 후보는 동의어 연결, 사용자 사전 등록, 복합어 분해입니다. 형식 검사 후 엔진 사본에 적용해 표적 질의의 nDCG 개선, 다른 질의의 품질 저하, 전체 평균을 확인합니다. nDCG는 관련 상품이 결과 앞쪽에 나오는 정도를 평가하며 1에 가까울수록 좋습니다. 이 게이트는 측정한 평가셋 안의 적용 조건입니다.

초기 아답터·백팩 후보는 사전 등록만으로 개선되지 않았습니다. 운영자가 카탈로그의 어댑터·배낭과 연결한 수동 후보는 각각 nDCG@10 0→1로 개선됐습니다. 후속 카페트·초콜렛·워시 수정으로 개발 자료의 평균은 높아졌지만 초콜렛 선물에는 무관한 향초 결과가 남았습니다. 각 후보의 결과와 결합 설정을 분리해 [v1](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v1/README.md)·[v2](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v2/README.md)에 보존했습니다.

v4에서 추가한 검사는 동의어 대표어가 실제 색인에 존재하는지 확인하는 것입니다. v3의 microscope 힌트 응답은 마이크로스코프를 대표어로 제안했지만 카탈로그에는 광학 현미경이 있습니다. 이 후보는 새 검사에서 `canonical_not_in_index`로 효과 평가 전에 차단됐습니다. 대표어 존재 검사는 의미 검증 전체를 대신하지 않으며, 박자와 박자기의 유사성처럼 남은 의미 문제는 검색 효과와 사람 검토로 계속 구분합니다.

## 실험과 결과

개발에 사용한 과거 자료와 새로 고정했던 자료, 실제 생성과 오프라인 검사를 나누어 기록했습니다. v3를 개선에 사용한 이번 단계에서는 해당 자료를 개발용으로 전환했습니다.

| 단계 | 확인한 결과 | 해석 범위 |
|---|---|---|
| v1·v2 개발 수정 | 개발 20질의 평균 nDCG@10 0.9142→0.9992 | 수동 수정의 개발 결과. 모델이 새 수정안을 발견한 성과가 아닙니다. |
| v2 별도 작성 자료 | 정답 있는 18질의 평균 0.5351→0.5351 | 기존 사전 수정이 새 표현을 자동 해결하지 못했습니다. |
| v3 통제된 누락 복구 | 정답 있는 16질의 평균 0.5000→0.7500 | 강제로 만든 복합어 결함 4개의 수동 복구 실험입니다. |
| v3 당시 원칙 검색 | 무힌트 7/8, 힌트 8/8 | 관련 운영 원칙의 hit@3이며 모델 원인 진단 정확도가 아닙니다. |
| v4 보완 후 같은 개발 자료 | 무힌트 7/8→8/8, 힌트 8/8→8/8 | 설명 단서로 후보를 보완한 검색 결과. 새 독립 평가가 아닙니다. |

**기준선과 새 실제 생성:** v3는 고정한 12사례를 힌트 유무로 나누어 24회 생성했습니다. v4는 같은 GPT-5.4-mini 스냅샷으로 직접 비교 24회와 추가 24회를 실행했습니다. 기존 응답에 새 검사를 적용한 결과를 새 생성과 섞지 않았습니다.

| 평가 범위 | 응답 수 | 인용·형식 통과 | 보류 | 차단 |
|---|---:|---:|---:|---:|
| v3 최초 실제 생성 기준선 | 24 | 7 | 9 | 8 |
| 같은 v3 저장 응답의 v4 재검사 | 24 | 6 | 9 | 9 |
| v4 새 생성: 직접 비교 | 24 | 7 | 13 | 4 |
| v4 새 생성: 추가 사례 | 24 | 1 | 18 | 5 |
| v4 새 생성 전체 | 48 | 8 | 31 | 9 |

통과는 `supported` 검사 상태이며 의미적 정답 수가 아닙니다. v4 새 생성은 48시도·48응답·API 오류 0건으로 완료됐습니다. 요청과 응답의 출처 무결성 오류도 0건이지만 이는 인용 문구 오류가 없다는 뜻과 다릅니다. 사용량 기준 비용 추정은 **$0.08442375**, 승인 예약 상한은 $0.60입니다. v3 최초 비용 추정 $0.0385605와 분리했습니다. 모두 청구 금액 확정값은 아닙니다.

**직접 비교 24응답:** 원래 12사례의 차단은 최초 8건에서 새 생성 4건으로 바뀌었습니다. 정상·불명·근거 부족·범위 밖의 보류·무패치·검증 통과 계약은 8/12에서 11/12로 바뀌었습니다. 같은 개발 사례에 입력과 검사 규칙을 함께 보완한 단일 배치의 결과이므로 새 상품의 진단 정확도나 개별 변경의 인과 효과로 표현하지 않습니다.

이번 48응답에서 상품 ID를 운영 지식 인용 출처로 사용한 오류는 없었습니다. 다만 원인용 90구절을 별도로 대조하면 87구절은 일치하고 3구절은 문구가 다릅니다. 인용 오류가 일차 차단 사유인 응답은 2건이고, microscope 힌트 응답의 추가 문구 불일치는 형식 검사가 먼저 차단해 일차 사유에 드러나지 않았습니다. 인용 오류가 모두 해결됐다고 계산하지 않았습니다. [인용 전수 대조·실행 분석](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/actual-api-analysis-v1/analysis.json)

**수정 효과:** 새 생성에서 검사를 통과한 8후보를 각각 별도 엔진에서 측정했습니다. 7응답이 채택됐으나 서로 다른 질의로는 5개이며, 1응답은 효과가 없어 기각됐습니다.

| 범위 | 채택된 응답 | 기각된 응답 |
|---|---|---|
| 직접 비교 24회 | 접착제 무힌트·건조대 힌트·팔래트 양 조건·파스탤 양 조건: 6응답, 4질의 | 박자기 힌트: 1응답 |
| 추가 24회 | 측정기 무힌트: 1응답, 1질의 | 없음 |

채택된 각 후보의 표적 nDCG는 0→1, 박자기 힌트는 0→0이었습니다. 8후보 각각에 대해 기존 36질의와 개발 자료의 정답 있는 16질의를 검사한 지표 하락은 0건이었습니다. 후보들을 함께 적용한 결합 성능이나 평가셋 밖의 무회귀를 검증한 실험은 아닙니다.

**남은 실패:** 접착제는 무힌트에서 목공접착제를 올바르게 분해해 개선됐지만 힌트에서는 중복·빈 구성 요소로 차단됐습니다. 건조대 무힌트와 보호대 양 조건, 측정기 힌트는 실제 색인 복합어 대신 질의 자체를 분해해 차단됐습니다. microscope는 무힌트에서 대응 근거 부족으로 보류했고 힌트에서는 ‘광학 현미경’처럼 여러 단어로 된 대표어가 형식 조건을 통과하지 못했습니다. 박자기는 무힌트에서 미확인 의미 대응을 보류했지만 힌트에서는 다시 박자와 연결해 검색이 개선되지 않았습니다. 원인 계열 라벨이 맞더라도 패치의 의미와 효과가 보장되지 않는 사례입니다.

**의미 검토:** 기존 v3 24응답에는 원인 근거·원문 인용·의미적 지지·수정안·보류의 5축, 총 120개 AI 판정과 이유·불확실성을 작성했습니다. 같은 작업의 AI가 기존 메모·작성 qrels·게이트 결과를 본 사후 평가이며 독립적인 사람의 평가가 아닙니다. 이 평가를 새 48응답의 의미 판정으로 전용하지 않았습니다. 기존 응답과 새 응답의 사람 의미 평가는 미완료입니다. [새 실제 48응답](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/actual-api-v1/results.json) · [기존 24응답 AI 의미 평가](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/AI-SEMANTIC-REVIEW.md)

## 사용 화면

[새 실제48응답 화면](https://queryscope-zwia.onrender.com/generation-v4.html)에서는 직접 비교24와 추가24를 나누고 힌트 유무의 입력·원응답·인용·차단 이유·수정 효과를 대조합니다. 응답 ID와 사용량, 기존24응답의 원판정도 확인할 수 있습니다. 원인용의 문구 대조는 최초 차단 사유와 별도로 표시합니다.

[기존24응답 재검사 화면](https://queryscope-zwia.onrender.com/review-v4.html)은 당시 원판정과 새 적용 검사를 보존합니다. [v3 실제 응답](https://queryscope-zwia.onrender.com/generation-v3.html), [평가 비교](https://queryscope-zwia.onrender.com/evaluation-v3.html), 기반 PR의 과거 응답과 [v1 기록](https://queryscope-zwia.onrender.com/evaluation.html)도 별도입니다. 공개 화면은 저장 결과를 재생하는 정적 데모이며 모델 API 키를 전달하지 않습니다. 배포 SHA·공개 파일 대조·로컬 화면 검증 범위는 [최신 운영 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/LIVE-OPERATIONS.md)에 남깁니다.

## 운영 설정과 한계

실제 생성은 서버에서 명시적으로 활성화하고 운영 토큰으로 접근합니다. API 키는 화면에 전달하지 않습니다. 요청 전에 비용을 예약하고 자동 재시도 없이 호출 수를 제한합니다. v3의 과거 승인과 v4의 48회·최대 $0.60 승인을 구분하고, 완료된 승인이 새 호출로 자동 반복되지 않도록 했습니다.

이번에 확인한 것은 작성 자료에서의 검색·검사 결과입니다. 서로 다른 문자 체계의 후보를 찾았다는 사실이나 대표어가 색인에 있다는 사실만으로 동의어의 의미가 입증되지는 않습니다. 자연 발생 분해 오류 평가, 작성 가설·정답의 모호성 검토, 사람의 의미 평가가 남아 있습니다. 새 생성에서 상품 ID 인용 오류는 사라졌지만 문구 불일치, 정상 응답의 상태 오류, 잘못된 분해와 의미 대응은 남았습니다.

실고객 효과, 평가셋 밖의 무회귀, 장기 공개 생성 API 운영, 독립 평가셋에서의 일반화는 주장하지 않습니다. 모델 학습이나 LangChain·LlamaIndex 사용 경험으로 소개하지도 않습니다. 같은 개발 사례의 재실행만으로 재현성과 일반화가 확인되지는 않습니다. 다음 실험도 입력·모델·호출 수·비용을 별도로 정하고 새 응답과 저장 응답 재검사를 구분해야 합니다.

## 검증 자료

- [실제48응답 분석·남은 실패·검증 재현](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/ACTUAL-API.md) · [최신 CI·배포·화면 검증](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/LIVE-OPERATIONS.md)
- [v4 실제 48응답·직접 비교와 추가 사례](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/actual-api-v1/results.json)
- [기존 24응답 × 5축 AI 의미 평가](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/AI-SEMANTIC-REVIEW.md)
- [v4 저장 응답 재검사와 입력 준비](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/run-v1/audit.json)
- [기존 159개 파일 보존 대조](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/preservation.json)
- [사람 검토 안내](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/HUMAN-REVIEW-GUIDE.md) · [24응답 AI 사전 검토](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v4/AI-REVIEW.md)
- [v3 실제 API 원응답·비용·실패 분석](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/ACTUAL-API.md) · [v3 평가 구성](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v3/README.md)
- [v2 새 자료 결과와 한계](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v2/README.md) · [v1 수동 수정 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/queryscope-v1/README.md)
- [기반 PR·출처](https://github.com/sokldjs554/queryscope/blob/main/docs/PROVENANCE.md) · [과거 실제 API 기록](https://github.com/sokldjs554/queryscope/blob/main/docs/verification/alba-20261027/README.md) · [실행·운영 안내](https://github.com/sokldjs554/queryscope/blob/main/docs/queryscope-operation.md)
