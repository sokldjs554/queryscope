/* Actual saved API answers only. No mocked model answers and no API calls. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=process.env.QUERYSCOPE_BROWSER_OUTPUT||path.join(root,'docs/verification/queryscope-v3/browser-actual');
 fs.mkdirSync(out,{recursive:false});
 const server=cp.spawn('python',['-m','http.server','8769','--bind','127.0.0.1','--directory',path.join(root,'src/searchclinic/web')],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:8769/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote']});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],paid=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('api.openai.com'))paid.push(r.url());});
  await page.goto('http://127.0.0.1:8769/');await page.locator('a[href="generation-v3.html"]').first().click();
  await page.waitForFunction(()=>document.querySelector('#actual-case').children.length===12);
  assert.match(await page.locator('#actual-cost').textContent(),/실제 호출 24회.*API 오류 0건.*0.0385605/);
  assert.equal(await page.locator('#actual-summary tr').count(),6);
  assert.match(await page.locator('#actual-no-hint').textContent(),/검증 차단/);
  await page.locator('#actual-no-hint details').first().locator('summary').click();
  assert.match(await page.locator('#actual-no-hint').textContent(),/허용된 운영 문서 출처가 아님/);
  assert(await page.locator('#actual-no-hint blockquote').first().isVisible());
  const data=JSON.parse(fs.readFileSync(path.join(root,'src/searchclinic/web/generation-v3.json'),'utf8'));
  for(let i=0;i<12;i++){
   await page.selectOption('#actual-case',String(i));
   for(const [condition,id] of [['no_hint','actual-no-hint'],['hint','actual-hint']]){
    const text=await page.locator('#'+id).textContent();
    assert(text.includes(data.pairs[i].conditions[condition].answer.summary));
    assert(text.includes(data.pairs[i].conditions[condition].context.problem));
   }
  }
  await page.selectOption('#actual-case','2');assert.match(await page.locator('#actual-no-hint').textContent(),/채택 · nDCG 0 → 1/);
  await page.selectOption('#actual-case','4');assert.match(await page.locator('#actual-no-hint').textContent(),/일차 판정: 보류/);assert.match(await page.locator('#actual-hint').textContent(),/기각 · nDCG 0 → 0/);
  for(const width of [1440,320,390,650]){
   await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
   if([1440,320].includes(width))await page.screenshot({path:path.join(out,`actual-${width}.png`),fullPage:true});
  }
  await page.locator('a[href="evaluation-v3.html"]').click();await page.locator('#family-rows tr').first().waitFor();
  assert.match(await page.locator('#retrieval-summary').textContent(),/7\/8 → 7\/8/);
  await page.locator('a[href="generation-v3.html"]').first().click();await page.locator('#actual-summary tr').first().waitFor();
  await page.route('**/generation-v3.json',r=>r.fulfill({status:503,body:'unavailable'}));await page.reload();
  await page.waitForFunction(()=>document.querySelector('#actual-status').textContent.includes('불러오지 못했습니다'));
  assert.deepEqual(errors,[]);assert.deepEqual(paid,[]);
  const result={passed:true,viewports:[1440,320,390,650],source:'24 actual saved API answers; no model mocks',new_model_calls:0,checks:['root and offline navigation','all 12 paired inputs and answers','blocked product citation disclosure','accepted patch 0 to 1','abstention versus ineffective patch','six summary metrics','source details','no overflow','fetch error visible','no JavaScript errors']};
  fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
