'use strict';
const get=id=>document.getElementById(id);
const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
const labels={spelling_variant:'표기 변형',cross_script:'영한 혼용',synonym_gap:'유의어',garbage_split:'잘못된 분해',compound_locked:'복합어'};
const score=x=>`${x.hits}/${x.eligible}`;
const tableRow=(id,cells)=>{const tr=node('tr','');cells.forEach(c=>tr.append(node('td',c)));get(id).append(tr);};
(async()=>{
 try{
  const response=await fetch('evaluation-v2.json');if(!response.ok)throw Error('v2 평가 자료를 불러오지 못했습니다. 새로고침하거나 저장소의 원자료를 확인해 주세요.');
  const data=await response.json(), summary=data.new_retrieval.summary;
  get('retrieval-summary').textContent=`무힌트 hit@3 ${score(summary.no_hint.legacy)} → ${score(summary.no_hint.observed)} · 힌트 ${score(summary.hint.legacy)} → ${score(summary.hint.observed)}`;
  for(const [family,s] of Object.entries(data.new_retrieval.per_family))tableRow('family-rows',[labels[family],`${score(s.no_hint.legacy)} → ${score(s.no_hint.observed)}`,`${score(s.hint.legacy)} → ${score(s.hint.observed)}`]);
  data.new_retrieval.rows.forEach((r,i)=>{const o=node('option',`${r.case_id} · ${r.query}`);o.value=String(i);get('case-v2').append(o);});
  const show=()=>{
   const row=data.new_retrieval.rows[Number(get('case-v2').value)];
   get('case-note').textContent=row.family_hypothesis?`작성한 계열 가설: ${labels[row.family_hypothesis]||row.family_hypothesis}. 실제 진단의 정답으로 확정하지 않았습니다.`:'정상·불명·근거 부족·범위 밖 사례는 계열 hit@3 채점에서 제외합니다.';
   for(const [condition,id] of [['no_hint','no-hint'],['hint','hint']]){
    const div=get(id),before=row.conditions[condition].legacy,after=row.conditions[condition].observed,c=after.context;
    div.replaceChildren(node('p',`검색어: ${c.query}`),node('p',`관찰: ${c.problem}`),node('p',`분석 토큰: ${c.analysis.tokens.map(t=>t.token).join(' · ')||'없음'}`),node('p',`기존 문서: ${before.retrieved_ids.join(', ')||'없음'}`),node('p',`보완 문서: ${after.retrieved_ids.join(', ')||'없음'}`));
    for(const d of c.documents){const detail=node('details','');detail.append(node('summary',`${d.id} · ${d.title}`),node('blockquote',d.body),node('p',`출처: ${d.source} / 원문 위치 ${d.body_start}–${d.body_end}. 의미적 지지는 사람 검토 필요.`));div.append(detail);}
    if(!c.documents.length)div.append(node('p','제공한 운영 근거 없음 · 새 모델의 보류 여부는 미실행'));
    const trace=node('details','');trace.append(node('summary','검색에 사용한 관측 신호 확인'),node('pre',JSON.stringify(c.retrieval.signals,null,2)));div.append(trace);
   }
  };
  get('case-v2').addEventListener('change',show);show();
  const dev=data.development_repairs.combined.v1_development_24.summary;
  get('development-summary').textContent=`개발 20질의 평균 nDCG@10 ${dev.mean_ndcg_before} → ${dev.mean_ndcg_after}. 측정 지표 하락 ${dev.decreases.length}건.`;
  for(const r of data.repairs)tableRow('repair-rows',[r.query,r.patch,`${r.before} → ${r.after}`,r.accepted?'채택':'기각']);
  const transfer=data.new_catalog_ranking.summary;
  get('transfer-summary').textContent=`새 18질의 평균 nDCG@10 ${transfer.mean_ndcg_before} → ${transfer.mean_ndcg_after} · 개선 ${transfer.improved}개`;
  for(const r of data.new_catalog_ranking.rows)tableRow('transfer-rows',[r.query,r.before.ndcg??'평가 제외',r.after.ndcg??'평가 제외']);
  get('v2-status').textContent='저장한 오프라인 결과 · 실제 LLM 생성 없음 · 추가 유료 호출 0회';
 }catch(error){get('v2-status').textContent=error.message;}
})();
