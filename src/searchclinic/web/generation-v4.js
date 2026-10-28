'use strict';
const get=id=>document.getElementById(id);
const node=(tag,text='')=>{const element=document.createElement(tag);element.textContent=text;return element;};
const labels={supported:'인용·형식·실행 조건 통과',abstain:'보류',invalid:'검증 차단'};
const quoteLabels={verified:'원문 추적 통과',unknown_evidence_source:'허용된 운영 지식 출처가 아님',text_mismatch:'인용 문구 불일치'};
const metrics=[['평가 슬롯','rows'],['검사 통과','supported'],['보류','abstain'],['검증 차단','invalid'],['API 오류','api_errors'],['응답 출처 검증 오류','provenance_errors'],['격리 게이트 실행','gate_measured'],['격리 게이트 채택','gate_accepted'],['격리 게이트 기각','gate_rejected'],['보류+무패치 계약 통과','abstention_contract_pass'],['보류 필요 사례의 패치 제안','wrong_patch_on_abstain_required']];
const money=value=>value===null||value===undefined?'미확인':`$${value}`;
function effectText(effect){
 if(!effect||effect.status!=='measured')return '격리 적용: 실행하지 않음 (보류·차단·후보 없음 또는 평가 미실행)';
 const gate=effect.gate;
 return `격리 게이트: ${gate.accepted?'채택':'기각'} · nDCG ${gate.target_before?.ndcg??'미기록'} → ${gate.target_after?.ndcg??'미기록'} · ${gate.reason||''}`;
}
function renderRow(row,target){
 const answer=row.answer,assessment=row.assessment;
 target.replaceChildren(node('p',`관찰 입력: ${row.context.problem}`),node('p',`수신 상태: ${row.generation_status} · 응답 ID: ${row.response_id||'없음'}`),node('p',`응답 비용 추정: ${money(row.estimated_usd)}`));
 if(row.error)target.append(node('p',`오류: ${row.error}`));
 if(!answer)target.append(node('p','생성 응답 없음. API 오류를 보류·검증 차단으로 바꾸어 집계하지 않습니다.'));
 else{
  target.append(node('p',`원응답: ${answer.status||'미기록'} · 계열: ${answer.family||'미기록'}`),node('p',answer.summary||'요약 없음'));
  target.append(node('p',`새 검사: ${assessment?labels[assessment.validated_status]||assessment.validated_status:'실행하지 않음'}`));
  if(assessment?.validation_error)target.append(node('p',`차단 이유: ${assessment.validation_error}`));
  if(!row.citation_checks.length)target.append(node('p','인용 제시 없음'));
  for(const quote of row.citation_checks){
   const details=node('details');details.append(node('summary',`${quote.doc_id} · ${quoteLabels[quote.status]||quote.status}`),node('blockquote',quote.quote));
   const source=row.context.documents.find(doc=>doc.id===quote.doc_id);
   if(source)details.append(node('p',`제공 원문: ${source.title}`),node('blockquote',source.body));
   else details.append(node('p','이 ID는 제공된 운영 지식 documents에 없습니다. 상품 관측 ID는 운영 지식 인용 출처가 아닙니다.'));
   target.append(details);
  }
  target.append(node('p',`원응답 패치: ${(answer.patches||[]).length?answer.patches.map(patch=>`${patch.kind}: ${(patch.terms||[]).join(' → ')}`).join(' / '):'없음'}`));
 }
 const effect=assessment?.patch_effect;
 target.append(node('p',effectText(effect)));
 if(effect?.status==='measured'){
  for(const [key,label] of [['development_16','개발16질의'],['original_36','원래36질의']]){
   const comparison=effect[key];
   target.append(node('p',comparison?`${label} 회귀: ${comparison.summary.decreases.length}건 · 평균 nDCG ${comparison.summary.mean_ndcg_before} → ${comparison.summary.mean_ndcg_after}`:`${label} 회귀: 미기록`));
  }
  const details=node('details');details.append(node('summary','격리 적용과 전수 회귀 원결과'),node('pre',JSON.stringify(effect,null,2)));target.append(details);
 }
 const candidates=row.context.observations?.catalog_candidates||[];
 if(candidates.length){const details=node('details');details.append(node('summary','설명에서 찾은 상품 후보 · 의미 동등성 미검증'),node('pre',JSON.stringify(candidates,null,2)));target.append(details);}
 if(row.previous){
  const previous=row.previous,details=node('details');
  details.append(node('summary','동일 사례의 기존 v3 원응답 · 일차 판정'),node('p',`기존 판정: ${labels[previous.assessment?.validated_status]||'미기록'}`),node('p',effectText(previous.assessment?.patch_effect)),node('p',previous.answer?.summary||'응답 없음'),node('pre',JSON.stringify(previous,null,2)));target.append(details);
 }else target.append(node('p','추가 개발 사례: 기존 v3 직접비교 응답 없음'));
 const details=node('details');details.append(node('summary','전송 입력 · 원응답 · HTTP 수신 기록'),node('pre',JSON.stringify({context:row.context,answer:row.answer,http_response:row.http_response,context_sha256:row.context_sha256,payload_sha256:row.payload_sha256},null,2)));target.append(details,node('p','의미적 지지: 독립적인 사람 검토 필요'));
}
(async()=>{
 try{
  const response=await fetch('generation-v4.json');
  if(!response.ok)throw Error('저장한 실제 평가 자료를 불러오지 못했습니다. 신규 원자료와 내보내기 파일을 확인해 주세요.');
  const data=await response.json();
  if(data.mode!=='static_actual_response_replay'||data.pairs?.length!==24||!data.complete||data.new_api_calls!==0)throw Error('평가 자료의 형식 또는 48슬롯 완료 상태를 확인하지 못했습니다.');
  if(data.pairs.some(pair=>!pair.conditions?.no_hint||!pair.conditions?.hint))throw Error('사례별 힌트 조건 자료가 누락됐습니다.');
  const cost=data.cost;
  get('v4-cost').textContent=`${data.model} · 실제 호출 ${data.attempts}회 · 출처 확인 응답 ${data.responses}건 · API 오류 ${data.api_errors}건 · 응답 출처 검증 오류 ${data.provenance_errors}건`;
  get('v4-cost-scope').textContent=`수신 HTTP ${cost.captured_http_responses}건 중 사용량 비용 확인 ${cost.responses_with_usage_estimate}건 · ${cost.estimate_complete?'전체 토큰 기준 추정':'확인된 범위의 토큰 추정 합계'} ${money(cost.known_estimate_usd)} · ${cost.estimate_complete?'추정 범위 완전':'누락 범위가 있어 실제 총비용은 확정하지 않음'} · 호출 예산 예약 합계 ${money(cost.reserved_usd)} (실제 청구액 아님)`;
  const citations=data.citation_summary;
  get('v4-citations').textContent=`원응답의 인용 ${citations.quotes_checked}개를 모두 따로 대조: 원문 추적 ${citations.verified_quotes}개, 불일치·허용 출처 아님 ${citations.untraceable_quotes}개 (${citations.responses_with_untraceable_quotes}응답). 최초 차단 사유가 인용 검사인 응답은 ${citations.first_citation_blocked_responses}개입니다. 스키마 등 앞선 검사에서 차단된 응답의 인용도 별도 대조하며, 원문 추적은 의미적 지지를 보장하지 않습니다.`;
  for(const [label,key] of metrics){
   const tr=node('tr');tr.append(node('th',label));
   for(const group of ['paired_v3','additional_development'])for(const condition of ['no_hint','hint'])tr.append(node('td',String(data.groups[group][condition][key])));
   get('v4-summary').append(tr);
  }
  for(const [label,key] of metrics){
   const tr=node('tr');tr.append(node('th',label),node('td',String(data.previous_summary.all[key])),node('td',String(data.groups.paired_v3.all[key])));get('v4-comparison').append(tr);
  }
  const show=()=>{
   const pair=data.pairs.find(item=>item.id===get('v4-case').value);if(!pair)return;
   get('v4-note').textContent=`${pair.comparison_group==='paired_v3'?'직접비교24':'추가 개발24'} · ${pair.category} · 작성 계열 가설: ${pair.family_hypothesis||'없음'} · 사람 의미 검토 대기`;
   renderRow(pair.conditions.no_hint,get('v4-no-hint'));renderRow(pair.conditions.hint,get('v4-hint'));
  };
  const filter=()=>{
   const group=get('v4-group').value;get('v4-case').replaceChildren();
   for(const pair of data.pairs.filter(item=>group==='all'||item.comparison_group===group)){
    const option=node('option',`${pair.id} · ${pair.query}`);option.value=pair.id;get('v4-case').append(option);
   }show();
  };
  get('v4-group').addEventListener('change',filter);get('v4-case').addEventListener('change',show);filter();
  get('v4-provenance').textContent=JSON.stringify({source_sha256:data.source_sha256,previous_source_sha256:data.previous_source_sha256,cases_source_sha256:data.cases_source_sha256,prepared_sha256:data.prepared_sha256,canonical_campaign_sha256:data.canonical_campaign_sha256,new_api_calls:data.new_api_calls,semantic_review:data.semantic_review},null,2);
  get('v4-content').hidden=false;
  get('v4-status').textContent=`신규 실제 평가 ${data.attempts}회 · 직접비교24슬롯 + 추가24슬롯의 저장 재생 · 현재 페이지 추가 모델 호출 0회 · 독립 인간 의미 평가 미완료`;
 }catch(error){get('v4-content').hidden=true;get('v4-status').textContent=`자료 로딩 오류: ${error.message}`;}
})();
