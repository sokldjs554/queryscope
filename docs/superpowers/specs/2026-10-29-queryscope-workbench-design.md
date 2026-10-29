# QueryScope 검색 품질 검증 UI

User request: resume the interrupted UI change; remove question-style and conversational headings (했을까, 했다, 했어요, 요), and replace the generic AI-tool presentation.

## Direction
Use the established title **검색 품질 검증**. Replace the long report/hero with a review workspace: compact product header, case list on the left, no-hint/hint results side by side, separate evaluation-summary and experiment-information tabs. Status and patch effect precede long model prose. Original inputs, citations, responses, and full evidence remain available in disclosures.

Alternatives considered: a card dashboard repeats the rejected visual pattern; a report merely restyles the old problem. The review workspace directly exposes the task and both outcomes. This is an implementation decision for the user's retry request, not a new user design approval.

## Boundaries
Keep HTML/CSS/vanilla JavaScript, existing JSON contracts and stable public URLs. Preserve all evaluation JSON, raw responses, approvals, model code, test baselines, API behavior and application documents. No new paid model calls or hosting services. Keep legacy pages functional and normalize their headings; no data rewriting to remove phrases from historical model outputs.

## Acceptance
Default viewport exposes a case and both result headers without scrolling through aggregate statistics. Search/scope/status filters, empty states, previous/next, native case select and keyboard-operable tabs must work. Data errors fail closed. 320/390/650/1024/1440 widths must have no document overflow. Source/effect details and all48 slots must match the existing projection. Whole Python CI and browser checks precede deployment to the existing Render service.
