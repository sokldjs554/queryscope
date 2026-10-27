'use strict';
const el=id=>document.getElementById(id);
const make=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
(async()=>{
 try{
  const response=await fetch('evaluation.json');if(!response.ok)throw Error('평가 자료를 불러오지 못했습니다.');
  const data=await response.json();const s=data.new_queries.summary;
  el('rank-summary').textContent=`정답 있는 ${s.ranked_n}개 평균 nDCG@10: ${s.mean_ndcg_before} → ${s.mean_ndcg_after}. 개선 ${s.improved_ndcg}개, 측정 지표 하락 ${s.degraded_metrics.length}건.`;
  for(const r of data.new_queries.rows){const tr=make('tr','');const b=r.before.ndcg,a=r.after.ndcg;for(const v of [r.query,b??'평가 제외',a??'평가 제외',a===null?'자료 부족':a>b?'개선':a<b?'하락':'같음'])tr.append(make('td',v));el('rank-rows').append(tr);}
  const h=data.new_hint_ablation.summary;
  el('hint-summary').textContent=`계열 근거 hit@3: 힌트 ${h.hint.hits}/${h.hint.eligible}, 무힌트 ${h.no_hint.hits}/${h.no_hint.eligible}. 동일 질의·분석기·문서 한도, 관찰 문장만 변경했습니다.`;
  const pairs=data.new_hint_ablation.rows;
  pairs.forEach((p,i)=>{const o=make('option',`${p.case_id} · ${p.conditions.hint.context.query}`);o.value=String(i);el('pair').append(o);});
  const render=()=>{const p=pairs[Number(el('pair').value)];for(const [cond,prefix] of [['hint','hint'],['no_hint','nohint']]){const c=p.conditions[cond];el(prefix+'-input').textContent=c.context.query+'\n'+c.context.problem;el(prefix+'-docs').textContent='검색 근거: '+(c.retrieved_ids.join(', ')||'없음')+' / 계열 관련 근거: '+(c.family_hit_at_3===null?'채점 제외':c.family_hit_at_3?'있음':'없음');}};
  el('pair').addEventListener('change',render);render();el('eval-status').textContent='저장된 새 오프라인 실험 · LLM 새 생성 없음 · 추가 유료 호출 0회';
 }catch(error){el('eval-status').textContent=error.message;}
})();
