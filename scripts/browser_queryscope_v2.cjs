/* Real static browser flow; no model endpoint and no mock model answers. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=process.env.QUERYSCOPE_BROWSER_OUTPUT||path.join(root,'docs/verification/queryscope-v2/browser');
 fs.mkdirSync(out,{recursive:false});
 const server=cp.spawn('python',['-m','http.server','8767','--bind','127.0.0.1','--directory',path.join(root,'src/searchclinic/web')],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:8767/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote']});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],paid=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('api.openai.com'))paid.push(r.url());});
  await page.goto('http://127.0.0.1:8767/');await page.locator('#cases button').first().waitFor();
  assert.equal(await page.locator('#cases button').count(),24);
  assert(await page.locator('#mode option[value="live"]').evaluate(e=>e.disabled));
  await page.locator('a[href="evaluation-v2.html"]').click();
  await page.waitForFunction(()=>document.querySelector('#family-rows').children.length===5);
  assert.match(await page.locator('#retrieval-summary').textContent(),/6\/15 → 10\/15/);
  assert.equal(await page.locator('#case-v2 option').count(),24);
  assert.equal(await page.locator('#transfer-rows tr').count(),24);
  assert.equal(await page.locator('#repair-rows tr').count(),3);
  await page.selectOption('#case-v2','8');assert.match(await page.locator('#no-hint').textContent(),/휴대용 배터리/);
  await page.locator('#no-hint details').first().locator('summary').click();
  assert(await page.locator('#no-hint blockquote').first().isVisible());
  for(const width of [1440,320,390,650]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
   if([1440,320].includes(width))await page.screenshot({path:path.join(out,`evaluation-v2-${width}.png`),fullPage:true});
  }
  await page.selectOption('#case-v2','20');assert.match(await page.locator('#no-hint').textContent(),/제공한 운영 근거 없음/);
  await page.selectOption('#case-v2','23');assert.match(await page.locator('#no-hint').textContent(),/비밀번호/);
  await page.locator('a[href="evaluation.html"]').click();await page.waitForFunction(()=>document.querySelector('#rank-rows').children.length===24);
  assert.match(await page.locator('#hint-summary').textContent(),/무힌트 1\/11/);
  await page.goto('http://127.0.0.1:8767/evaluation-v2.html');await page.locator('#family-rows tr').first().waitFor();
  await page.route('**/evaluation-v2.json',r=>r.fulfill({status:503,body:'unavailable'}));await page.reload();
  await page.waitForFunction(()=>document.querySelector('#v2-status').textContent.includes('불러오지 못했습니다'));
  assert.deepEqual(errors,[]);assert.deepEqual(paid,[]);
  const result={passed:true,viewports:[1440,320,390,650],source:'real static saved results',new_model_calls:0,
   checks:['legacy replay 24 and live disabled','v2 navigation','all 24 paired cases','five family rows','three development repairs','new catalog 24 ranking rows','citation source disclosure','insufficient documents and out of scope visible','no horizontal overflow','preserved v1 comparison','failed fetch visible','no JavaScript errors']};
  fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
