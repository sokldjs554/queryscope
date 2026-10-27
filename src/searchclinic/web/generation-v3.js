'use strict';
const get=id=>document.getElementById(id);
const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
const labels={supported:'인용·형식 통과',abstain:'보류',invalid:'검증 차단'};
const quoteLabels={verified:'원문 추적 통과',unknown_evidence_source:'허용된 운영 문서 출처가 아님',text_mismatch:'인용 문구가 원문과 다름'};
(async()=>{
 try{
  const response=await fetch('generation-v3.json');if(!response.ok)throw Error('실제 응답 자료를 불러오지 못했습니다. 저장소 원자료를 확인해 주세요.');
  const data=await response.json();
  get('actual-cost').textContent=`${data.model} · 실제 호출 ${data.attempts}회 · 응답 ${data.responses}건 · API 오류 ${data.api_errors}건 · 토큰 기준 추정 $${data.estimated_usd} (청구서 아님)`;
  for(const [label,key,den] of [['인용·형식 통과','supported',''],['보류','abstain',''],['차단','invalid',''],['작성 계열 라벨 일치','literal_family_match','/6'],['보류+무패치+검증 통과','abstention_contract_pass','/6'],['보류 필요 사례에 패치 제안','wrong_patch_on_abstain_required','/6']]){
   const tr=node('tr','');[label,`${data.summary.no_hint[key]}${den}`,`${data.summary.hint[key]}${den}`].forEach(v=>tr.append(node('td',v)));get('actual-summary').append(tr);
  }
  data.pairs.forEach((p,i)=>{const opt=node('option',`${p.id} · ${p.query}`);opt.value=String(i);get('actual-case').append(opt);});
  const show=()=>{
   const pair=data.pairs[Number(get('actual-case').value)];get('actual-note').textContent=`사례: ${pair.category} · 작성 계열 가설: ${pair.family_hypothesis||'없음'} · 사람 의미 검토 대기`;
   for(const [condition,id] of [['no_hint','actual-no-hint'],['hint','actual-hint']]){
    const row=pair.conditions[condition],div=get(id),a=row.assessment,answer=row.answer;
    div.replaceChildren(node('p',`관찰 입력: ${row.context.problem}`),node('p',`실제 분석 토큰: ${row.context.analysis.tokens.map(t=>t.token).join(' · ')}`),node('p',`일차 판정: ${labels[a.validated_status]} · 원응답 status: ${answer.status} · 원인: ${answer.family}`),node('p',answer.summary));
    if(a.validation_error)div.append(node('p',`차단 이유: ${a.validation_error}`));
    for(const q of row.citation_checks){const detail=node('details','');detail.append(node('summary',`${q.doc_id} · ${quoteLabels[q.status]}`),node('blockquote',q.quote));const doc=row.context.documents.find(d=>d.id===q.doc_id);if(doc)detail.append(node('p',`제공 원문: ${doc.title}`),node('blockquote',doc.body));else detail.append(node('p','상품 관측에 등장한 ID여도 제공한 운영 지식 documents의 인용 출처는 아닙니다.'));div.append(detail);}
    if(!answer.evidence.length)div.append(node('p','인용 제시 없음'));
    div.append(node('p',`원응답 패치: ${answer.patches.length?answer.patches.map(p=>`${p.kind}: ${p.terms.join(' → ')}`).join(' / '):'없음'}`));
    const effect=a.patch_effect;
    if(effect.status==='measured')div.append(node('p',`격리 엔진 판정: ${effect.gate.accepted?'채택':'기각'} · nDCG ${effect.gate.target_before.ndcg} → ${effect.gate.target_after.ndcg}`),node('p',effect.gate.reason));
    else div.append(node('p','일차 수정 효과: 실행하지 않음 (보류·차단 또는 후보 없음)'));
    div.append(node('p','의미적 지지: 독립적인 사람 검토 필요'));
    const detail=node('details','');detail.append(node('summary','제공 입력과 응답 식별자'),node('pre',JSON.stringify({response_id:row.response_id,context:row.context},null,2)));div.append(detail);
   }
  };
  get('actual-case').addEventListener('change',show);show();
  get('actual-status').textContent='실제 API 24응답의 저장 재생 · 현재 페이지는 새 모델 호출 없음 · 독립 인간 의미 평가 미완료';
 }catch(error){get('actual-status').textContent=error.message;}
})();
