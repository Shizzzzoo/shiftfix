// Playwright product walkthrough with fictional browser fixtures.
// This recording is illustrative: it does not send authenticated API requests.
import { chromium, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const appUrl = process.env.APP_URL || 'http://localhost:5174/';
const outputDir = path.resolve(process.env.VIDEO_DIR || '.deploy/video-recordings');
const fixture = JSON.parse(fs.readFileSync('.deploy/demo-fixture.json', 'utf8'));
fs.mkdirSync(outputDir, { recursive: true });
const apiUrl = new URL('/qa-fixture-api', appUrl).href.replace(/\/$/, '');
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 810 },
  recordVideo: { dir: outputDir, size: { width: 1440, height: 810 } },
  deviceScaleFactor: 1,
});
const page = await context.newPage();
const video = page.video();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
let role = 'admin';
let activeId = null;
let sequence = 0;
const jobs = structuredClone(fixture.items);
const worker = { id: 'fixture-worker', name: 'Avery Chen', email: 'avery@example.invalid', role: 'worker', demo: false };
const manager = { id: 'fixture-manager', name: 'Morgan Lee', email: 'morgan@example.invalid', role: 'admin', demo: false };
const threads = new Map();
const events = new Map();
const me = () => ({ ...(role === 'worker' ? worker : manager), onboardingComplete: true, demoDataset: fixture.manifest });
const now = () => new Date().toISOString();
const meta = thread => ({ id: thread.id, title: thread.title, createdAt: thread.createdAt, updatedAt: thread.updatedAt, turnCount: thread.turnCount, version: thread.version, available: true, full: false });
const activity = job => events.get(job.id) || fixture.rows.filter(row => row.PK === job.PK && row.SK?.startsWith('EVENT#'));
const addEvent = (job, action, reason) => {
  const list = events.get(job.id) || [];
  list.push({ id: crypto.randomUUID(), action, at: now(), actorId: me().id, actorName: me().name, reason });
  events.set(job.id, list);
};

await page.route('**/config.json', route => route.fulfill({ json: { apiUrl, region: 'ap-south-1', clientId: 'fixture', userPoolId: 'fixture' } }));
await page.route(apiUrl + '/**', async route => {
  const request = route.request();
  const pathname = new URL(request.url()).pathname.replace(/^\/qa-fixture-api/, '');
  const method = request.method();
  const body = request.postDataJSON() || {};
  let status = 200, response = { items: [] };
  if (pathname === '/me') response = me();
  else if (pathname === '/machines') response = { items: fixture.catalog.assets.filter(item => !item.archived) };
  else if (pathname === '/users') response = { items: [manager, worker, ...fixture.users] };
  else if (pathname === '/catalog') response = { catalog: fixture.catalog };
  else if (pathname === '/settings/workflow') response = { ackMinutes: 60, repairMinutes: 240, verifyMinutes: 120, version: 1 };
  else if (pathname === '/workorders' && method === 'GET') response = { items: jobs };
  else if (pathname === '/workorders' && method === 'POST') {
    const machine = fixture.catalog.assets.find(item => item.id === body.machineId);
    const job = {
      PK: 'WORK#fixture-' + (++sequence), id: 'fixture-' + sequence, number: 'DEMO-NEW-' + String(sequence).padStart(3, '0'),
      title: body.title, description: body.description, priority: body.priority, category: body.category,
      machineId: body.machineId, machineName: machine?.name || 'Demo machine', status: 'pending_review', assignmentStatus: 'unassigned',
      assigneeId: '', assigneeName: '', reporterId: manager.id, reporterName: manager.name,
      createdAt: now(), updatedAt: now(), version: 1, attachments: body.attachments || [], archived: false,
      possibleDuplicate: true, possibleResolved: false,
    };
    jobs.unshift(job); activeId = job.id; addEvent(job, 'reported', 'Fictional fault submitted in scripted demo'); response = job;
  } else if (pathname.startsWith('/workorders/')) {
    const job = jobs.find(item => item.id === pathname.split('/')[2]);
    if (!job) { status = 404; response = { message: 'Not found' }; }
    else if (pathname.endsWith('/actions') && method === 'POST') {
      if (body.version !== job.version) { status = 409; response = { message: 'The work order changed. Reload it.' }; }
      else {
        if (body.action === 'approve') { job.status = 'open'; job.assignmentStatus = 'awaiting_acceptance'; job.assigneeId = worker.id; job.assigneeName = worker.name; }
        if (body.action === 'accept') { job.status = 'in_progress'; job.assignmentStatus = 'accepted'; }
        if (body.action === 'submit') job.status = 'awaiting_verification';
        if (body.action === 'verify') { job.status = 'closed'; job.closedAt = now(); }
        if (body.action === 'keep_separate') job.possibleDuplicate = false;
        job.updatedAt = now(); job.version += 1; addEvent(job, body.action, body.reason || 'Scripted demo decision'); response = job;
      }
    } else response = { ...job, attachments: job.attachments.map(item => ({ ...item, url: '/assets/factory-floor.jpg' })), activity: activity(job) };
  }
  if (pathname === '/assistant/status') response = { configured: true, dataScope: 'demo', model: 'Maintenance assistant' };
  if (pathname === '/assistant/conversations') {
    if (method === 'POST') {
      if (!threads.has(body.id)) threads.set(body.id, { id: body.id, title: 'New conversation', createdAt: now(), updatedAt: now(), turnCount: 0, version: 1, messages: [] });
      response = { conversation: meta(threads.get(body.id)) };
    } else response = { items: [...threads.values()].map(meta).reverse() };
  }
  if (pathname.startsWith('/assistant/conversations/')) {
    const id = pathname.split('/')[3], thread = threads.get(id);
    if (pathname.endsWith('/delete')) { threads.delete(id); response = { deleted: true, id }; }
    else response = thread ? { conversation: meta(thread), messages: thread.messages } : { conversation: null, messages: [] };
  }
  if (pathname === '/assistant/chat') {
    const thread = threads.get(body.conversationId);
    if (!thread) { status = 410; response = { message: 'Conversation deleted' }; }
    else {
      const reply = 'Three fictional requests are awaiting verification. Open the review inbox to check evidence and approve each repair.';
      thread.title = body.message.slice(0, 80); thread.updatedAt = now(); thread.turnCount += 1; thread.version += 1;
      thread.messages.push({ id: body.requestId + '-u', role: 'user', text: body.message }, { id: body.requestId + '-a', role: 'assistant', text: reply, sources: [], drafts: [] });
      response = { reply, drafts: [], sources: [], conversation: meta(thread), messages: thread.messages };
    }
  }
  await route.fulfill({ status, json: response });
});
await page.addInitScript(() => sessionStorage.setItem('shiftfix-token', 'LOCAL_FIXTURE_ONLY'));

const nav = name => page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name, exact: true });
const pause = ms => page.waitForTimeout(ms);
const caption = async (eyebrow, title, text) => {
  await page.evaluate(({ eyebrow, title, text }) => {
    let root = document.getElementById('shiftfix-recording-overlay');
    if (!root) {
      root = document.createElement('div'); root.id = 'shiftfix-recording-overlay'; document.body.appendChild(root);
      const style = document.createElement('style'); style.textContent = `
        #shiftfix-recording-overlay,#shiftfix-recording-overlay *{pointer-events:none!important}
        #shiftfix-recording-overlay{position:fixed!important;z-index:2147483647!important;left:310px!important;bottom:16px!important;right:auto!important;top:auto!important;width:880px!important;height:auto!important;box-sizing:border-box!important;display:block!important;padding:15px 23px 16px;color:#fff;background:rgba(13,25,34,.96);border-left:5px solid #ff8d55;border-radius:12px;font-family:Arial,sans-serif;box-shadow:0 10px 32px #0006}
        #shiftfix-recording-overlay small{display:block;color:#ffbc91;font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
        #shiftfix-recording-overlay strong{display:block;font-size:23px;line-height:1.18;margin:4px 0}
        #shiftfix-recording-overlay span{display:block;font-size:15px;line-height:1.35;color:#e7eef2}
        #shiftfix-demo-label{position:fixed;z-index:2147483647;right:18px;top:16px;padding:8px 12px;border-radius:7px;background:#142b37;color:#fff;font:700 12px Arial;box-shadow:0 4px 16px #0005;pointer-events:none}`;
      document.head.appendChild(style);
      const label = document.createElement('div'); label.id = 'shiftfix-demo-label'; label.textContent = 'SCRIPTED DEMO · FICTIONAL DATA'; document.body.appendChild(label);
    }
    root.replaceChildren();
    for (const [tag, value] of [['small', eyebrow], ['strong', title], ['span', text]]) { const el = document.createElement(tag); el.textContent = value; root.appendChild(el); }
  }, { eyebrow, title, text });
};
const scene = async (eyebrow, title, text, ms = 6000) => { await caption(eyebrow, title, text); await pause(ms); };

try {
  await page.goto(appUrl, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Work order statistics' }).waitFor();
  await scene('ShiftFix · Factory maintenance', 'From fault report to verified repair', 'A serverless work-order workflow with clear ownership across shifts.', 7000);
  await scene('01 · Overview', 'One operational picture', 'The dashboard tracks review load, overdue repairs and two months of fictional history.', 6500);
  await page.getByRole('button', { name: 'Report fault', exact: true }).click();
  await caption('02 · Report', 'Capture the fault at the machine', 'Select the asset, describe the condition, and add photo evidence where available.');
  await page.getByRole('dialog', { name: 'Report a machine fault' }).getByLabel('Fault title').fill('Hydraulic press seal leaking at shift handover');
  await page.getByRole('dialog', { name: 'Report a machine fault' }).getByLabel('Description').fill('Fictional demo: oil visible near the hydraulic coupling after the evening shift. Stop and inspect before restart.');
  await page.getByRole('dialog', { name: 'Report a machine fault' }).getByLabel('Priority').selectOption('high');
  await pause(6000);
  await page.getByRole('button', { name: 'Submit fault report' }).click();
  await expect(page.getByText('DEMO-NEW-001').first()).toBeVisible();
  await scene('03 · Saved request', 'A numbered, auditable work order', 'The request enters manager review with equipment, priority and reporter linked.', 6500);
  await nav('Review inbox').click();
  await scene('04 · Review', 'Duplicate and repeat-fault checks', 'An existing issue is advisory. A manager decides whether to merge, reject or keep separate.', 6500);
  await page.getByRole('button', { name: /Open DEMO-NEW-001:/ }).click();
  await page.getByLabel('Responsible worker').selectOption(worker.id);
  await pause(3000);
  await page.getByRole('button', { name: 'Approve & assign' }).click();
  await expect(page.getByText('DEMO-NEW-001').first()).toBeVisible();
  await scene('05 · Ownership', 'Assign the responsible worker', 'Every decision is version checked and recorded in the activity timeline.', 6000);
  role = 'worker'; await page.reload(); await page.getByRole('button', { name: /Open DEMO-NEW-001:/ }).click();
  await scene('06 · Worker', 'Accept or return the assignment', 'Workers can accept, report a blocker, or return a job that belongs elsewhere.', 6000);
  await page.getByRole('button', { name: 'Accept assignment' }).click();
  await expect(page.getByRole('button', { name: 'Submit repair' })).toBeVisible();
  await page.getByLabel('Notes / decision reason').fill('Isolated equipment, replaced seal and completed a function check. Fictional demonstration.');
  await expect(page.getByRole('button', { name: 'Submit repair' })).toBeEnabled();
  await pause(2000);
  await page.getByRole('button', { name: 'Submit repair' }).click();
  await scene('07 · Verification', 'Repair waits for supervisor sign-off', 'A repair submission does not close the work order until a manager verifies it.', 6500);
  role = 'admin'; await page.reload(); await nav('Review inbox').click(); await page.getByRole('button', { name: /Open DEMO-NEW-001:/ }).click();
  await page.getByRole('button', { name: 'Accept repair' }).click();
  await scene('08 · Audit trail', 'Verified and closed', 'The timeline records the report, assignment, acceptance, repair and verification.', 7000);
  await nav('Parts').click();
  await scene('09 · Connected operations', 'Parts, assets and locations', 'Inventory, meter readings, inspections and planned work share the same workspace.', 7000);
  await nav('Requests').click();
  await scene('10 · Edge cases', 'Every request stays accountable', 'Duplicate reports, prior repairs and returned assignments stay visible for human review.', 6500);
  await page.getByRole('button', { name: 'Open Maintiny assistant' }).click();
  await caption('11 · Maintiny', 'Ask within your role', 'Saved chats, scoped search and reviewed drafts. The temporary Gemini provider uses fictional demo data only.');
  await page.getByLabel('Message Maintiny').fill('Show demo work awaiting verification');
  await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByText('Three fictional requests are awaiting verification.', { exact: false })).toBeVisible();
  await pause(7000);
  await page.getByRole('button', { name: 'Open Maintiny tab' }).click();
  await scene('12 · Saved conversations', 'Continue or delete a chat', 'Maintiny stores private history and asks for confirmation before deleting a conversation.', 7000);
  const diagram = fs.readFileSync('docs/submission-assets/architecture.png').toString('base64');
  await page.setContent(`<html><head><style>body{margin:0;background:#f4f6f8;font:18px Arial;color:#17252e}.wrap{height:810px;display:flex;flex-direction:column;align-items:center;justify-content:center}h1{font-size:31px;margin:0 0 12px}img{max-width:1200px;max-height:620px;object-fit:contain}.note{font-size:16px;margin-top:12px;color:#40525e}.label{position:absolute;right:20px;top:18px;background:#142b37;color:white;padding:8px 12px;font-size:12px;border-radius:7px;font-weight:bold}</style></head><body><div class="label">SCRIPTED DEMO · FICTIONAL DATA</div><div class="wrap"><h1>Serverless architecture</h1><img src="data:image/png;base64,${diagram}" alt="ShiftFix serverless architecture"><div class="note">API Gateway · Lambda · DynamoDB · S3 · Step Functions · EventBridge Scheduler · Cognito</div></div></body></html>`);
  await pause(11000);
  await page.setContent(`<html><head><style>body{margin:0;height:810px;background:#14242e;color:#fff;font-family:Arial;display:grid;place-items:center;text-align:center}h1{font-size:66px;margin:0;color:#ff9d69}p{font-size:25px;margin:20px 0}small{font-size:16px;color:#b9c9d2}</style></head><body><div><h1>ShiftFix</h1><p>Built for the handoff. Verified at the finish.</p><small>github.com/Shizzzzoo/shiftfix</small><br><small>Live app: 11z3m6ydfe.execute-api.ap-south-1.amazonaws.com</small></div></body></html>`);
  await pause(6500);
  if (errors.length) throw new Error(errors.join('\n'));
} finally {
  await page.close();
  await context.close();
  await browser.close();
  console.log('Playwright recording:', await video.path());
}
