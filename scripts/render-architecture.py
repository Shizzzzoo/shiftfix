"""Render the ShiftFix architecture as editable SVG and a 3600px PNG."""
from pathlib import Path
from html import escape
import base64
import cairosvg
from PIL import ImageFont

OUT = Path('docs/submission-assets')
W,H=1800,1650
s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '''<defs>
<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#dce4ec"/></pattern>
<pattern id="safety" width="28" height="12" patternUnits="userSpaceOnUse" patternTransform="skewX(-35)"><rect width="14" height="12" fill="#ed8b51"/><rect x="14" width="14" height="12" fill="#263f4d"/></pattern>
<filter id="shadow" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="5" stdDeviation="7" flood-color="#122c42" flood-opacity=".07"/></filter>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#526b80"/></marker>
<marker id="purple" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#8353b7"/></marker>
</defs>''']
def rect(x,y,w,h,fill,stroke='none',r=16,extra=''):
 s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" {extra}/>')
def text(x,y,t,size=18,color='#405569',weight=400,anchor='start'):
 s.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(t)}</text>')
def logo(x,y,size):
 # Original factory roof + verified-repair mark, shared with the standalone PNG.
 s.append(f'<g transform="translate({x} {y}) scale({size/100})">{logo_mark}</g>')
def aws_icon(x,y,size,name):
 data=base64.b64encode((OUT/'aws-icons'/f'{name}.svg').read_bytes()).decode()
 s.append(f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>')
def line(d,purple=False,dash=False):
 color='#8353b7' if purple else '#526b80'
 s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" marker-end="url(#{"purple" if purple else "arrow"})" '+('stroke-dasharray="8 6"' if dash else '')+'/>')
def label(x,y,t,purple=False):
 width=len(t)*8.3+20
 rect(x-width/2,y-18,width,27,'#f5f8fb',r=6)
 text(x,y,t,15,'#8353b7' if purple else '#526b80',500,'middle')
def card(x,y,w,h,kicker,title,lines,color,icon,fill='#fff'):
 rect(x,y,w,h,fill,'#dbe4ed',16,'filter="url(#shadow)"')
 rect(x,y,6,h,color,r=3)
 service={'λ':'AWS-Lambda','ID':'Amazon-Cognito','↗':'Amazon-API-Gateway','S3':'Amazon-Simple-Storage-Service','DB':'Amazon-DynamoDB','◷':'Amazon-EventBridge','≋':'DynamoDB-Stream','⋈':'AWS-Step-Functions','UI':'Client'}.get(icon)
 if service:
  aws_icon(x+18,y+16,50,service)
 else:
  rect(x+20,y+20,42,42,color,r=10)
  text(x+41,y+48,icon,22,'#fff',700,'middle')
 text(x+78,y+34,kicker.upper(),12,color,700)
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',20)
 title_size=min(20,20*(w-100)/font.getlength(title))
 text(x+78,y+61,title,title_size,'#172b3b',700)
 for i,l in enumerate(lines):
  font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
  size=min(16,16*(w-44)/font.getlength(l))
  text(x+22,y+96+i*25,l,size)

logo_mark='''<rect x="0" y="0" width="100" height="100" rx="23" fill="#e77b3f"/>
<rect x="5" y="5" width="90" height="90" rx="19" fill="none" stroke="#ffbd8f" stroke-opacity=".5"/>
<path d="M19 70V43L39 31V43L58 31V47H72V24H82V69H19Z" fill="none" stroke="#fff8ee" stroke-width="4.5" stroke-linejoin="round"/>
<path d="M29 56V61M42 56V61M55 56V61" stroke="#fff8ee" stroke-width="4.5" stroke-linecap="round"/>
<circle cx="76" cy="77" r="19" fill="#142732" stroke="#e77b3f" stroke-width="4"/>
<path d="M68 77L74 83L85 71" fill="none" stroke="#fff8ee" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'''
rect(0,0,W,H,'#f5f8fb',r=0)
s.append(f'<rect x="0" y="210" width="1800" height="1255" fill="url(#dots)"/>')
rect(0,0,1800,210,'#142732',r=0)
logo(60,36,92)
text(178,76,'ShiftFix',43,'#fff',700)
text(410,76,'Serverless factory maintenance',27,'#cfdee8',400)
text(178,112,'Every fault owned. Every repair verified. Every shift connected.',18,'#b8cbd8')
# Factory elevation / conveyor line, drawn as an understated engineering sketch.
s.append('''<g transform="translate(1290 24)" stroke="#608093" stroke-width="2" stroke-linejoin="round">
<path d="M0 93H450M18 81V42L75 17V42L132 17V48H169V11H186V48H245V81Z" fill="#1b3442"/>
<path d="M169 11L173 2H183L186 11M31 51H57V65H31ZM86 51H112V65H86ZM141 57H156V71H141Z" fill="none"/>
<path d="M207 56H229V80H207Z" fill="none"/>
<rect x="275" y="64" width="150" height="15" rx="7" fill="#1b3442"/>
<path d="M290 79V92M410 79V92"/>
<path d="M296 62V41H325V62M356 62V33H385V62" fill="#243f4c" stroke="#c98458"/>
<path d="M264 45V22H290L308 5L324 14L306 31H282V45" fill="none" stroke="#c98458"/>
<circle cx="282" cy="22" r="5" fill="#142732" stroke="#c98458"/>
<circle cx="308" cy="5" r="4" fill="#142732" stroke="#c98458"/>
<path d="M285 71H414" stroke-dasharray="4 9"/>
</g>''')
s.append('<rect x="0" y="204" width="1800" height="6" fill="url(#safety)"/>')
for x,n,t in [(90,'01','REPORT'),(360,'02','REVIEW & ASSIGN'),(760,'03','REPAIR'),(1070,'04','VERIFY'),(1390,'05','HISTORY')]:
 text(x,177,n,14,'#ffab79',700);text(x+35,177,t,15,'#fff',700)

# Regions are diagram groupings, not VPC or subnet boundaries.
rect(40,240,1720,1190,'none','#c8d6e2',22,'stroke-width="2"')
for x,y in [(52,252),(1748,252),(52,1418),(1748,1418)]:
 s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#c2cfda"/><path d="M{x-2} {y+2}L{x+2} {y-2}" stroke="#f5f8fb" stroke-width="1.2"/>')
# Dimension ticks echo an equipment drawing without competing with the graph.
for y in range(320,1370,32):
 s.append(f'<path d="M19 {y}H{29 if (y-320)%128==0 else 24}" stroke="#b9c9d5" stroke-width="1"/>')
text(65,270,'APPLICATION & AWS MANAGED SERVICES',13,'#526b80',700)
text(1730,270,'ap-south-1  •  Deployed prototype',13,'#526b80',500,'end')

# Connectors behind cards.
line('M370 390 H470');label(420,372,'Sign in')
line('M220 310 V292 H1040 V330');label(1040,309,'HTTPS requests + JWT')
line('M770 390 H870',dash=True);label(820,372,'Validate JWT')
line('M1210 390 H1310');label(1260,372,'Public GETs')
line('M1040 480 V590');label(1040,544,'Authenticated app routes')
line('M1130 480 V540 H1510 V590');label(1420,526,'Assistant routes')
line('M620 480 V590');label(620,544,'Post-confirmation')
line('M770 670 H800 V460 H770');label(800,510,'Set group')
line('M870 625 H820 V565 H410 V625 H370');label(620,580,'Signed photo access')
line('M220 480 V590',dash=True);label(220,545,'Signed upload / view')
line('M1040 750 V870');label(1040,816,'Atomic writes + activity + timer')
line('M1430 750 V810 H1160 V870');label(1390,796,'Scoped tools + private chats')
line('M1510 750 V870',purple=True,dash=True);label(1510,843,'Model call',purple=True)
line('M370 950 H470');label(420,930,'Due plans')
line('M550 1040 V1080 H220 V1140');label(315,1104,'Committed TIMER inserts')
line('M370 1225 H470');label(420,1207,'Filtered')
line('M770 1225 H870');label(820,1207,'Start')
line('M1210 1225 H1310');label(1260,1207,'Invoke')
line('M1510 1140 V1080 H1090 V1040');label(1320,1104,'Recheck current state; flag overdue')

card(70,330,300,150,'People & interface','ShiftFix web app',['React + TypeScript','Reporter · Worker','Manager · Admin'],'#d26b30','UI')
card(470,330,300,150,'Identity','Amazon Cognito',['Email verification + sign-in','Groups establish authority'],'#bd456d','ID')
card(870,330,340,150,'HTTPS entry point','API Gateway',['HTTP API + JWT authorizer','Public static / protected data'],'#8762b7','↗')
card(1310,330,400,150,'Frontend delivery','Static Lambda',['Compiled app + hashed assets','HTTPS served through API Gateway'],'#d77422','λ')
card(70,590,300,160,'Evidence storage','Amazon S3',['Private fault + repair images','Signed access; validated files','5 MiB per image · 5 per report'],'#32876c','S3')
card(470,590,300,160,'Onboarding','Auth Lambda',['Verified account group setup','Admin owner / Reporter default'],'#d77422','λ')
card(870,590,340,160,'Business rules','API Lambda',['Role + ownership checks','Review, assignment, verification','Versions + retry idempotency'],'#d77422','λ')
card(1310,590,400,160,'Maintiny assistant','Assistant Lambda',['Allowlisted tools + access checks','Search, drafts and private history','Explicit confirmation before creation'],'#d77422','λ')
card(70,870,300,170,'Preventive maintenance','Scheduled planning',['EventBridge Scheduler: hourly','Planning Lambda checks due plans','Creates review requests once'],'#a15488','◷')
card(470,870,740,170,'System of record','Amazon DynamoDB · on-demand',['Work orders · audit activity · assets · inventory · profiles','Private conversations · idempotency records · timer outbox','Conditional transactions keep state, history and timers consistent.'],'#3576b8','DB',fill='#f2f8ff')
card(1310,870,400,170,'Temporary external provider','Gemini API',['Fictional demo records only','Bedrock adapter implemented;','account model access restricted.'],'#8353b7','AI',fill='#f8f3fd')
card(70,1140,300,170,'Durable deadline path','DynamoDB Streams',['Committed timer-outbox records','INSERT events with TIMER# keys'],'#3576b8','≋')
card(470,1140,300,170,'Event dispatch','Dispatcher Lambda',['Native stream event mapping','Deterministic execution name'],'#d77422','λ')
card(870,1140,340,170,'Durable wait','AWS Step Functions',['Standard state machine','Wait until deadline → check','No Lambda running during wait'],'#b24f91','⋈')
card(1310,1140,400,170,'Version-aware follow-up','Deadline Lambda',['Check deadline version + status','Ignore completed / superseded work','Update current work if overdue'],'#d77422','λ')
text(70,1374,'CORE RELIABILITY PATTERN',13,'#2c586c',700)
text(330,1374,'Conditional business update  +  audit event  +  durable, version-checked follow-up',20,'#183747',600)

rect(40,1460,1720,112,'#e9eff5',r=18)
for x,title,desc in [(70,'CloudFormation','Manual IaC deployments'),(410,'IAM','Scoped service roles'),(750,'CloudWatch','Application + API logs'),(1090,'Amazon SQS','Async failure destinations'),(1430,'Deployment model','On-demand compute')]:
 service={'CloudFormation':'AWS-CloudFormation','IAM':'AWS-Identity-and-Access-Management','CloudWatch':'Amazon-CloudWatch','Amazon SQS':'Amazon-Simple-Queue-Service'}.get(title)
 if service:
  aws_icon(x,1484,46,service)
  text(x+58,1500,title,18,'#183747',700);text(x+58,1528,desc,13,'#526b80')
 else:
  text(x,1497,title,18,'#183747',700);text(x,1528,desc,15,'#526b80')
text(60,1610,'Solid: application / event flow     Dashed: identity validation, signed access or external model call',14,'#607488')
text(60,1638,'Service and resource icons: official AWS Architecture Icons, July 2026. ShiftFix factory mark: original artwork.',12,'#607488')
text(1740,1610,'github.com/Shizzzzoo/shiftfix',14,'#607488',500,'end')
s.append('</svg>')
svg='\n'.join(s)
OUT.mkdir(exist_ok=True,parents=True)
(OUT/'shiftfix-architecture-hq.svg').write_text(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/'shiftfix-architecture-hq.png'),output_width=W*2,output_height=H*2)
logo_svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 108 108">{logo_mark}</svg>'
cairosvg.svg2png(bytestring=logo_svg.encode(),write_to=str(OUT/'shiftfix-factory-logo.png'),output_width=1024,output_height=1024)
print('Rendered 3600 x 3300 PNG and editable SVG.')
