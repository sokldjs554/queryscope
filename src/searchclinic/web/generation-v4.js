/* Immutable response review. All model/evidence text is rendered as text, never HTML. */
(() => {
  'use strict';
  const get = id => document.getElementById(id);
  const el = (tag, text = '', className = '') => {
    const item = document.createElement(tag);
    item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  const statuses = {supported: '인용·형식·적용 검사 통과', abstain: '보류', invalid: '검증 차단'};
  const families = {compound_locked: '복합어 색인', synonym_gap: '표현 대응', tokenization: '형태소 분해', unknown: '원인 미확정'};
  const categories = {candidate_failure: '검색 실패 후보', healthy: '정상 검색', unknown: '원인 불명', insufficient: '근거 부족', out_of_scope: '범위 밖 요청'};
  const reasons = {compound_whole_not_in_index: '색인에 없는 복합어 분해 대상', canonical_not_in_index: '색인에 없는 대표어', output_schema: '수정안 형식 오류', citation_source_or_text: '인용 출처 또는 문구 불일치', status_or_support: '응답 상태와 근거의 불일치'};
  const quoteLabels = {verified: '원문 일치', unknown_evidence_source: '출처 불일치', text_mismatch: '문구 불일치'};
  const patchNames = {compound: '복합어 분해', synonym: '동의어 연결', user_word: '사용자 사전', user_dict: '사용자 사전'};
  const metrics = [['평가 응답', 'rows'], ['검사 통과', 'supported'], ['보류', 'abstain'], ['검증 차단', 'invalid'], ['API 오류', 'api_errors'], ['응답 출처 오류', 'provenance_errors'], ['개별 후보 검사', 'gate_measured'], ['수정안 채택', 'gate_accepted'], ['수정안 기각', 'gate_rejected'], ['보류·무패치 계약 통과', 'abstention_contract_pass'], ['보류 필요 사례의 패치 제안', 'wrong_patch_on_abstain_required']];
  const money = value => value == null ? '미확인' : `$${value}`;
  const number = value => typeof value === 'number' ? String(value) : '미기록';
  function verdict(row) {
    if (row.generation_status === 'api_error') return {key: 'blocked', label: 'API 오류', title: 'API 호출 오류'};
    if (row.generation_status === 'provenance_error') return {key: 'blocked', label: '출처 오류', title: '응답 출처 오류'};
    const a = row.assessment;
    if (!a) return {key: 'abstain', label: '미평가', title: '평가 기록 없음'};
    if (a.validated_status === 'invalid') return {key: 'blocked', label: '차단', title: '적용 전 차단'};
    if (a.patch_effect?.status === 'measured') return a.patch_effect.gate.accepted ? {key: 'accepted', label: '채택', title: '수정안 채택'} : {key: 'rejected', label: '기각', title: '수정안 기각'};
    if (a.validated_status === 'abstain') return {key: 'abstain', label: '보류', title: '수정안 보류'};
    return {key: 'accepted', label: '통과', title: '적용 조건 통과'};
  }
  function details(title, value, record) {
    const block = el('details', '', 'record-details');
    if (record) block.dataset.record = record;
    block.append(el('summary', title), el('pre', JSON.stringify(value, null, 2)));
    return block;
  }
  function section(title) {
    const block = el('section', '', 'row-section');
    block.append(el('h4', title));
    return block;
  }
  function renderRow(row, target) {
    target.replaceChildren();
    const v = verdict(row), a = row.assessment, answer = row.answer, effect = a?.patch_effect;
    const outcome = el('div', '', `outcome ${v.key}`);
    outcome.append(el('strong', v.title));
    if (effect?.status === 'measured') {
      outcome.append(el('div', `${number(effect.gate.target_before?.ndcg)} → ${number(effect.gate.target_after?.ndcg)}`, 'effect-metric'));
      outcome.append(el('span', '표적 nDCG · 개별 후보 적용', 'outcome-detail'));
    } else {
      const explanation = a?.validation_error ? reasons[a.validation_error] || a.validation_error : (v.label === '보류' ? '적용 가능한 수정안 없음' : row.error || '수정 효과 검사 미실행');
      outcome.append(el('span', explanation, 'outcome-detail'));
    }
    target.append(outcome);
    if (row.error) target.append(el('p', row.error, 'validation-note blocked'));
    const patchSection = section('수정 후보');
    const patches = answer?.patches || [];
    if (!patches.length) patchSection.append(el('p', '제안 없음', 'validation-note'));
    for (const patch of patches) {
      const line = el('p', '', 'patch-line');
      line.append(el('span', patchNames[patch.kind] || patch.kind, 'patch-kind'));
      const terms = patch.terms || [];
      const value = patch.kind === 'compound' ? `${terms[0] || '빈 대상'} → ${terms.slice(1).map(t => t || '[빈 값]').join(' + ')}` : terms.map(t => t || '[빈 값]').join(' ↔ ');
      line.append(document.createTextNode(value));
      patchSection.append(line);
    }
    if (effect?.status === 'measured') {
      const regression = el('div', '', 'regression-list');
      for (const [key, label] of [['development_16', '개발 16질의'], ['original_36', '기존 36질의']]) {
        const s = effect[key]?.summary;
        regression.append(el('div', s ? `${label} · 지표 하락 ${s.decreases.length}건 · 평균 nDCG ${number(s.mean_ndcg_before)} → ${number(s.mean_ndcg_after)}` : `${label} · 미기록`));
      }
      patchSection.append(regression, details('개별 적용·회귀 검사 원결과', effect, 'effect'));
    } else if (a?.validation_error) patchSection.append(el('p', `검사 코드: ${a.validation_error}`, 'validation-note'));
    target.append(patchSection);
    const observation = section('입력 관찰');
    const facts = el('div', '', 'input-facts');
    facts.append(el('span', `검색 ${row.context.search?.total ?? '미기록'}건`));
    const tokens = row.context.analysis?.tokens || [];
    facts.append(el('span', `토큰 ${tokens.map(t => t.token).join(' · ') || '없음'}`));
    observation.append(facts, el('p', row.context.problem, 'input-problem'));
    target.append(observation);
    const explanation = section('모델 설명');
    if (answer) {
      explanation.append(el('p', `${families[answer.family] || answer.family || '원인 미기록'} · ${statuses[a?.validated_status] || '평가 미실행'}`, 'validation-note'));
      explanation.append(el('p', answer.summary || '설명 없음', 'model-summary'));
    } else explanation.append(el('p', '생성 응답 없음 · 오류와 정상 보류를 별도 집계', 'validation-note'));
    target.append(explanation);
    const citations = section(`인용 근거 · ${row.citation_checks.length}개`);
    if (!row.citation_checks.length) citations.append(el('p', '제시된 인용 없음', 'validation-note'));
    const list = el('div', '', 'evidence-list');
    row.citation_checks.forEach((quote, index) => {
      const block = el('details', '', 'evidence-item');
      const head = el('summary');
      head.append(el('span', quote.doc_id, 'evidence-code'), el('span', quoteLabels[quote.status] || quote.status, `quote-status ${quote.status === 'verified' ? 'accepted' : 'blocked'}`));
      block.append(head, el('blockquote', quote.quote));
      const source = row.context.documents.find(doc => doc.id === quote.doc_id);
      if (source) {
        const doc = el('details', '', 'source-doc');
        doc.append(el('summary', source.title), el('p', source.body));
        block.append(doc);
      } else block.append(el('p', '허용된 운영 지식 문서에 없는 출처', 'validation-note blocked'));
      if (index === 0) block.open = true;
      list.append(block);
    });
    citations.append(list, el('p', '원문 일치와 의미적 지지는 별도 검토 대상', 'validation-note'));
    target.append(citations);
    if (row.previous) {
      const previous = details('기존 v3 응답·최초 판정', row.previous, 'previous');
      previous.insertBefore(el('p', `기존 판정: ${statuses[row.previous.assessment?.validated_status] || '미평가'}`, 'previous-label'), previous.lastChild);
      target.append(previous);
    } else target.append(el('p', '추가 개발 사례 · 기존 직접 비교 응답 없음', 'validation-note'));
    target.append(details('입력·응답·사용량·식별자 원본', row, 'row'));
  }
  function fillTables(data) {
    for (const [label, key] of metrics) {
      const tr = el('tr'), head = el('th', label); head.scope = 'row'; tr.append(head);
      for (const group of ['paired_v3', 'additional_development']) for (const condition of ['no_hint', 'hint']) tr.append(el('td', String(data.groups[group][condition][key])));
      get('v4-summary').append(tr);
      const comparison = el('tr'), compareHead = el('th', label); compareHead.scope = 'row';
      comparison.append(compareHead, el('td', String(data.previous_summary.all[key])), el('td', String(data.groups.paired_v3.all[key])));
      get('v4-comparison').append(comparison);
    }
    for (const [label, key] of [['전체 응답', 'rows'], ['검사 통과', 'supported'], ['보류', 'abstain'], ['검증 차단', 'invalid']]) {
      const stat = el('div', '', 'summary-stat'); stat.append(el('span', label), el('strong', String(data.summary.all[key])));get('summary-totals').append(stat);
    }
    const c = data.citation_summary;
    get('v4-citations').textContent = `원인용 ${c.quotes_checked}개 중 원문 일치 ${c.verified_quotes}개, 불일치·허용되지 않은 출처 ${c.untraceable_quotes}개 (${c.responses_with_untraceable_quotes}응답). 최초 차단 사유가 인용 오류인 응답은 ${c.first_citation_blocked_responses}개입니다. 앞선 형식 검사에서 차단된 응답의 인용도 별도로 대조합니다.`;
    get('v4-cost').textContent = `${data.model} · 실제 호출 ${data.attempts}회 / 응답 ${data.responses}건 / API 오류 ${data.api_errors}건 / 응답 출처 오류 ${data.provenance_errors}건`;
    const cost = data.cost;
    get('v4-cost-scope').textContent = `HTTP 수신 ${cost.captured_http_responses}건 · 비용 사용량 확인 ${cost.responses_with_usage_estimate}건 · ${cost.estimate_complete ? '전체 토큰 기준 추정' : '확인된 사용량의 부분 추정'} ${money(cost.known_estimate_usd)} · 예약 한도 ${money(cost.reserved_usd)}${cost.estimate_complete ? '' : ' · 누락 사용량으로 전체 비용 미확정'}`;
    get('v4-provenance').textContent = JSON.stringify({source_sha256: data.source_sha256, previous_source_sha256: data.previous_source_sha256, cases_source_sha256: data.cases_source_sha256, prepared_sha256: data.prepared_sha256, canonical_campaign_sha256: data.canonical_campaign_sha256, new_api_calls: data.new_api_calls, semantic_review: data.semantic_review}, null, 2);
  }
  async function main() {
    try {
      const response = await fetch('generation-v4.json');
      if (!response.ok) throw new Error(`저장 자료 응답 오류 (${response.status})`);
      const data = await response.json();
      if (data.mode !== 'static_actual_response_replay' || !data.complete || data.new_api_calls !== 0 || data.pairs?.length !== 24 || data.pairs.some(pair => !pair.conditions?.no_hint || !pair.conditions?.hint)) throw new Error('48응답 자료 구조 불일치');
      fillTables(data);
      get('dataset-count').textContent = `${data.pairs.length}사례 / ${data.attempts}응답`;
      const groupNames = {paired_v3: '직접 비교', additional_development: '추가 개발'};
      const tabs = ['cases', 'summary', 'info'];
      const state = {tab: 'cases', group: 'all', outcome: 'all', query: '', selected: 'T01'};
      let visible = [];
      const saveState = () => {
        const params = new URLSearchParams({tab: state.tab, group: state.group, status: state.outcome});
        if (state.selected) params.set('case', state.selected);
        if (state.query) params.set('q', state.query);
        history.replaceState(null, '', '#' + params.toString());
      };
      function selectTab(name, focus = false, save = true) {
        state.tab = tabs.includes(name) ? name : 'cases';
        for (const tab of tabs) {
          const selected = state.tab === tab, button = get('tab-' + tab);
          button.setAttribute('aria-selected', String(selected));button.tabIndex = selected ? 0 : -1;
          get('panel-' + tab).hidden = !selected;
        }
        if (focus) get('tab-' + state.tab).focus();
        if (save) saveState();
      }
      function showSelected(save = true) {
        const pair = visible.find(item => item.id === state.selected);
        const empty = !pair;
        get('no-selection').hidden = !empty;get('selected-case').hidden = empty;
        get('v4-case').disabled = empty;
        if (empty) {
          state.selected = '';
          get('v4-no-hint').replaceChildren();get('v4-hint').replaceChildren();
          if (save) saveState();
          return;
        }
        get('v4-case').value = pair.id;
        get('case-id').textContent = pair.id;get('case-title').textContent = pair.query;
        get('v4-note').textContent = `${groupNames[pair.comparison_group]} · ${categories[pair.category] || pair.category} · 힌트 유무별 개별 후보 검사`;
        renderRow(pair.conditions.no_hint, get('v4-no-hint'));renderRow(pair.conditions.hint, get('v4-hint'));
        const index = visible.indexOf(pair);
        get('case-prev').disabled = index === 0;get('case-next').disabled = index === visible.length - 1;
        for (const button of get('case-list').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.case === pair.id));
        if (save) saveState();
      }
      function filter(save = true) {
        const query = state.query.trim().toLocaleLowerCase();
        visible = data.pairs.filter(pair => (state.group === 'all' || pair.comparison_group === state.group) && (!query || `${pair.id} ${pair.query}`.toLocaleLowerCase().includes(query)) && (state.outcome === 'all' || Object.values(pair.conditions).some(row => state.outcome === 'accepted' ? row.assessment?.patch_effect?.status === 'measured' && row.assessment.patch_effect.gate.accepted : verdict(row).key === state.outcome)));
        get('case-list').replaceChildren();get('v4-case').replaceChildren();
        get('case-count').textContent = `${visible.length} / ${data.pairs.length}`;
        get('case-empty').hidden = visible.length > 0;
        for (const pair of visible) {
          const button = el('button', '', 'case-row');button.type = 'button';button.dataset.case = pair.id;
          const title = el('span', '', 'case-row-title');title.append(el('span', pair.id, 'case-row-code'), el('span', pair.query, 'case-query'));button.append(title);
          const labels = [];
          for (const condition of ['no_hint', 'hint']) {
            const v = verdict(pair.conditions[condition]);button.append(el('span', v.label, `mini-status ${v.key}`));labels.push(v.label);
          }
          button.setAttribute('aria-label', `${pair.id} ${pair.query} · 힌트 없음 ${labels[0]}, 힌트 있음 ${labels[1]}`);
          button.addEventListener('click', () => {state.selected = pair.id;showSelected();});
          get('case-list').append(button);
          const option = el('option', `${pair.id} · ${pair.query}`);option.value = pair.id;get('v4-case').append(option);
        }
        if (!visible.some(pair => pair.id === state.selected)) state.selected = visible[0]?.id || '';
        showSelected(save);
      }
      function restore() {
        const params = new URLSearchParams(location.hash.slice(1));
        state.tab = tabs.includes(params.get('tab')) ? params.get('tab') : 'cases';
        state.group = ['all', 'paired_v3', 'additional_development'].includes(params.get('group')) ? params.get('group') : 'all';
        state.outcome = ['all', 'accepted', 'blocked', 'rejected', 'abstain'].includes(params.get('status')) ? params.get('status') : 'all';
        state.query = (params.get('q') || '').slice(0, 100);state.selected = params.get('case') || 'T01';
        get('v4-group').value = state.group;get('case-outcome').value = state.outcome;get('case-search').value = state.query;
        selectTab(state.tab, false, false);filter(false);saveState();
      }
      for (const tab of tabs) {
        get('tab-' + tab).addEventListener('click', () => selectTab(tab));
        get('tab-' + tab).addEventListener('keydown', event => {
          let next;
          if (event.key === 'ArrowRight') next = tabs[(tabs.indexOf(tab) + 1) % tabs.length];
          if (event.key === 'ArrowLeft') next = tabs[(tabs.indexOf(tab) + tabs.length - 1) % tabs.length];
          if (event.key === 'Home') next = tabs[0];
          if (event.key === 'End') next = tabs[tabs.length - 1];
          if (next) {event.preventDefault();selectTab(next, true);}
        });
      }
      get('v4-group').addEventListener('change', () => {state.group = get('v4-group').value;filter();});
      get('case-outcome').addEventListener('change', () => {state.outcome = get('case-outcome').value;filter();});
      get('case-search').addEventListener('input', () => {state.query = get('case-search').value;filter();});
      get('v4-case').addEventListener('change', () => {state.selected = get('v4-case').value;showSelected();});
      get('reset-filters').addEventListener('click', () => {state.group = 'all';state.outcome = 'all';state.query = '';get('v4-group').value = 'all';get('case-outcome').value = 'all';get('case-search').value = '';filter();});
      for (const [id, delta] of [['case-prev', -1], ['case-next', 1]]) get(id).addEventListener('click', () => {const item = visible[visible.findIndex(pair => pair.id === state.selected) + delta];if (item) {state.selected = item.id;showSelected();}});
      window.addEventListener('hashchange', restore);
      restore();
      get('v4-content').hidden = false;
      get('v4-status').dataset.ready = 'true';
      get('v4-status').textContent = `${data.attempts}응답 · 직접비교24슬롯 / 추가24슬롯 · 현재 화면 추가 호출 0회`;
    } catch (error) {
      get('v4-content').hidden = true;
      get('v4-status').dataset.error = 'true';
      get('v4-status').textContent = `자료 로딩 오류: ${error.message}`;
    }
  }
  main();
})();
