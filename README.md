# QueryScope

한국어 검색 실패의 **관측 → 원인 설명 → 인용 근거 → 수정 후보 → 회귀 판정**을 연결합니다. 설명의 원문 인용, 의미적 타당성, 실제 수정 효과를 나눠 확인하는 Python 프로젝트입니다.

[ko-search-clinic PR #2](https://github.com/sokldjs554/ko-search-clinic/pull/2)의 RAG 서비스와 전체 Git 이력을 이어받았습니다. 기준 `493935f6`, 보존 태그 `upstream-pr2`. [출처](docs/PROVENANCE.md). 알바천국 AI 개발자 지원용 개인 프로젝트이며 Codex를 구현·분석·문서 작성에 활용했습니다. 실제 알바천국 데이터나 운영 성과가 아닙니다.

## 먼저 보기

- [v4 후속 검사·검토 자료](docs/verification/queryscope-v4/README.md): 같은 실제 24응답의 원판정과 새 적용 검사를 비교합니다. 신규 모델 호출은 0회이며 로컬 `/demo/review-v4.html`에서 확인합니다. v4 CI·배포 확인은 진행 중입니다.
- [v3 새 실제 모델 응답 24건](https://queryscope-zwia.onrender.com/generation-v3.html): 힌트 유무, 인용 차단, 보류와 수정 효과 비교.
- [과거 실제 API 응답 재생](https://queryscope-zwia.onrender.com/): 기존에 생성한 24응답과 수정안 채택·기각 기록.
- [v3 정상 검색·통제된 누락 비교](https://queryscope-zwia.onrender.com/evaluation-v3.html): 정상 검색의 잘못된 누락 신호와 미개선 사례.
- [v2 보존 상품·무힌트 검색 비교](https://queryscope-zwia.onrender.com/evaluation-v2.html): 새 작성 자료의 개선, 하락, 미해결 사례.
- [v1 보존 결과](https://queryscope-zwia.onrender.com/evaluation.html): 이전 24질의 결과. 이번 개선에는 개발 자료로 사용했습니다.

공개 사이트는 **저장 결과를 읽는 정적 데모**입니다. 새 모델을 호출하지 않습니다. 2026-10-27 사용자가 공개 접속과 수동 테스트 완료를 확인했습니다([확인 기록](docs/verification/queryscope-v3/USER-ACCEPTANCE.md)). Codex 환경의 직접 접속은 프록시 CONNECT403으로 차단됐던 기록을 유지합니다. 로컬 데스크톱·모바일 자동 검사도 통과했습니다. 최신 배포 상태와 확인 범위는 [운영 기록](docs/verification/queryscope-v3/OPERATIONS.md)에 구분합니다.

## 최신 v4: 원응답 보존과 실행 전 검사

v3 실제 응답에서 상품 관찰 ID를 지식 출처로 인용한 오류와 색인에 없는 대표어 후보를 확인해 런타임 계약을 보완했습니다. 지식 문서 ID만 인용하도록 입력에 허용 목록을 넣고, 기존 원문 인용 검사를 통과한 뒤에도 실제 색인 대표어·복합어 전체·질의와 수정 대상의 관계를 검사합니다. 상품 설명으로 찾은 후보는 의미 관계가 확인되지 않은 관찰로만 전달합니다.

| 측정 | v4 후속 결과 | 해석 |
|---|---|---|
| 저장된 실제24응답 재검사: 통과 / 보류 / 차단 | **7 / 9 / 8 → 6 / 9 / 9** | `microscope` 힌트 응답의 없는 대표어1건 추가 차단; 최초 판정 보존 |
| 실행 조건을 통과한6후보 | **4응답 채택 / 2응답 기각** | 채택은 고유2질의, 의미적 타당성은 사람 검토 필요 |
| v3 개발8개 계열: 무힌트 근거 hit@3 | **7/8 → 8/8** | 이미 본 개발 자료의 일반 원칙 검색, 새 모델 진단 성능 아님 |
| 새 런타임 입력 | **48건 준비 / 모델 응답0건** | 최대7,444바이트, 기존11,000바이트 한도 이내 |
| 과거 원자료·검토 | **159파일 보존 / 사람24건 pending** | AI 사전 검토와 독립 인간 판정을 구분 |

추가 모델 호출·새 모델 응답은 **0건**입니다. 인용 추적과 적용 가능성 검사를 보완했으며, 새 프롬프트가 생성 오류를 줄였다는 실측은 없습니다. 자료를 본 뒤 보완했으므로 v3는 이제 개발 자료입니다. [원자료·구현·검증·남은 한계](docs/verification/queryscope-v4/README.md) · [AI 사전 검토](docs/verification/queryscope-v4/AI-REVIEW.md) · [사람 검토 안내](docs/verification/queryscope-v4/HUMAN-REVIEW-GUIDE.md).

## v3에서 확인한 결과

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

[http://127.0.0.1:8000/demo/](http://127.0.0.1:8000/demo/) → **후속 검사·검토**에서 같은24응답의 원판정·후속 검사·미생성 입력을 비교합니다. **v3 비교 보기**에서는 이전 입력·토큰·문서·인용 원문을 확인합니다. API 키 없이 동작합니다.

```bash
python -m pytest -q
clinic baseline
python scripts/evaluate_queryscope_runtime.py --output work/reproduction-v4
python scripts/export_queryscope_runtime.py --input work/reproduction-v4/audit.json --output work/review-v4.json
python scripts/evaluate_queryscope_v3.py --output work/reproduction-v3
python scripts/evaluate_queryscope_v2.py --output work/reproduction-v2
python scripts/evaluate_queryscope_llm.py --suite queryscope-v3 --output work/llm-prepared-v3
python scripts/verify_queryscope_operations.py --output work/operations-v3
```

평가 출력 폴더가 이미 있으면 중단하며, 동결 자료의 해시가 다르면 평가하지 않습니다. v4는 실제 원응답·입력·준비 해시·응답ID의 연결도 검사하며 저장된24응답의 재검사와48입력 준비만 수행합니다. `evaluate_queryscope_llm.py` 기본 실행도 공급자를 만들지 않는 무료 준비 모드입니다. [v4 재현 근거](docs/verification/queryscope-v4/README.md) · [v3 원자료](docs/verification/queryscope-v3/README.md).

최신 로컬 전체 검사 **419 passed, 1 skipped, 2 deselected**(107.86초), 기본 검색 기준선 평균 nDCG0.5839 유지. [v4 테스트 기록](docs/verification/queryscope-v4/checks/pytest-final.txt). v4 화면은1440/320/390/650px에서24행·탐색·원판정 비교·미생성 표시·로딩 실패·가로 넘침 등12검사를 통과했습니다([브라우저 기록](docs/verification/queryscope-v4/browser-final/checks.json)). v4 CI·배포 확인은 진행 중이며 성공 여부는 별도 운영 기록에 추가합니다.

과거 v3의 [CI](https://github.com/sokldjs554/queryscope/actions/runs/40520729351)는 Ubuntu·Windows 테스트와 검색 품질 게이트를 통과했고, 공개 접속은 사용자 확인 기록이 있습니다. 이는 v4의 배포 확인과 구분합니다. [v3 검사·지연·CI·배포 범위](docs/verification/queryscope-v3/OPERATIONS.md). 독립 인간 의미 평가와 장기 운영 성능은 미완료입니다.

## 승인 후 실제 LLM 평가

고정12사례×힌트유무를 `gpt-5.4-mini-2026-03-17`로 **24회 실행해 실제 응답24건·API오류0건**을 확보했습니다. 토큰 기준 추정 비용은 **$0.0385605**, 예약 상한은$0.30이었습니다. 이번 승인은 소진됐으며 새 호출은 하지 않습니다. 과거 PR의24응답과 별도 결과입니다.

| 일차 자동 판정 | 무힌트12 | 힌트12 |
|---|---:|---:|
| 인용·형식 통과 / 보류 / 차단 | 3 / 5 / 4 | 4 / 4 / 4 |
| 작성 원인 계열 라벨 일치 | 4/6 | 5/6 |
| 보류+무패치+검증 통과 계약 | **4/6** | **4/6** |
| 보류 필요 사례에 패치 제안 | 0/6 | 0/6 |

8응답은 상품ID를 운영 지식 인용 출처로 사용해 차단됐습니다. 인용을 통과한7후보 중4응답(서로 다른2질의)은 nDCG0→1로 게이트 채택,3응답은 효과가 없어 기각됐습니다. 계열 라벨 일치나 인용 통과를 진단 정확도·의미적 지지로 표현하지 않습니다. 독립 인간 의미 평가는24건 모두 미완료입니다.

[실제 응답·실패 분석·비용·재현](docs/verification/queryscope-v3/ACTUAL-API.md). GitHub 시크릿은 실행 단계에서만 사용했고 값은 저장하지 않았습니다. 원격 실행 표식과24회 예산 원장을 보존해 자동 재실행을 차단합니다. 공개 사이트는 실제 응답을 **저장 재생**하며 API 키와 생성 서버를 게시하지 않습니다.

**남은 한계:** 정상 검색의 상태/인용 계약 실패, 원인 계열 혼동과 효과 없는 수정, 독립 인간 의미·정답 평가, 실제 채용 데이터 성능과 공개 장기 운영. 기존 [PR 실제 API24회](docs/verification/alba-20261027/README.md), v1/v2/v3 오프라인 기록은 별도로 보존합니다.

[지원용 자소서](docs/application/cover-letter.md) · [포트폴리오](docs/application/portfolio.md) · [문서 수정 근거](docs/application/REVISION-NOTES.md) · [기존 상세 검색 실험](README-legacy.md).
