// Maintiny UI checks use local fixtures only. Build demo data; run Vite on5174.
import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
const fixture=JSON.parse(fs.readFileSync('.deploy/demo-fixture.json','utf8'));
fs.mkdirSync('/tmp/shiftfix-maintiny',{recursive:true});
const browser=await chromium.launch(),ctx=await browser.newContext({viewport:{width:1440,height:1000}}),page=await ctx.newPage();
let role='admin',blocked=false,failDelete=false,holdNext=false,releaseHeld,confirms=0,ruleSaves=0,errors=[];
const threads=new Map(),catalog=structuredClone(fixture.catalog),items=structuredClone(fixture.items),asset=catalog.assets.find(x=>!x.archived),meter=catalog.meters[0];
const owner=()=>({id:'qa',name:'Demo reviewer',email:'qa@example.invalid',role,onboardingComplete:true,demoDataset:fixture.manifest});
const metadata=t=>({id:t.id,title:t.role===role?t.title:'Conversation from previous access',updatedAt:t.updatedAt,createdAt:t.createdAt,turnCount:t.turnCount,version:t.version,available:t.role===role,full:false});
const draft={id:'9b09dd7b-121d-4518-83ec-f3ab0289d4ab',kind:'work_order',context:{machineName:asset.name,machineCode:asset.code||asset.id},expiresAt:Math.floor(Date.now()/1000)+900,payload:{machineId:asset.id,title:'Inspect hydraulic oil leak',description:'Fictional oil below the press.',priority:'high',category:'Hydraulic'}};
const rule={id:'c58d9043-026d-46bd-b5c8-5c3cf382f523',kind:'automations',context:{meterName:meter.name},expiresAt:Math.floor(Date.now()/1000)+900,payload:{name:'Press meter exception review',meterId:meter.id,enabled:false}};
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/503|410/.test(m.text()))errors.push(m.text())});
await page.route('**/config.json',r=>r.fulfill({json:{apiUrl:'https://qa.shiftfix.invalid',region:'ap-south-1',clientId:'qa',userPoolId:'qa'}}));
await page.route('https://qa.shiftfix.invalid/**',async r=>{
 const path=new URL(r.request().url()).pathname,method=r.request().method(),body=r.request().postDataJSON();let status=200,json={items:[]};
 if(path==='/me')json=owner();if(path==='/machines')json={items:catalog.assets.filter(x=>!x.archived)};if(path==='/workorders')json={items};if(path==='/users')json={items:[owner(),...fixture.users]};if(path==='/catalog')json={catalog};
 if(path==='/assistant/status')json={configured:true,dataScope:'demo',model:'Maintenance assistant'};
 if(path==='/assistant/conversations'){
   if(method==='POST'){if(!threads.has(body.id))threads.set(body.id,{id:body.id,title:'New conversation',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),version:1,turnCount:0,role,messages:[]});json={conversation:metadata(threads.get(body.id))}}
   else json={items:[...threads.values()].map(metadata).reverse()};
 }
 if(path.startsWith('/assistant/conversations/')){
   const id=path.split('/')[3],t=threads.get(id);
   if(path.endsWith('/delete')){if(failDelete){status=503;json={message:'The deletion could not complete. Retry.'}}else{threads.delete(id);json={deleted:true,id}}}
   else if(!t){status=410;json={message:'This conversation was deleted.',code:'CHAT_DELETED'}}else json={conversation:metadata(t),messages:t.messages};
 }
 if(path==='/assistant/chat'){
   expect(body.history).toBeUndefined();expect(body.conversationId).toBeTruthy();const t=threads.get(body.conversationId);
   if(blocked){status=503;json={message:'The model service is unavailable. Use direct workspace search.',code:'AI_UNAVAILABLE'}}
   else if(!t){status=410;json={message:'This conversation was deleted.',code:'CHAT_DELETED'}}
   else{
    const isRule=body.message.includes('automation'),expired=body.message.includes('expired');
    const text=isRule?'Review this paused automation in the editor. Nothing has been saved.':expired?'This old draft has expired.':body.message.includes('draft')?'Review and confirm this work order. Nothing has been created.':'There are 3 fictional work orders awaiting verification.';
    const ds=isRule?[rule]:expired?[{...draft,id:'expired',expiresAt:1,expired:true}]:body.message.includes('draft')?[draft]:[];
    t.title=t.turnCount?t.title:body.message.slice(0,80);t.turnCount++;t.version++;t.updatedAt=new Date().toISOString();
    t.messages.push({id:body.requestId+'-user',role:'user',text:body.message},{id:body.requestId+'-assistant',role:'assistant',text,sources:[],drafts:ds});
    json={reply:text,drafts:ds,sources:[],conversation:metadata(t),messages:structuredClone(t.messages)};
    if(holdNext){holdNext=false;await new Promise(resolve=>{releaseHeld=resolve})}
   }
 }
 if(path==='/assistant/search')json={result:{totalMatches:items.length,items:items.slice(0,3)},sources:[],mode:'no AI inference'};
 if(path==='/assistant/confirm'){
   confirms++;const job={...items[0],...draft.payload,id:'new-ai-job',number:'WO-QA-SAFE',status:'pending_review',version:1,archived:false,reporterId:'qa',attachments:[]};if(!items.some(x=>x.id===job.id))items.unshift(job);json={workOrder:job};
   for(const t of threads.values())for(const m of t.messages)for(const d of m.drafts||[])if(d.id===draft.id)d.confirmedWorkOrder=job;
 }
 if(path==='/assistant/review')json={draft:rule};
 if(path.startsWith('/catalog/')&&method==='POST'){ruleSaves++;json={id:'not-needed'}}
 if(path.startsWith('/workorders/')){const j=items.find(x=>x.id===path.split('/')[2]);json={...j,attachments:[],activity:[]}}
 await r.fulfill({status,json});
});
await page.addInitScript(()=>sessionStorage.setItem('shiftfix-token','LOCAL_FIXTURE_ONLY'));
const nav=name=>page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name,exact:true});
const launcher=()=>page.getByRole('button',{name:'Open Maintiny assistant',exact:true});
const widget=()=>page.getByRole('dialog',{name:'Maintiny',exact:true});
const type=async text=>{await page.getByLabel('Message Maintiny',{exact:true}).fill(text);await page.getByRole('button',{name:'Send message',exact:true}).click()};
const axe=async label=>{const a=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();console.log(label,JSON.stringify(a.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({html:n.html,why:n.failureSummary}))}))));expect(a.violations).toEqual([])};
const fit=async()=>expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
await page.goto('http://localhost:5174');await page.getByRole('heading',{name:'Work order statistics',exact:true}).waitFor();
await expect(launcher()).toBeVisible();await launcher().click();await expect(widget()).toBeVisible();await expect(page.getByText('What needs attention this shift?',{exact:true})).toBeVisible();await axe('Floating empty');
await type('Show demo work awaiting verification');await expect(page.getByText('There are 3 fictional work orders awaiting verification.',{exact:true})).toBeVisible();expect(threads.size).toBe(1);
await page.screenshot({path:'/tmp/shiftfix-maintiny/floating.png'});
await page.keyboard.press('Escape');await expect(widget()).not.toBeVisible();await expect(launcher()).toBeFocused();
await nav('Parts').click();await expect(launcher()).toBeVisible();await launcher().click();await expect(page.getByText('There are 3 fictional work orders awaiting verification.',{exact:true})).toBeVisible();
await page.getByRole('button',{name:'Open Maintiny tab',exact:true}).click();await expect(page.locator('h1')).toHaveText('Maintiny');await expect(launcher()).toHaveCount(0);await expect(page.getByRole('button',{name:/Show demo work awaiting verification.*exchange/})).toBeVisible();await axe('Dedicated saved chat');await page.screenshot({path:'/tmp/shiftfix-maintiny/dedicated.png'});
await page.reload();await nav('Maintiny').click();await page.getByRole('button',{name:/Show demo work awaiting verification.*exchange/}).click();await expect(page.getByText('There are 3 fictional work orders awaiting verification.',{exact:true})).toBeVisible();
await type('Please draft an oil leak work order');await expect(page.getByRole('region',{name:'Work order draft'})).toBeVisible();expect(confirms).toBe(0);await page.getByRole('button',{name:'Confirm create',exact:true}).click();await expect(page.getByText('WO-QA-SAFE created',{exact:true})).toBeVisible();expect(confirms).toBe(1);
await page.getByRole('button',{name:'New conversation',exact:true}).click();await type('Prepare an automation');await page.getByRole('button',{name:'Review in editor',exact:true}).click();await expect(page.locator('h1')).toHaveText('Automations');await expect(page.getByLabel('Name *',{exact:true})).toHaveValue(rule.payload.name);await expect(page.getByLabel('Automation enabled',{exact:true})).not.toBeChecked();expect(ruleSaves).toBe(0);
await nav('Maintiny').click();await page.getByRole('button',{name:'New conversation',exact:true}).click();await type('Show expired draft');await expect(page.getByText('This draft has expired. Ask Maintiny to prepare a new one.',{exact:true})).toBeVisible();
// Delete confirmation is cancelable; failed deletion is retryable and preserves the chat.
await page.getByRole('button',{name:'Delete current conversation',exact:true}).click();await expect(page.getByRole('alertdialog')).toBeVisible();await expect(page.getByRole('button',{name:'Keep chat',exact:true})).toBeFocused();await page.keyboard.press('Escape');await expect(page.getByRole('alertdialog')).not.toBeVisible();
failDelete=true;await page.getByRole('button',{name:'Delete current conversation',exact:true}).click();await page.getByRole('button',{name:'Delete chat',exact:true}).click();await expect(page.getByRole('alertdialog').getByRole('alert')).toContainText('Retry');failDelete=false;await page.getByRole('button',{name:'Delete chat',exact:true}).click();await expect(page.getByRole('alertdialog')).not.toBeVisible();await expect(page.getByText('This draft has expired. Ask Maintiny to prepare a new one.',{exact:true})).toHaveCount(0);
// A successful network reply delivered after deletion must not bring a chat back.
await page.getByLabel('Message Maintiny',{exact:true}).fill('Late reply must not resurrect me');holdNext=true;await page.getByRole('button',{name:'Send message',exact:true}).click();await expect(page.getByRole('button',{name:'Delete current conversation',exact:true})).toBeVisible();await expect.poll(()=>typeof releaseHeld).toBe('function');await page.getByRole('button',{name:'Delete current conversation',exact:true}).click();await page.getByRole('button',{name:'Delete chat',exact:true}).click();await expect(page.getByRole('alertdialog')).not.toBeVisible();releaseHeld();await expect(page.getByText('Late reply must not resurrect me',{exact:true})).toHaveCount(0);
blocked=true;await type('A blocked question');await expect(page.getByRole('alert').first()).toContainText('unavailable');await expect(page.getByLabel('Message Maintiny',{exact:true})).toHaveValue('A blocked question');await page.getByRole('button',{name:'Search records',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'matching records'})).toBeVisible();blocked=false;
// Launcher exists on each other signed-in destination, including catalog and help views.
const labels=await page.getByRole('navigation',{name:'Main navigation'}).locator('button[aria-label]').evaluateAll(bs=>bs.map(b=>b.getAttribute('aria-label')));
for(const name of labels){if(name==='Maintiny')continue;await nav(name).click();await expect(launcher()).toBeVisible()}
await nav('Maintiny').click();await expect(launcher()).toHaveCount(0);await page.setViewportSize({width:390,height:844});await fit();await page.getByRole('button',{name:/Saved chats \(/}).click();await axe('Maintiny mobile history');await page.screenshot({path:'/tmp/shiftfix-maintiny/mobile.png',fullPage:true});
await nav('Help & accessibility').click();await page.getByRole('button',{name:'Turn on high contrast',exact:true}).click();await page.getByRole('button',{name:'Use larger text',exact:true}).click();await launcher().click();await page.setViewportSize({width:320,height:800});await fit();await axe('Floating 320px contrast larger text');await page.screenshot({path:'/tmp/shiftfix-maintiny/mobile-widget.png'});await page.keyboard.press('Escape');
await nav('Maintiny').click();await fit();await axe('Maintiny 320px contrast larger text');
role='reporter';await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page.locator('h1')).toHaveText('Work orders');await nav('Maintiny').click();await expect(page.getByText('Review and confirm this work order. Nothing has been created.',{exact:true})).toHaveCount(0);await expect(page.getByRole('region',{name:'Planning draft'})).toHaveCount(0);await expect(page.locator('#assistant-search-scope option[value=people]')).toHaveCount(0);
expect(errors).toEqual([]);console.log('PASS shared launcher/tab, persisted reload, confirmation, paused editor, expiry, deletion/cancel/retry/late reply, every navigation destination, mobile/320px accessibility and role reset.');await browser.close();
