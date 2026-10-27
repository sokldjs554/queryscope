# QueryScope

한국어 검색 실패의 **관측 → 원인 설명 → 인용 근거 → 수정 후보 → 회귀 판정**을 연결합니다. 설명의 원문 인용, 의미적 타당성, 실제 수정 효과를 나눠 확인하는 Python 프로젝트입니다.

[ko-search-clinic PR #2](https://github.com/sokldjs554/ko-search-clinic/pull/2)의 RAG 서비스와 전체 Git 이력을 이어받았습니다. 기준 `493935f6`, 보존 태그 `upstream-pr2`. [출처](docs/PROVENANCE.md). 알바천국 AI 개발자 지원용 개인 프로젝트이며 Codex를 구현·분석·문서 작성에 활용했습니다. 실제 알바천국 데이터나 운영 성과가 아닙니다.

## 먼저 보기

- [과거 실제 API 응답 재생](https://queryscope-zwia.onrender.com/): 기존에 생성한 24응답과 수정안 채택·기각 기록.
- [v2 새 상품·무힌트 검색 비교](https://queryscope-zwia.onrender.com/evaluation-v2.html): 새 작성 자료의 개선, 하락, 미해결 사례.
- [v1 보존 결과](https://queryscope-zwia.onrender.com/evaluation.html): 이전 24질의 결과. 이번 개선에는 개발 자료로 사용했습니다.

공개 사이트는 **저장 결과를 읽는 정적 데모**입니다. 새 모델을 호출하지 않습니다. 검증 환경에서 공개 주소 접속은 프록시 CONNECT 403과 웹 도구 접근 제한으로 확인하지 못했습니다. 로컬 데스크톱·모바일 검사는 통과했습니다. 최신 배포 상태와 확인 범위는 [운영 기록](docs/verification/queryscope-v2/OPERATIONS.md)에 구분합니다.

## 이번에 확인한 결과

기존 상품 카탈로그 72건, 평가셋 36질의(건강 20 + 실패 16), v1의 24질의는 개발·회귀 자료입니다. 별도 **18상품·24질의**를 작성해 정답·기준을 실행 전 커밋과 SHA-256으로 고정했습니다.

| 대상 | 결과 | 해석 |
|---|---|---|
| v1 개발 11개, 무힌트 근거 hit@3 | **1/11 → 10/11** | 개선에 사용한 자료 |
| 새 15개 계열 가설, 무힌트 hit@3 | **6/15 → 10/15** | 일반 원칙 문서 검색이며 진단 정확도 아님 |
| 새 15개, 힌트 hit@3 | 9/15 → 11/15 | 같은 질의·문서 한도·판정 기준 |
| 새 유의어 계열 | **3/3 → 2/3** | 악화 사례도 보존 |
| 카페트 / 초콜렛 선물 / 워시 | 0.8262→1 / 0.4582→0.9832 / 0→1 | 수동 후보, 기존36+v1정답있는20 게이트 통과 |
| v1 개발20 순위 평균 nDCG@10 | 0.9142 → 0.9992 | 세 후보 추가, 측정 지표 하락0 |
| 새18 순위 평균 nDCG@10 | **0.5351 → 0.5351** | 같은 설정을 적용해도 개선0·하락0 |

새 분해 오류 가설3개는 근거 hit@3 **0/3**입니다. 실제 토큰 분석과 작성 가설이 맞지 않는 사례도 발견했습니다. 초콜렛 선물에는 무관한 향초가 남고, 원문 부분일치 신호가 정상 형태소 분석을 오류로 취급하는 반례도 있습니다. [계열별 결과·실패·정답 모호성](docs/verification/queryscope-v2/README.md)을 확인할 수 있습니다.

새 카탈로그 어휘93개 중15개(16.13%)는 기존 자료와 겹칩니다. 같은 작성자·상품 도메인·운영 지식을 공유하며 독립 인간 검토가 없으므로 독립적인 고객 일반화를 주장하지 않습니다.

## 무엇을 바꿨나

기존 근거 검색은 질의와 관찰 문장만 사용했습니다. 이제 실제 분해 토큰·버려진 품사·원문과 색인 차이·가까운 표기·문자 체계를 검색에 활용합니다. 긴 문서는 관련된 연속 본문을 발췌하고 원문 위치를 남깁니다. 이 관측은 **가설**이며 원인 확정이나 동의어 자동 승인이 아닙니다.

원인 분류, 인용 추적, 의미적 지지, 수정 구조, 실제 검색 효과를 구분합니다. 원문에 있는 인용도 해당 진단을 뒷받침하는지는 `requires_human_review`로 남깁니다. 후보는 별도 엔진에서 검사하고 기본 검색 설정을 자동 변경하지 않습니다. 과거 잘못된 응답은 보존하고 현재의 구조 검사·프롬프트를 보완했습니다.

## 실행과 재현

Python 3.11 또는 3.12:

```bash
git clone https://github.com/sokldjs554/queryscope.git
cd queryscope
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[api,mcp,dev,scale]'
python -m searchclinic.api.explanation_api
```

[http://127.0.0.1:8000/demo/](http://127.0.0.1:8000/demo/) → **v2 새 상품·힌트 비교**에서 사례를 선택하면 입력·토큰·기존/보완 문서·인용 원문을 따라갈 수 있습니다. API 키 없이 동작합니다.

```bash
python -m pytest -q
clinic baseline
python scripts/evaluate_queryscope_v2.py --output work/reproduction-v2
python scripts/evaluate_queryscope_llm.py --output work/llm-prepared-v2
python scripts/verify_queryscope_operations.py --output work/operations-v2
```

출력 폴더가 이미 있으면 중단하며, 동결 자료의 해시가 다르면 평가하지 않습니다. `evaluate_queryscope_llm.py` 기본 실행은 공급자를 만들지 않는 무료 준비 모드입니다. [전체 원자료·환경·재현 근거](docs/verification/queryscope-v2/README.md).

로컬 전체 검사 **370 passed, 1 skipped, 2 deselected**. 기본 검색 기준선 평균 nDCG 0.5839를 유지합니다. 검증 코드 `18beac2`의 [Ubuntu·Windows 테스트와 검색 품질 CI](https://github.com/sokldjs554/queryscope/actions/runs/40497362426)도 모두 통과했습니다. 1440/320/390/650px에서 기존 재생과 새 비교 화면을 검사했습니다. 공개 접속·실제 공급자 장애·생성 지연 검증은 이 검사에 포함하지 않습니다.

## 실제 LLM 평가의 남은 단계

**이번 추가 유료 호출0, 새 모델 응답0**입니다. 이전 승인24회는 소진됐고 기본 호출 한도0과 종료 캠페인 차단을 유지합니다. 새 사례12개×힌트유무=24회의 입력·예산·독립 인간 검토표와 실행 코드를 준비했습니다.

[미승인 평가안](docs/verification/queryscope-v2/PAID-EVALUATION-PROPOSAL.md): `gpt-5.4-mini-2026-03-17`, 24회, 비용 예약 상한 **$0.30**. 별도 사용자 승인과 준비물 해시에 결합된 승인 파일 없이는 실행하지 않습니다. 오류·invalid·보류·잘못된 패치를 분리하고 이전/테스트 응답을 새 결과로 집계하지 않습니다.

**미실행:** 새 질의의 실제 모델 진단·보류·설명 타당성, 독립 인간 의미/정답 평가, 실제 채용 데이터 성능, 공개 생성 API 장기 운영. 기존 [실제 API24회 결과](docs/verification/alba-20261027/README.md)와 [v1 원자료](docs/verification/queryscope-v1/README.md)는 별도로 보존합니다.

[지원용 자소서](docs/application/cover-letter.md) · [포트폴리오](docs/application/portfolio.md) · [문서 수정 근거](docs/application/REVISION-NOTES.md) · [기존 상세 검색 실험](README-legacy.md).
