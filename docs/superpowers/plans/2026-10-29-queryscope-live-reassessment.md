# QueryScope Live Reassessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 자료를 보존하며 48입력 실제 평가를 승인 직전 상태로 만들고 24건의 AI 의미 판정을 완성한다.

**Architecture:** 별도 runtime campaign 모듈이 준비·승인 검증·원응답 보존·runtime 효과 평가를 담당한다. 기존 OpenAI provider와 24회 Budget 두 개를 한 캠페인 아래 사용한다. 새 CLI와 GitHub workflow는 새 승인 파일에만 반응한다.

**Tech Stack:** Python 3.11/3.12, 기존 httpx/provider/pytest, GitHub Actions, JSON/Markdown.

**Spec:** `docs/superpowers/specs/2026-10-29-queryscope-live-reassessment-design.md`

## Global Constraints

- 새 유료 API 0회; 새 approved=true 기록 금지. 구현·검증·고정·배포 전 준비만 수행한다.
- suite queryscope-v4-runtime, 모델 gpt-5.4-mini-2026-03-17, 48회, $0.60, 800출력토큰, 11,000요청바이트.
- 기존 provider/Budget/llm_campaign/claim/v1-v3 원자료를 변경하지 않는다.
- 기존 키 재사용은 앞선 설정 승인에 따른다. 새 키 생성이나 키 값 출력은 없다.
- 과거 결과·사람 평가·새 준비 입력·AI 평가를 섞지 않는다.

## Review Focus

- 전체 raw 응답은 저장했지만 점수 계산이 실패한 경우: 원응답 보존, 불완전 상태, 자동 재개 금지.
- 입력 파일을 복사하거나 생성일만 바꾸는 재실행: 원본 prepared 해시뿐 아니라 고정 context/payload campaign identity로 중복 거절.
- 24번째와 25번째 호출 경계 및 실패 예약: 정확히 두 고정 원장, 49번째 거절, 오류도 예약 유지.
- 모델/사례쌍/문맥/원자료/payload/상한 변조: 네트워크 전 차단.
- 원래 24개와 추가 24개가 섞인 집계: 비교 가능 24개만 별도 paired summary, 사람 정답률은 산출하지 않음.

## Task 1: Runtime campaign

**Files:** Create `src/searchclinic/evaluation/runtime_campaign.py`, `tests/test_runtime_campaign.py`.

**Interfaces:**
- `prepare_runtime_campaign(output, source=DEFAULT_AUDIT) -> dict`: requests.json 및 approved=false 템플릿만 기록.
- `validate_runtime_preparation(prepared_dir) -> dict`: 고정 원자료·48쌍·context/payload·모델·상한 검증, 부작용 없음.
- `check_runtime_approval(prepared_dir, approval_path) -> dict`: 승인·준비 해시 검증 후 승인 metadata 반환.
- `execute_runtime_campaign(prepared_dir, output, approval_path) -> dict`: once-only 상태·예산·응답 저장·검사·보고.
- `assess_runtime_generation(raw, context, case, engine, evalset) -> dict`: runtime 적용 검사 후 gate, 기존 요약 키와 호환.
- `CAMPAIGN_STATE_ROOT`, `SUITE`, `MAX_CALLS`, `MAX_USD`: CLI/워크플로가 사용할 상수.

- [ ] RED: import 가능 여부만이 아닌 준비48건·provider 생성0, 거짓/변조 승인 거절, 중복 재실행, 49번째 예약 거절, 평가 실패 시 raw 보존, 없는 대표어 gate 미실행을 확인하는 테스트 작성/실행.
- [ ] GREEN: 별도 모듈로 위 계약만 구현. 기존 모듈 수정 없음. SHA뿐 아니라 고정 payload 집합 identity로 복사/날짜 변경도 재실행 거절.
- [ ] Verify: `pytest tests/test_runtime_campaign.py tests/test_queryscope_v2.py tests/test_queryscope_v3.py tests/test_runtime_audit.py -q`; 모두 통과.

## Task 2: CLI, remote claim and inert workflow

**Files:** Create `scripts/evaluate_queryscope_runtime_llm.py`, `src/searchclinic/evaluation/runtime_campaign_io.py`, `tests/test_runtime_campaign_cli.py`, `tests/test_runtime_campaign_transport.py`, `.github/workflows/queryscope-v4-runtime-approved.yml`.

**Interfaces:** Task1의 prepare/check/execute/state 상수를 사용한다. CLI 기본은 무료 준비; --live는 --prepared/--approval 필수. 원격 ref는 `refs/tags/queryscope-v4-runtime-paid-<canonical_campaign_sha256>`이며 execute 내부에서 `acquire_remote_claim`을 반드시 호출한다. `RecordingClient`가 HTTP 응답을 파싱 전에 저장하고 `verify_generation_provenance`가 관측 모델·ID를 확인한다.

- [ ] RED: 승인 전 provider/network0, 잘못된 GitHub repository/attempt/commit/approval 거절, 기존 원격 ref 재사용·4xx/5xx에서 retry0 테스트.
- [ ] GREEN: 새로운 live-approval.json 생성 push만 실행하는 워크플로. 실제 승인 파일은 만들지 않음. key 존재확인→실행기 내 승인검증·원격claim→실행→always 영수증·artifact·별도 결과branch 보존. 별도 claim-only CLI는 제공하지 않는다.
- [ ] Verify: CLI/claim 테스트, actionlint(사용가능 시), 전체 pytest. 기존 워크플로 바이트 불변 확인.

**코드 검토 후 수정:** 실행기 외부 claim 단계가 선택적으로 우회되는 문제, provider 실패의 원문 손실, 모델·ID의 기본값/중복 허용을 중요 결함으로 받아들였다. 실제 provider와 HTTP MockTransport를 사용하는 11개 실패 재현을 먼저 확인하고, 실행기 내부 claim·응답 기록기·관측 출처 검증으로 수정한다. 초기 별도 claim 스크립트 설계는 이 구조로 대체했다.

## Task 3: Complete explicit AI semantic assessments

**Files:** Create `docs/verification/queryscope-v4/ai-semantic-review-v1.json`, `AI-SEMANTIC-REVIEW.md`.

- [ ] 원응답24건을 읽고 원인근거·원문인용·의미지지·패치의미/효과·보류적절성의 판정·이유·불확실성을 기록.
- [ ] source_sha/response_id/context_sha/JSON Pointer 연결, 24고유쌍·5축 확인, 사람 원본 해시 불변 확인.
- [ ] 원본 작성자의 가설·과거 AI메모에 접근했다는 한계를 명시; AI 정확도를 사람 정답률로 합산하지 않음.

## Task 4: Freeze, review, publish and request final paid approval

**Files:** `docs/verification/queryscope-v4/live-prepared-v1/`, `LIVE-EVALUATION-PROPOSAL.md`, free verification reports, updated v4 README.

- [ ] 48입력을 고정하고 모델·입력·토큰/요청 제한·횟수·현행 단가·비용 예상 및 상한·실패 처리·기존24짝비교 범위를 구체화.
- [ ] 별도 코드 검토 후 중요 결함은 실패 재현→수정→전체 검증으로 처리.
- [ ] 원격 CI까지 확인하고 모든 과거 기록 보존. actual API 결과 파일은 생성하지 않음.
- [ ] 사용자에게 무료로 완료한 작업과 준비물을 제시하고 48회/$0.60에 대한 최종 확인만 요청.
