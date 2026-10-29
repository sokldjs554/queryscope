# QueryScope Review Workspace Implementation Plan

> Execute inline using superpowers:executing-plans. Track each check below.

**Goal:** Replace report-style entry with a concise case review workspace and nominal headings.
**Architecture:** Preserve the immutable generation-v4.json projection, use the existing generation-v4 URL, and add one isolated CSS file. Keep old page contracts, with copy/style adjustments only.
**Tech Stack:** HTML, CSS, vanilla JavaScript, Python Playwright, pytest, GitHub Actions, existing Render static site.
**Spec:** ../specs/2026-10-29-queryscope-workbench-design.md

## Global Constraints
No new paid calls. No JSON/raw-result/approval/provider/application changes. No question-style/conversational headings. Escape all untrusted rendered content using textContent. No external script or font requests.

## Review Focus
Empty filter results must not retain the previous case; invalid hashes fall back safely; schema/API errors remain distinguishable; hidden panels cannot receive focus; mobile controls cannot overflow.

## Tasks
- [x] 1. RED: add heading/layout tests and capture current browser baseline.
- [x] 2. Implement case-first layout, case filters, clear result/effect/evidence hierarchy, accessible summary/info tabs; retain detail records.
- [x] 3. Normalize all legacy headings and compact shared styling without changing legacy IDs or data.
- [ ] 4. GREEN: check all48 slots, filters, tabs, malformed loading, 5 viewport widths, screenshots, preserved data hashes. Run project pytest; use remote CI for unavailable local dependencies.
- [ ] 5. Inspect diff, run remote full suite, deploy existing Render site, verify public files/UI, record exact scope.

## Execution ledger
Source: cb2ba18d snapshot; main base ee84b51a. Read-only Actions archive transported the tracked source because direct container GitHub DNS is unavailable. Isolated local Git workspace and remote ui/search-quality-workbench branch; main remains unchanged until verification.

Ruling: local network navigation and full Python dependency setup unavailable; actual data DOM checks run offline without changing browser security. Remote CI remains mandatory before merge.
