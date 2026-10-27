# QueryScope

한국어 검색 실패의 **관측 → 원인 설명 → 인용 근거 → 수정 후보 → 회귀 판정**을 연결하는 Python 프로젝트입니다. 설명이 그럴듯해도 인용의 의미나 수정 효과가 입증된 것은 아니라는 점을 드러냅니다.

알바천국 AI 개발자 지원용으로 [ko-search-clinic PR #2](https://github.com/sokldjs554/ko-search-clinic/pull/2)의 RAG 서비스와 전체 Git 이력을 이어받았습니다. 기준 커밋은 `493935f6`, 태그는 `upstream-pr2`입니다. [출처와 변경 이력](docs/PROVENANCE.md).

직접 작성한 상품 카탈로그 72건을 사용합니다. 기존 평가셋 36질의(건강 20 + 실패 16)는 회귀 게이트로 유지하고, 신규 24질의와 분리합니다. 실제 채용 공고·알바천국 고객 데이터가 아닙니다. 구현·실험·문서 작성에 Codex를 사용했습니다.

## 데모 실행

**공개 저장 결과 데모:** [QueryScope](https://queryscope-zwia.onrender.com/) · [새 평가 비교](https://queryscope-zwia.onrender.com/evaluation.html).
Render가 검증 코드 `714600f`의 배포를 `live`로 보고했습니다. 공개 주소의 외부 HTTP/브라우저 접속은 현재 검증 환경의 네트워크 제한으로 확인하지 못했습니다. 아래 로컬 실행과 화면 검사는 완료했습니다. [배포 확인 범위](docs/verification/queryscope-v1/deployment.json).

Python 3.11 또는 3.12:

```bash
git clone https://github.com/sokldjs554/queryscope.git
cd queryscope
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[api]'
python -m searchclinic.api.explanation_api
```

[http://127.0.0.1:8000/demo/](http://127.0.0.1:8000/demo/)에서 시작합니다.

1. **새 검증 결과**: 신규 24질의의 전후 순위와 힌트 유무별 입력·검색 문서를 비교합니다.
2. **저장 결과 열람**: PR #2에서 실제 생성한 응답 24건의 재검증 기록을 재생합니다. 새 생성이 아닙니다.
3. 아답터·백팩을 선택하면 과거 후보의 기각 사유를 볼 수 있습니다. 새 수정 후보와 효과는 새 검증 결과에서 따로 확인합니다.

API 키 없이 동작합니다. **추가 유료 호출은 0회이며 기본 호출 한도도 0회**입니다. 기존 24회 캠페인은 종료해 실행 경로를 차단했습니다. 새 API 생성은 별도 예산 승인과 서버 설정이 필요합니다. [운영 및 재현](docs/queryscope-operation.md).

## 새로 확인한 결과

실행 전에 [24개 질의·정답·프로토콜](docs/verification/queryscope-v1/PROTOCOL.md)을 Git 커밋과 SHA-256으로 고정했습니다. 기존 36질의와 정확히 같은 질의는 없으나 같은 상품과 어휘를 재사용하므로 완전한 독립 일반화 평가가 아닙니다.

| 검사 | 실제 결과 | 해석 범위 |
|---|---|---|
| 신규 순위 평가 20질의 | 평균 nDCG@10 **0.8255 → 0.9142**, 4개 개선 | 아답터·백팩 두 수동 후보를 함께 적용; 측정 지표 하락 0건 |
| 자료 부족 4질의 | 전후 검색 결과 0건 | 순위 평균 제외; 모델의 보류 성공으로 계산하지 않음 |
| 신규 원인 계열 11질의의 근거 hit@3 | **힌트 11/11 → 무힌트 1/11** | 검색만 평가; 새 LLM 진단 정확도 아님 |
| 과거 9질의의 근거 hit@3 | 힌트 8/9 → 무힌트 6/9 | 기존 개발 사례, 신규 결과와 분리 |
| 아답터·백팩 | 사전만: 각각 0→0 / 사전+표준형 연결: 각각 **0→1** | 후보별 기존 36질의 게이트 채택, 허용치 .02 초과 회귀 없음 |
| 잘못된 티슈 복합어 후보 | 원응답 차단 유지; 별도 물티슈→물+티슈 후보 0→1 | 수동 후보, 새 모델 생성 성과 아님 |

남은 순위 실패: **거실 카페트 0.8262, 초콜렛 선물 0.4582, 워시 0**. 낮은 무힌트 검색 결과를 확인한 뒤 이 평가셋에 맞춰 검색기를 수정하지 않았습니다.

[전체 결과·실패 분석](docs/verification/queryscope-v1/README.md) · [원자료](docs/verification/queryscope-v1/run-v1/results.json) · [설명 평가 기준](docs/verification/queryscope-v1/rubric.json).

## 근거를 판정하는 방법

- **원인 분류**: 저장 응답의 라벨 비교와 관측 충분성을 구분합니다. 백팩의 `compound_locked` 분류는 기존 참조 라벨 및 분해 관측과 맞지 않습니다.
- **인용 추적**: 제공 문서 ID와 본문 인용을 대조합니다. 단어·어미를 바꾼 인용은 복원하지 않습니다.
- **의미적 지지**: 인용한 일반 원칙이 이번 질의의 원인을 입증하는지는 자동 확정하지 않고 `requires_human_review`로 표시합니다.
- **수정 후보**: 구조 검사와 실제 순위 효과를 구분합니다. 게이트 통과는 정해진 평가셋의 결과이며, 현실의 동의 관계나 고객 효과를 증명하지 않습니다.

## 재현

```bash
pip install -e '.[api,mcp,dev,scale]'
python -m pytest -q
clinic baseline
python scripts/evaluate_queryscope.py --output work/reproduction-1
python scripts/verify_queryscope_operations.py --output work/operations-1
```

**최종 로컬 검사: 353 passed, 1 skipped, 2 deselected.** 기존 기준선 평균 nDCG 0.5839 유지, 수정 후 새 평가 재현 값 일치.
검증 코드 `714600f`의 [GitHub Actions](https://github.com/sokldjs554/queryscope/actions/runs/40480583240)도 Ubuntu·Windows 테스트와 검색 품질 게이트 모두 통과했습니다.

결과 디렉터리가 이미 있으면 중단합니다. 정답/프로토콜 파일의 해시가 다르면 평가를 시작하지 않습니다. 브라우저: Playwright/Chromium 준비 후 `node scripts/browser_queryscope.cjs`.

[로컬 HTTP 측정](docs/verification/queryscope-v1/operations/operations.json): 120회 순차 GET 모두 200, 기본 생성 요청은 예상한 503, 빈 입력은 422. 준비 이후 p95 1.937ms는 로컬 정적 자료/상태 조회 수치이며 모델 지연·공개 운영 SLA가 아닙니다.

## 기존 결과와 남은 범위

PR #2의 실제 API 24회·추정 $0.02903175와 저장 응답 사후 재검증은 [이전 기록](docs/verification/alba-20261027/README.md)에 보존했습니다. 새 실험과 합산하지 않습니다.

**미확인:** 새 질의에서 LLM의 힌트/무힌트 원인 정확도·설명 타당성·자연 발생 보류율, 독립 인간 의미 평가, 실제 채용 검색 성과, 공개 생성 API 장기 운영. [추가 평가안](docs/verification/queryscope-v1/PAID-EVALUATION-PROPOSAL.md)은 모델·24회·비용을 명시한 미승인 계획이며 실행하지 않았습니다.

별도 초안(기존 Library 원본 대조 대기): [지원용 자소서 문안](docs/application/cover-letter.md) · [포트폴리오](docs/application/portfolio.md) · [기존 상세 검색 실험](README-legacy.md).
