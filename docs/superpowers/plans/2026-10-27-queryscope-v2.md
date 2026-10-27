# QueryScope v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 무힌트 검색과 남은 검색 실패를 보완하고 새 독립 자료/실제 LLM 평가 실행 준비 및 검증 가능한 데모·지원 문서를 제공한다.
**Architecture:** 순수 observation builder를 API/평가에서 공유, frozen bundle과 별도 offline/live 실행기를 분리, legacy 입력 재현 경로 보존.
**Tech Stack:** Python, Kiwi, BM25, Pydantic, FastAPI, 정적 JS, pytest/Playwright.
**Spec:** docs/superpowers/specs/2026-10-27-queryscope-v2-design.md

## Global Constraints
- 추가 유료 API 호출 0회; 별도 승인 전 --live 실행하지 않음.
- 이전 raw/results 파일 보존; 새 데이터와 판정 기준 먼저 Git/SHA 고정.
- v1 24개는 개발용; 새평가 결과 뒤 이 셋에 대한 튜닝 금지.
- 자동 의미 확정 없음; independent_human_review=pending.

## Review Focus
- 유사한 철자나 부분일치가 곧 원인 확정으로 표현되지 않을 것.
- 빈/한글 외 입력, 범위 밖 요청, 근거 없는 입력에 패치 강요하지 않을 것.
- 준비물 변조·재실행·누락 승인·부분 호출 실패에도 예산 우회/성공 집계 없을 것.
- 본문 발췌 오프셋/인용이 실제 원문과 대응하고 기존 응답은 바뀌지 않을 것.
- v1/기존36/새18상품 순위 및 테스트 응답/실제 응답이 섞이지 않을 것.

### Task 1: Freeze and diagnose
- [ ] 새 catalog/cases/rubric/protocol manifest 커밋; baseline 코드·원시결과·CI·공개접속 확인 기록.
- [ ] v1개발 사례 토큰/검색/원문 분석; 새로운 평가 점수는 아직 실행하지 않음.

### Task 2: Observation retrieval
Files: src/searchclinic/rag/observations.py, explanation_service.py; scripts/evaluate_queryscope.py; tests/test_observation_retrieval.py.
Interface: build_context(engine, retriever, query, problem, strategy='observed') -> (context, docs). Inputs contain no evaluation metadata.
- [ ] dropped/split, raw substring without index match, fuzzy spelling, excerpt offset, no label leak tests RED.
- [ ] 관측 query 보강/발췌 구현; legacy 명시 경로 유지; focused tests GREEN.

### Task 3: LLM preparation and separated assessment
Files: src/searchclinic/evaluation/queryscope_v2.py, scripts/evaluate_queryscope_v2.py, scripts/evaluate_queryscope_llm.py, tests/test_queryscope_v2.py.
Interfaces: load_bundle(path), prepare(output), score(raw, context, reference, engine, evalset); new only output directories.
- [ ] hash tamper/default no provider/missing approval/output overwrite/abstention with patch tests RED.
- [ ] offline runner+paired24call dry-run+approved-only live executor; rows/errors/receipts persisted, review template pending.
- [ ] all tests GREEN; prepare but never live.

### Task 4: Failure repair and locked evaluation
Files: candidate_review.py, scripts/evaluate_queryscope_v2.py, tests/test_queryscope_v2.py, docs/verification/queryscope-v2/run-v1/.
- [ ] 카페트/초콜렛/워시 개발자료 분석과 후보 회귀 검사. malformed compound/whitespace/status contradictions tests RED then fix.
- [ ] 개발 개선 코드 커밋 후 동결된 새셋 최초실행, 모든하락/계열별hit/새상품 overlap 기록. 결과보고후튜닝하지않음.

### Task 5: Demo, verification and application docs
Files: web/evaluation-v2.*, scripts/browser_queryscope_v2.cjs, README, docs/application/*.
- [ ] 결과기반 새화면 + legacy보존. local desktop/mobile/errors tests, HTTP operations, full pytest/baseline.
- [ ] fresh whole-branch reviewer, 중요문제 RED->GREEN, 필요시 full suite.
- [ ] push new code, CI, Render 배포/공개접속 확인; 문서와 자소서 실제 결과로만 업데이트.
