/* Verify the static v4 projection against every saved slot; never calls a model. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),source=path.join(root,'src/searchclinic/web/generation-v4.json');
 const data=JSON.parse(fs.readFileSync(source,'utf8'));
 assert.equal(data.mode,'static_actual_response_replay');assert.equal(data.pairs.length,24);
 const out=process.env.QUERYSCOPE_BROWSER_OUTPUT||path.join(root,'docs/verification/queryscope-v4/live-browser-v1');
 fs.mkdirSync(out,{recursive:false});
 const port=process.env.QUERYSCOPE_BROWSER_PORT||'8784',base=`http://127.0.0.1:${port}`;
 const server=cp.spawn(process.env.QUERYSCOPE_PYTHON||'python',['-m','http.server',port,'--bind','127.0.0.1','--directory',path.join(root,'src/searchclinic/web')],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<100;i++){try{if((await fetch(base+'/generation-v4.html')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote']});
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],external=[];
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!request.url().startsWith(base+'/'))external.push(request.url());});
  await page.goto(base+'/generation-v4.html');await page.waitForFunction(()=>!document.querySelector('#v4-content').hidden);
  assert.match(await page.locator('#v4-status').textContent(),/직접비교24슬롯/);
  assert((await page.locator('#v4-citations').textContent()).includes(`인용 ${data.citation_summary.quotes_checked}개`));
  assert((await page.locator('#v4-citations').textContent()).includes(`(${data.citation_summary.responses_with_untraceable_quotes}응답)`));
  const metrics=['rows','supported','abstain','invalid','api_errors','provenance_errors','gate_measured','gate_accepted','gate_rejected','abstention_contract_pass','wrong_patch_on_abstain_required'];
  for(let i=0;i<metrics.length;i++){
   const actual=await page.locator('#v4-summary tr').nth(i).locator('td').allTextContents(),expected=[];
   for(const group of ['paired_v3','additional_development'])for(const condition of ['no_hint','hint'])expected.push(String(data.groups[group][condition][metrics[i]]));
   assert.deepEqual(actual,expected);
  }
  let checked=0;
  for(const group of ['paired_v3','additional_development']){
   await page.selectOption('#v4-group',group);assert.equal(await page.locator('#v4-case option').count(),12);
   for(const pair of data.pairs.filter(item=>item.comparison_group===group)){
    await page.selectOption('#v4-case',pair.id);
    for(const [condition,id] of [['no_hint','v4-no-hint'],['hint','v4-hint']]){
     const row=pair.conditions[condition],text=await page.locator('#'+id).textContent();
     assert(text.includes(row.context.problem));assert(text.includes(row.generation_status));
     if(row.answer?.summary)assert(text.includes(row.answer.summary));else assert(text.includes('생성 응답 없음'));
     if(row.error)assert(text.includes(row.error));
     if(row.response_id)assert(text.includes(row.response_id));
     for(const citation of row.citation_checks)assert(text.includes(citation.quote));
     const effect=row.assessment?.patch_effect;
     if(effect?.status==='measured'){
      assert(text.includes(`격리 게이트: ${effect.gate.accepted?'채택':'기각'}`));
      assert(text.includes(`nDCG ${effect.gate.target_before.ndcg} → ${effect.gate.target_after.ndcg}`));
      const effectJson=await page.locator('#'+id+' details').filter({hasText:'격리 적용과 전수 회귀 원결과'}).locator('pre').textContent();
      assert.deepEqual(JSON.parse(effectJson),effect);
     }
     assert(text.includes(group==='paired_v3'?'동일 사례의 기존 v3':'기존 v3 직접비교 응답 없음'));checked++;
    }
   }
  }
  assert.equal(checked,48);await page.selectOption('#v4-group','all');assert.equal(await page.locator('#v4-case option').count(),24);
  await page.selectOption('#v4-case','T15');
  for(const width of [1440,320,390,650]){
   await page.setViewportSize({width,height:1050});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
   if([1440,320].includes(width))await page.screenshot({path:path.join(out,`generation-v4-${width}.png`),fullPage:true});
  }
  for(const filename of ['index.html','generation-v3.html','review-v4.html','evaluation-v3.html']){
   await page.goto(base+'/'+filename);assert(await page.locator('a[href="generation-v4.html"]').count());
  }
  await page.route('**/generation-v4.json',route=>route.fulfill({status:503,body:'unavailable'}));await page.goto(base+'/generation-v4.html');
  await page.waitForFunction(()=>document.querySelector('#v4-status').textContent.includes('자료 로딩 오류'));assert(await page.locator('#v4-content').isHidden());
  await page.unroute('**/generation-v4.json');await page.route('**/generation-v4.json',route=>route.fulfill({status:200,contentType:'application/json',body:'{}'}));await page.reload();
  await page.waitForFunction(()=>document.querySelector('#v4-status').textContent.includes('자료 로딩 오류'));assert(await page.locator('#v4-content').isHidden());
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const result={passed:true,source_sha256:data.source_sha256,slots_checked:checked,viewports:[1440,320,390,650],new_model_calls:0,checks:['all48 input/answer/citation/response IDs match saved projection','all summary cells traced','paired24/additional24 separate','gate and both regression scopes preserved','old24 response distinction','navigation links','no overflow','503 and invalid data visibly fail closed','zero external requests','no JavaScript errors']};
  fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
