# QueryScope

한국어 검색 실패의 **관측 → 원인 설명 → 인용 근거 → 수정 후보 → 회귀 판정**을 연결합니다. 설명의 원문 인용, 의미적 타당성, 실제 수정 효과를 나눠 확인하는 Python 프로젝트입니다.

[ko-search-clinic PR #2](https://github.com/sokldjs554/ko-search-clinic/pull/2)의 RAG 서비스와 전체 Git 이력을 이어받았습니다. 기준 `493935f6`, 보존 태그 `upstream-pr2`. [출처](docs/PROVENANCE.md). 알바천국 AI 개발자 지원용 개인 프로젝트이며 Codex를 구현·분석·문서 작성에 활용했습니다. 실제 알바천국 데이터나 운영 성과가 아닙니다.

## 먼저 보기

- [과거 실제 API 응답 재생](https://queryscope-zwia.onrender.com/): 기존에 생성한 24응답과 수정안 채택·기각 기록.
- [v3 정상 검색·통제된 누락 비교](https://queryscope-zwia.onrender.com/evaluation-v3.html): 정상 검색의 잘못된 누락 신호와 미개선 사례.
- [v2 보존 상품·무힌트 검색 비교](https://queryscope-zwia.onrender.com/evaluation-v2.html): 새 작성 자료의 개선, 하락, 미해결 사례.
- [v1 보존 결과](https://queryscope-zwia.onrender.com/evaluation.html): 이전 24질의 결과. 이번 개선에는 개발 자료로 사용했습니다.

공개 사이트는 **저장 결과를 읽는 정적 데모**입니다. 새 모델을 호출하지 않습니다. 검증 환경에서 공개 주소 접속은 프록시 CONNECT 403과 웹 도구 접근 제한으로 확인하지 못했습니다. 로컬 데스크톱·모바일 검사는 통과했습니다. 최신 배포 상태와 확인 범위는 [운영 기록](docs/verification/queryscope-v3/OPERATIONS.md)에 구분합니다.

## 이번에 확인한 결과

기존 상품 카탈로그 72건과 평가셋 36질의(건강 20 + 실패 16)는 회귀 검사에 유지합니다. v1·v2 자료는 후속 개선에 사용해 **개발 자료**로 전환했습니다. 새로운 **16상품·24질의**의 정답·기준·분석기 구성을 실행 전에 `2e7ec2c`와 SHA-256으로 고정했습니다. 이전 실제 API와 v1/v2 자료는 보존했습니다.

| 대상 | v2 → v3 결과 | 해석 |
|---|---|---|
| 새 정상8개: 잘못된 복합어 누락 신호 | **8/8 → 0/8** | 양조건 동일, 실제 진단/보류 성능 아님 |
| 새8개 계열: 무힌트 근거 hit@3 | **7/8 → 7/8** | 개선 없음, microscope 실패 유지 |
| 새8개 계열: 힌트 hit@3 | 8/8 → 8/8 | 일반 원칙 검색 |
| v2 개발15개: 무힌트 hit@3 | 10/15 → 11/15 | 유의어2/3→3/3 복구, 개발 성과 |
| 통제된 분해 수정4개, 순위16개 평균 | 0.5000 → 0.7500 | 강제로 만든 누락을 되돌린 수동 실험 |
| 카페트 / 초콜렛 / 워시 | v2 수정 결과 동일 재현 | 향초 잔여 문제 유지 |

4개 복합어는 통짜 색인을 강제한 통제 시나리오이며 자연 발생 고객 장애가 아닙니다. 정상8개와 누락4개의 사전조건을 검사하고 점수를 계산했습니다. 새 분해 오류 계열은 **n=0 미평가**입니다. 표기·영한·유의어의 미해결 상품 검색4개도 남습니다.

새 분석어휘78개 중19개(24.36%)는 기존90상품과 겹칩니다. 같은 작성자·도메인·접미표현·운영 지식을 공유하며 독립 인간 검토가 없어 고객 일반화나 모든 약점 해결을 주장하지 않습니다. [새 계열별 결과·실패·원시 입력·재현](docs/verification/queryscope-v3/README.md).

과거 v2의 새 자료 결과(무힌트6/15→10/15, 유의어3/3→2/3 하락, 순위0.5351→0.5351)는 당시 기록으로 그대로 보존했습니다. [v2 기록](docs/verification/queryscope-v2/README.md).

## 무엇을 바꿨나

기존 근거 검색은 질의와 관찰 문장만 사용했습니다. 이제 실제 분해 토큰·버려진 품사·원문과 색인 차이·가까운 표기·문자 체계를 검색에 활용합니다. 긴 문서는 관련된 연속 본문을 발췌하고 원문 위치를 남깁니다. 이 관측은 **가설**이며 원인 확정이나 동의어 자동 승인이 아닙니다.

v3에서는 원문 단어 자체가 아니라 실제 분석 토큰의 색인 포함 여부를 검사해 정상 접미 분석을 누락으로 오해하지 않게 했습니다. 발췌 분석은 최대512항목 캐시로 반복 계산을 줄이고, 과거 `observed_v2` 재현 경로도 보존했습니다.

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

[http://127.0.0.1:8000/demo/](http://127.0.0.1:8000/demo/) → **v3 비교 보기**에서 사례를 선택하면 입력·토큰·기존/보완 문서·인용 원문을 따라갈 수 있습니다. API 키 없이 동작합니다.

```bash
python -m pytest -q
clinic baseline
python scripts/evaluate_queryscope_v3.py --output work/reproduction-v3
python scripts/evaluate_queryscope_v2.py --output work/reproduction-v2
python scripts/evaluate_queryscope_llm.py --suite queryscope-v3 --output work/llm-prepared-v3
python scripts/verify_queryscope_operations.py --output work/operations-v3
```

출력 폴더가 이미 있으면 중단하며, 동결 자료의 해시가 다르면 평가하지 않습니다. `evaluate_queryscope_llm.py` 기본 실행은 공급자를 만들지 않는 무료 준비 모드입니다. [전체 원자료·재현 근거](docs/verification/queryscope-v3/README.md).

로컬 전체 검사 **378 passed, 1 skipped, 2 deselected**. 기본 검색 기준선 평균 nDCG0.5839 유지. 1440/320/390/650px에서 재생·비교·원문 펼침·로딩 실패·가로 넘침을 검사했습니다. [검사·지연·CI·배포 범위](docs/verification/queryscope-v3/OPERATIONS.md). 공개 접속과 실제 모델 품질은 별도 미확인입니다.

## 실제 LLM 평가의 남은 단계

**이번 추가 유료 호출0, 새 모델 응답0**입니다. 이전 승인24회는 소진됐고 기본 호출 한도0과 종료 캠페인 차단을 유지합니다. v3 새 사례12개×힌트유무=24회의 입력·예산·독립 인간 검토표와 실행 코드를 준비했습니다.

[미승인 평가안](docs/verification/queryscope-v3/PAID-EVALUATION-PROPOSAL.md): `gpt-5.4-mini-2026-03-17`, 24회, 비용 예약 상한 **$0.30**. 별도 사용자 승인과 준비물 해시에 결합된 승인 파일 없이는 실행하지 않습니다. v2 준비물도 별도 보존하며 합쳐48회로 승인된 것은 아닙니다. 오류·invalid·보류·잘못된 패치를 분리하고 이전/테스트 응답을 새 결과로 집계하지 않습니다.

**미실행:** 새 질의의 실제 모델 진단·보류·설명 타당성, 독립 인간 의미/정답 평가, 실제 채용 데이터 성능, 공개 생성 API 장기 운영. 기존 [실제 API24회 결과](docs/verification/alba-20261027/README.md)와 [v1 원자료](docs/verification/queryscope-v1/README.md)는 별도로 보존합니다.

[지원용 자소서](docs/application/cover-letter.md) · [포트폴리오](docs/application/portfolio.md) · [문서 수정 근거](docs/application/REVISION-NOTES.md) · [기존 상세 검색 실험](README-legacy.md).
