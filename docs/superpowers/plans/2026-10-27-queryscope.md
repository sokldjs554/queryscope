# QueryScope Implementation Plan

> Execute inline with superpowers:executing-plans. Spec: ../specs/2026-10-27-queryscope-design.md

Goal: PR #2 이력을 보존하는 QueryScope와 재현 가능한 무료 평가.
Architecture: 기존 Python 패키지 유지, 새 검증/평가 모듈과 독립 결과 디렉터리.
Constraints: 원본 무수정, 추가 유료 호출 0, 작성 데이터임을 공개, 실패 보존.
Review focus: 잘못된 의미 확정, 단어 없는 후보, 데이터 누수, 유료 캠페인 재실행, 정답 없는 질의 평균 왜곡.

- [x] 1. 출처·프로토콜·정답 고정. SHA 검증/중복 질의 검사. 커밋 후 최초 평가.
- [x] 2. tests/test_queryscope.py: unknown/비관련 인용의 검토 표시, 사전만 후보 무효 vs 명시적 연결, 잘못된 복합어 차단, 비용 차단을 RED→GREEN.
- [x] 3. rag/candidate_review.py에 build_link_candidate(query,canonical) 구현. 관측과 명시적 대응만 사용, 전역 설정 불변.
- [x] 4. scripts/evaluate_queryscope.py: manifest 검증, baseline/candidate 순위, paired context, 기존 응답 rubric 감사, 별도 출력·해시·환경. 정답 없는 행 별도 집계.
- [x] 5. 데모 브랜드/검토 구분/새 결과 표시. README·provenance·운영·지원 자료 갱신은 결과 후.
- [x] 6. 전체 pytest, 무료 평가, HTTP/브라우저·git diff 검사, 최종 리뷰, 별도 저장소 업로드 또는 bundle 보존.

## Execution ledger

Source isolated clone on queryscope branch; original upstream push disabled. Inputs frozen in 4be6122 before any new evaluation. Manual candidate tests used only legacy cases. First evaluation f973b9a; output immutable.

Ruling: extra paid generation prohibited — measured retrieval ablations and validator contracts only; new LLM outcomes remain not_run. Cost: diagnosis/abstention generalization remains unknown.

Ruling: fresh reviewer classified whitespace/stale effect fields minor; promoted to important because they misstate verification. Five RED tests, fixed, full suite 353 pass.

Ruling: reviewer declined independent semantic/qrels/generalization/provider/public operation claims; retained as explicitly unverified, no invented success.

Original application Library files inaccessible through available direct file tools; separate repo drafts created, original revision pending attachment. New remote and Render static deployment tracked in final verification record.
