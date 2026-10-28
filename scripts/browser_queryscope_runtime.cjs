/* Verify retrospective results and explicitly ungenerated inputs in the real UI. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=process.env.QUERYSCOPE_BROWSER_OUTPUT||path.join(root,'docs/verification/queryscope-v4/browser');
 fs.mkdirSync(out,{recursive:false});
 const server=cp.spawn(process.env.QUERYSCOPE_PYTHON||'python',['-m','http.server','8773','--bind','127.0.0.1','--directory',path.join(root,'src/searchclinic/web')],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:8773/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote']});
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],paid=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('api.openai.com'))paid.push(r.url());});
  await page.goto('http://127.0.0.1:8773/');await page.locator('a[href="review-v4.html"]').first().click();
  await page.waitForFunction(()=>document.querySelector('#review-case').children.length===12);
  assert.match(await page.locator('#review-status').textContent(),/추가 모델 호출 0회.*원래 일차 판정 보존/);
  assert.equal(await page.locator('#review-summary tr').count(),3);
  assert.deepEqual(await page.locator('#review-summary tr').allTextContents(),['인용·형식·실행 조건 통과76','보류99','검증 차단89']);
  assert.match(await page.locator('#review-effect').textContent(),/추가 차단 1응답.*검사 6후보.*채택 4응답/);
  const data=JSON.parse(fs.readFileSync(path.join(root,'src/searchclinic/web/review-v4.json'),'utf8'));
  for(const id of [...new Set(data.rows.map(r=>r.case_id))]){
   await page.selectOption('#review-case',id);
   for(const [condition,div] of [['no_hint','review-no-hint'],['hint','review-hint']]){
    const row=data.rows.find(r=>r.case_id===id&&r.condition===condition),text=await page.locator('#'+div).textContent();
    assert(text.includes(row.raw_answer.summary));assert(text.includes(row.context.problem));
   }
  }
  await page.selectOption('#review-case','T15');
  assert.match(await page.locator('#review-hint').textContent(),/실제 색인에 없습니다/);
  assert.match(await page.locator('#review-no-hint').textContent(),/기존 일차 판정: 보류 → 후속 검사: 보류/);
  await page.locator('#review-no-hint details').nth(1).locator('summary').click();
  assert.match(await page.locator('#review-no-hint details').nth(1).textContent(),/모델 응답은 미생성.*K007/s);
  for(const width of [1440,320,390,650]){
   await page.setViewportSize({width,height:1050});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
   if([1440,320].includes(width))await page.screenshot({path:path.join(out,`runtime-${width}.png`),fullPage:true});
  }
  await page.selectOption('#review-case','T13');assert.match(await page.locator('#review-hint').textContent(),/채택 · nDCG 0 → 1/);
  await page.selectOption('#review-case','T16');assert.match(await page.locator('#review-hint').textContent(),/기각 · nDCG 0 → 0/);
  await page.locator('a[href="generation-v3.html"]').click();await page.locator('#actual-case option').first().waitFor({state:'attached'});
  assert.match(await page.locator('#actual-status').textContent(),/실제 API 24응답/);
  await page.locator('a[href="review-v4.html"]').first().click();await page.locator('#review-summary tr').first().waitFor();
  await page.route('**/review-v4.json',r=>r.fulfill({status:503,body:'unavailable'}));await page.reload();
  await page.waitForFunction(()=>document.querySelector('#review-status').textContent.includes('불러오지 못했습니다'));
  assert.deepEqual(errors,[]);assert.deepEqual(paid,[]);
  const result={passed:true,viewports:[1440,320,390,650],new_model_calls:0,rows:24,checks:['root and v3 navigation','original versus runtime counts','all24 original inputs and outputs','absent canonical blocked','unchanged abstention','new context explicitly not generated','source disclosures','valid gain retained','ineffective candidate rejected','no overflow','load failure visible','no JavaScript errors']};
  fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
