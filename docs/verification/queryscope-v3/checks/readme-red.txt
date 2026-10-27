F                                                                        [100%]
=================================== FAILURES ===================================
____________________ test_documented_scale_matches_reality _____________________

    def test_documented_scale_matches_reality():
        """문서가 선언한 코퍼스 규모가 실제와 일치해야 한다.
    
        실측 실패: 질의를 하나 추가한 뒤 문서의 '66건/35질의/실패 15'가 그대로
        남아 조용히 거짓말이 됐다. 검증되지 않는 문서 수치는 반드시 낡는다.
    
        규모를 '선언하는' 문장만 대조한다 — 본문에는 '평가셋 16건을 순회'처럼
        부분집합을 가리키는 정당한 표현이 있으므로 숫자를 싸잡아 훑지 않는다.
        """
        from pathlib import Path
    
        from searchclinic.corpus import load_evalset
    
        n_docs, n_eval = len(load_catalog()), len(load_evalset())
        n_fail, n_healthy = len(failing_queries()), len(healthy_queries())
        assert n_fail + n_healthy == n_eval, "실패+건강이 평가셋 전체와 다르다"
    
        required = {
            "README.md": [
                f"상품 카탈로그 {n_docs}건",
                f"평가셋 {n_eval}질의",
                f"건강 {n_healthy} + 실패 {n_fail}",
            ],
            "docs/ARCHITECTURE.md": [
                f"상품 카탈로그 {n_docs}건",
                f"문서 {n_docs}건, 질의 {n_eval}건(건강 {n_healthy} + 실패 {n_fail})",
            ],
            "docs/EVALUATION.md": [f"코퍼스 {n_docs}건, 평가셋 {n_eval}건"],
        }
    
        root = Path(__file__).resolve().parent.parent
        stale = [
            f"{rel}: '{phrase}' 없음"
            for rel, phrases in required.items()
            for phrase in phrases
            if phrase not in (root / rel).read_text(encoding="utf-8")
        ]
>       assert not stale, "문서의 규모 선언이 실제와 어긋남: " + "; ".join(stale)
E       AssertionError: 문서의 규모 선언이 실제와 어긋남: README.md: '상품 카탈로그 72건' 없음; README.md: '평가셋 36질의' 없음; README.md: '건강 20 + 실패 16' 없음
E       assert not ["README.md: '상품 카탈로그 72건' 없음", "README.md: '평가셋 36질의' 없음", "README.md: '건강 20 + 실패 16' 없음"]

tests/test_corpus_contract.py:182: AssertionError
=========================== short test summary info ============================
FAILED tests/test_corpus_contract.py::test_documented_scale_matches_reality
1 failed in 0.09s
