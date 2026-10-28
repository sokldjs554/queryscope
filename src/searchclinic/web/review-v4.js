'use strict';
const get = id => document.getElementById(id);
const node = (tag, text) => {const n=document.createElement(tag);n.textContent=text;return n;};
const labels={supported:'검사 통과',abstain:'보류',invalid:'검증 차단'};
const reasons={canonical_not_in_index:'연결하려는 표준형이 실제 색인에 없습니다.',compound_whole_not_in_index:'분해할 전체 단어가 현재 색인 토큰에 없습니다.',patch_target_unrelated_to_query:'수정 대상이 입력 질의와 연결되지 않습니다.',citation_source_or_text:'인용 출처 또는 원문을 확인하지 못했습니다.',status_or_support:'응답 상태와 근거 조건이 맞지 않습니다.'};
(async()=>{
 try {
  const response=await fetch('review-v4.json');
  if(!response.ok)throw Error('후속 검증 자료를 불러오지 못했습니다. 검증 기록 링크를 확인해 주세요.');
  const data=await response.json();
  for(const [title,key] of [['인용·형식·실행 조건 통과','supported'],['보류','abstain'],['검증 차단','invalid']]){
   const tr=node('tr','');[title,data.summary.primary_status_counts[key],data.summary.runtime_status_counts[key]].forEach(v=>tr.append(node('td',String(v))));get('review-summary').append(tr);
  }
  get('review-effect').textContent=`실행 전 추가 차단 ${data.summary.newly_blocked}응답 · 격리 엔진 검사 ${data.summary.gate_measured}후보 · 채택 ${data.summary.accepted_responses}응답(서로 다른 ${data.accepted_unique_queries}질의) · 효과 없음으로 기각 ${data.summary.rejected_responses}응답`;
  const ids=[...new Set(data.rows.map(r=>r.case_id))];
  for(const id of ids){const row=data.rows.find(r=>r.case_id===id);const option=node('option',`${id} · ${row.query}`);option.value=id;get('review-case').append(option);}
  const show=()=>{
   for(const [condition,id] of [['no_hint','review-no-hint'],['hint','review-hint']]){
    const row=data.rows.find(r=>r.case_id===get('review-case').value&&r.condition===condition),target=get(id);
    target.replaceChildren(node('p',`관찰 입력: ${row.context.problem}`),node('p',`기존 일차 판정: ${labels[row.primary_status]} → 후속 검사: ${labels[row.runtime_status]}`),node('p',row.raw_answer.summary));
    if(row.runtime_validation_error)target.append(node('p',`차단 이유: ${reasons[row.runtime_validation_error]||row.runtime_validation_error}`));
    target.append(node('p',`원래 수정 후보: ${row.raw_answer.patches.length?row.raw_answer.patches.map(p=>`${p.kind}: ${p.terms.join(' → ')}`).join(' / '):'없음'}`));
    const effect=row.runtime_effect;
    if(effect.status==='measured')target.append(node('p',`격리 엔진: ${effect.gate.accepted?'채택':'기각'} · nDCG ${effect.gate.target_before.ndcg} → ${effect.gate.target_after.ndcg}`));
    else target.append(node('p','후속 수정 적용: 실행하지 않음'));
    const old=node('details','');old.append(node('summary','원응답과 당시 입력 확인'),node('pre',JSON.stringify({response_id:row.response_id,answer:row.raw_answer,context:row.context},null,2)));target.append(old);
    const prepared=data.prepared.find(r=>r.case_id===row.case_id&&r.condition===condition);
    const next=node('details','');next.append(node('summary','새로 준비한 근거와 상품 후보'),node('p','이 입력에 대한 모델 응답은 미생성입니다.'),node('p',`운영 문서: ${prepared.prior_document_ids.join(', ')} → ${prepared.runtime_document_ids.join(', ')}`),node('pre',JSON.stringify({catalog_candidates:prepared.context.observations.catalog_candidates||[],citation_policy:prepared.context.runtime_contract,documents:prepared.context.documents},null,2)));target.append(next,node('p','의미적 타당성: 독립적인 사람 검토 대기'));
   }
  };
  get('review-case').addEventListener('change',show);show();
  const r=data.retrieval_summary;
  get('review-retrieval').textContent=`v3 개발 자료의 계열 근거 검색: 무힌트 ${r.no_hint.prior_hits}/${r.no_hint.eligible} → ${r.no_hint.runtime_hits}/${r.no_hint.eligible}, 힌트 ${r.hint.prior_hits}/${r.hint.eligible} → ${r.hint.runtime_hits}/${r.hint.eligible}. 과거 실패 분석 후 같은 자료로 확인한 사후 결과입니다.`;
  get('review-status').textContent='저장 응답 24건의 후속 검사 · 추가 모델 호출 0회 · 원래 일차 판정 보존 · 독립 인간 의미 평가 미완료';
 } catch(error){get('review-status').textContent=error.message;}
})();
