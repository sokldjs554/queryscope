# QueryScope v3 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation and one fresh whole-branch code review.

Goal: follow up currentmain e8f967c, fix the known normal-morphology false gap, preserve v2 exact reproduction, validate new controlled positives and healthy negatives before scoring, keep actual LLM calls unapproved.
Architecture: retain observed_v2 strategy; observed becomes v3 token-set comparison with exact-output bounded excerpt cache. Shared campaign supports explicit v2/v3 bundles. Prior frozen artifacts untouched.
Spec: user request in current turn; docs/verification/queryscope-v3/PROTOCOL.md frozen2e7ec2c.
Constraints: additional paid calls0; old v1/v2 nowdevelopment; newcase scores cannot tune algorithm; independent semantic review pending; preserve24 historicalactualresponses and both prepared campaigns separately.
Review focus: normal suffix token coverage vs true atomic compound gap; empty tokenizer output; baseline exact reproduction; per-checkout canonical budget for both campaigns; no data labels in model input; exclusions/n=0 disclosed.

- [ ] Freeze v3 before measurements; assess currentmain/raw/CI/demo.
- [ ] RED tests for normal surface morphology, true compound recall and repeat excerpt exactness. Implement token coverage and bounded cache; preserve observed_v2.
- [ ] Make bundle selection explicit in preparation/approval/execution without altering v2 prepared payloads. RED->GREEN for correct frozen config and cross-suite tampering.
- [ ] v3 runner preconditions abort before scoring; olddevelopment/newcontrolled results separate; all24paired contexts, all families including n=0, null model outputs. Commit code before first v3 scoring.
- [ ] Local tests/baseline/browser/operations; document new results and limits, update application originals without inventing contribution.
- [ ] Fresh review, fix blockers, full suite, push/CI/Render, public access attempt and scoped final report.
