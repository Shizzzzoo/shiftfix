// Local fixtures only. Run python3 scripts/build-demo-data.py and Vite on port 5174.
// Playwright Chromium exercises the app; no production login credentials are used.
import {createRequire} from 'node:module';import fs from 'node:fs';import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url)).replace(/\/$/,''),require=createRequire(root+'/package.json');
const {chromium,expect}=require('@playwright/test'),AxeBuilder=require('@axe-core/playwright').default;
const fixture=JSON.parse(fs.readFileSync(root+'/.deploy/demo-fixture.json'));
const browser=await chromium.launch(),ctx=await browser.newContext({viewport:{width:1440,height:1000}}),page=await ctx.newPage();
fs.mkdirSync('/tmp/shiftfix-assistant',{recursive:true});
let errors=[],role='admin',blocked=true,confirmed=0,modelCalls=0,catalogCalls=0,ruleSaves=0;
const items=[...fixture.items],catalog=structuredClone(fixture.catalog),owner=()=>({id:'qa',name:'Demo reviewer',role,email:'qa@example.invalid',onboardingComplete:true,demoDataset:fixture.manifest});
const asset=catalog.assets.find(x=>!x.archived),meter=catalog.meters[0];
const draft={id:'9b09dd7b-121d-4518-83ec-f3ab0289d4ab',kind:'work_order',context:{machineName:asset.name,machineCode:asset.code||asset.id},expiresAt:Math.floor(Date.now()/1000)+900,payload:{machineId:asset.id,title:'Inspect hydraulic oil leak',description:'Oil below the press after the morning shift. Inspect before operation.',priority:'high',category:'Hydraulic'}};
const rule={id:'c58d9043-026d-46bd-b5c8-5c3cf382f523',kind:'automations',context:{meterName:meter.name},expiresAt:Math.floor(Date.now()/1000)+900,payload:{name:'Press meter exception review',meterId:meter.id,enabled:false}};
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/503|410/.test(m.text()))errors.push(m.text())});
await page.route('**/config.json',r=>r.fulfill({json:{apiUrl:'https://qa.shiftfix.invalid',region:'ap-south-1',clientId:'qa',userPoolId:'qa'}}));
await page.route('https://qa.shiftfix.invalid/**',async r=>{
const path=new URL(r.request().url()).pathname,body=r.request().postDataJSON();let status=200,json={items:[]};
if(path==='/me')json=owner();
if(path==='/machines')json={items:catalog.assets.filter(x=>!x.archived)};
if(path==='/workorders')json={items};
if(path==='/users')json={items:[owner(),...fixture.users]};
if(path==='/catalog'){catalogCalls++;json={catalog}}
if(path==='/assistant/status')json={configured:true,model:'Amazon Nova Micro · Amazon Bedrock',scope:role,dataScope:'demo'};
if(path==='/assistant/search'){const rows=items.filter(x=>!x.archived);json={result:{totalMatches:rows.length,items:rows.slice(0,3)},sources:rows.slice(0,3).map(x=>({kind:'work_order',id:x.id,label:x.number+' · '+x.title})),mode:'permission-scoped search; no AI inference'}}
if(path==='/assistant/chat'){modelCalls++;expect(body.history.every(x=>['user','assistant'].includes(x.role))).toBeTruthy();await new Promise(resolve=>setTimeout(resolve,300));if(blocked){status=503;json={message:'AWS has restricted Bedrock inference for this account (Operation not allowed). Direct workspace search remains available.',code:'AI_ACCOUNT_RESTRICTED'}}else if(body.message.includes('automation')){json={reply:'Review this paused automation draft in the normal editor. Nothing has been saved.',sources:[],drafts:[rule],toolsUsed:['draft_rule'],model:'Amazon Nova Micro · Amazon Bedrock'}}else if(body.message.includes('expired')){json={reply:'Review this draft.',sources:[],drafts:[{...draft,id:'expired-draft',expiresAt:1}]}}else{json={reply:'I found the press and prepared a report. Review the details and confirm to create a request.',sources:[{kind:'page',page:'Assets',label:'Assets'}],drafts:[draft],toolsUsed:['search_catalog','draft_work_order'],model:'Amazon Nova Micro · Amazon Bedrock'}}}
if(path==='/assistant/confirm'){confirmed++;expect(body).toEqual({draftId:draft.id});const job={...items[0],...draft.payload,id:'new-ai-job',number:'WO-QA-SAFE',machineName:asset.name,reporterId:'qa',reporterName:'Demo reviewer',status:'pending_review',version:1,archived:false,attachments:[],createdAt:new Date().toISOString(),possibleDuplicate:true,possibleResolved:false};if(!items.some(x=>x.id===job.id))items.unshift(job);json={workOrder:job}}
if(path==='/assistant/review'){expect(body).toEqual({draftId:rule.id});json={draft:rule}}
if(path.startsWith('/catalog/')&&r.request().method()==='POST'){ruleSaves++;json={id:'not-needed'}}
if(path.startsWith('/workorders/')){const job=items.find(x=>x.id===path.split('/')[2]);json={...job,attachments:[],activity:[]}}
await r.fulfill({status,json});
});
await page.addInitScript(()=>sessionStorage.setItem('shiftfix-token','LOCAL_FIXTURE_ONLY'));
const axe=async label=>{const a=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();console.log(label,JSON.stringify(a.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({html:n.html,why:n.failureSummary}))}))));expect(a.violations).toEqual([])};
const fit=async()=>expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
await page.goto('http://localhost:5174');await page.getByRole('heading',{name:'Work order statistics',exact:true}).waitFor();await expect(page).toHaveTitle(/ShiftFix/);const initialCatalogCalls=catalogCalls;
await page.getByRole('button',{name:'Ask ShiftFix',exact:true}).click();await expect(page.getByRole('heading',{name:'Your maintenance workspace, in plain language.'})).toBeVisible();
await expect(page.getByText(/This assistant uses fictional demo records/)).toBeVisible();await axe('Assistant empty');await page.screenshot({path:'/tmp/shiftfix-assistant/desktop.png'});
await page.getByRole('button',{name:'Show my overdue work orders',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Operation not allowed');await expect(page.getByText('Assistant access pending',{exact:true})).toBeVisible();await expect(page.locator('#assistant-message')).toHaveValue('Show my overdue work orders');expect(confirmed).toBe(0);
await page.getByRole('button',{name:'Search records',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'matching records'})).toBeVisible();expect(catalogCalls).toBe(initialCatalogCalls);await axe('Assistant verification pending and direct search');await page.screenshot({path:'/tmp/shiftfix-assistant/verification.png',fullPage:true});
await page.getByRole('button',{name:'Open record',exact:true}).first().click();await page.locator('.detail h2').waitFor();
await page.getByRole('button',{name:'Ask ShiftFix',exact:true}).click();await expect(page.getByText('Assistant access pending',{exact:true})).toBeVisible();
blocked=false;await page.locator('#assistant-message').fill('Draft a work order for the oil leak');await page.locator('#assistant-message').press('Enter');await expect(page.getByRole('region',{name:'Work order draft'})).toBeVisible();expect(confirmed).toBe(0);await axe('Assistant draft');
await page.getByRole('button',{name:'Confirm create',exact:true}).click();await expect(page.getByText('WO-QA-SAFE created',{exact:true})).toBeVisible();expect(confirmed).toBe(1);await expect(page.getByRole('button',{name:'Confirm create',exact:true})).toHaveCount(0);await page.screenshot({path:'/tmp/shiftfix-assistant/created.png',fullPage:true});
await page.getByRole('button',{name:'Open work order',exact:true}).click();await expect(page.locator('#detail-heading')).toHaveText(draft.payload.title);
await page.getByRole('button',{name:'Ask ShiftFix',exact:true}).click();await page.locator('#assistant-message').fill('Draft an automation for the press meter');await page.getByRole('button',{name:'Ask',exact:true}).click();await expect(page.getByRole('region',{name:'Planning draft'})).toBeVisible();await page.getByRole('button',{name:'Review in editor',exact:true}).click();await expect(page.locator('h1')).toHaveText('Automations');await expect(page.getByLabel('Name *',{exact:true})).toHaveValue(rule.payload.name);await expect(page.getByLabel('Automation enabled',{exact:true})).not.toBeChecked();expect(ruleSaves).toBe(0);
await page.getByRole('button',{name:'Ask ShiftFix',exact:true}).click();await page.locator('#assistant-message').fill('Show an expired draft');await page.getByRole('button',{name:'Ask',exact:true}).click();await expect(page.getByRole('button',{name:'Draft expired',exact:true})).toBeDisabled();
await page.setViewportSize({width:390,height:844});await fit();await axe('Assistant mobile');await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.screenshot({path:'/tmp/shiftfix-assistant/mobile.png',fullPage:true});
await page.getByRole('button',{name:'Help & accessibility',exact:true}).click();await page.getByRole('button',{name:'Turn on high contrast',exact:true}).click();await page.getByRole('button',{name:'Use larger text',exact:true}).click();await page.getByRole('button',{name:'Ask ShiftFix',exact:true}).click();await page.setViewportSize({width:320,height:800});await fit();await axe('Assistant 320px contrast larger text');
role='reporter';await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page.locator('h1')).toHaveText('Work orders');await page.getByRole('button',{name:'Ask ShiftFix',exact:true}).click();await expect(page.locator('#assistant-search-scope option[value=people]')).toHaveCount(0);await expect(page.locator('#assistant-search-scope option[value=parts]')).toHaveCount(0);await expect(page.getByRole('region',{name:'Work order draft'})).toHaveCount(0);
expect(errors).toEqual([]);console.log('PASS blocked inference is explicit, independent read-only search/source links, chat memory, no write before confirmation, one confirmed request, paused rule editor prefill, expiry, role reset, desktop/mobile/320px axe.');await browser.close();
