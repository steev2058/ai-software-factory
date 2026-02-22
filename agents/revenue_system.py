#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path('/srv/ai-software-factory')
RESEARCH_DIR = ROOT / 'research'
REPORTS_DIR = ROOT / 'reports'
PROJECTS_DIR = ROOT / 'projects'
QUEUE_FILE = RESEARCH_DIR / 'build-queue.json'
AGENT_LOG = REPORTS_DIR / 'agent-actions.jsonl'

MONEY_CATEGORIES = [
    'ATS CV / cover letter / LinkedIn (job seekers)',
    'Fiverr/Upwork gig optimizer (freelancers)',
    'Exam quiz generator + summary (students)',
    'Arabic caption/ad copy generator (small businesses)',
    'PDF-to-notes + action items (professionals)',
]


def now_iso(): return dt.datetime.now(dt.timezone.utc).isoformat()
def today_str(): return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')


def ensure_dirs():
    for d in [RESEARCH_DIR, REPORTS_DIR, PROJECTS_DIR, ROOT / 'agents']:
        d.mkdir(parents=True, exist_ok=True)


def load_env() -> Dict[str, str]:
    env = {}
    p = ROOT / '.env'
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    env.update({k: os.environ[k] for k in os.environ if k not in env})
    return env


def log_action(agent: str, action: str, result: Dict[str, Any]):
    ensure_dirs()
    with AGENT_LOG.open('a') as f:
        f.write(json.dumps({'ts': now_iso(), 'agent': agent, 'action': action, 'result': result}, ensure_ascii=False) + '\n')


def telegram_send(env: Dict[str, str], text: str):
    token = env.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = env.get('TELEGRAM_TARGET_CHAT_ID', '564358288')
    if not token:
        return
    requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={'chat_id': int(chat_id), 'text': text[:3900]}, timeout=20)


def openrouter_chat(env: Dict[str, str], system: str, user: str) -> str:
    key = env.get('OPENROUTER_API_KEY', '')
    if not key:
        return ''
    base = env.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    model = env.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    r = requests.post(
        f'{base}/chat/completions',
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json={'model': model, 'temperature': 0.25, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]},
        timeout=90,
    )
    if not r.ok:
        return ''
    return (((r.json().get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()


def slugify(s: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:40] or f'tool-{int(dt.datetime.now().timestamp())}'


def read_json(p: Path, default):
    if not p.exists(): return default
    try: return json.loads(p.read_text())
    except Exception: return default


def write_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def score_idea(idea: Dict[str, Any]) -> Dict[str, int]:
    text = json.dumps(idea, ensure_ascii=False).lower()
    instant = 30 if any(x in text for x in ['instant', '< 30', 'seconds', '30 seconds', 'one click']) else 18
    willingness = 25 if 'instant payoff' in text else 14
    simplicity = 20 if str(idea.get('build_complexity', '')).upper() == 'LOW' else 8
    viral = 15 if len(idea.get('keywords', [])) >= 5 else 8
    syria = 10 if any(ch in idea.get('marketing_channels', []) for ch in ['Syria FB groups', 'Telegram']) else 4
    total = instant + willingness + simplicity + viral + syria
    return {'instant_payoff': instant, 'willingness_1usd': willingness, 'build_simplicity': simplicity, 'viral_shareability': viral, 'syria_fit': syria, 'total': total}


# Agent 1

def fallback_ideas() -> List[Dict[str, Any]]:
    return [
        {
            'project_id': 'ats-keyword-gap-checker', 'tool_name': 'ATS Keyword Gap Checker',
            'one_sentence_promise': 'Find missing ATS keywords in under 30 seconds',
            'target_user': 'Job seekers', 'user_intent': 'Optimize CV for a specific job now',
            'input_fields': ['CV text', 'Job title', 'Job description'],
            'output_fields': ['ATS score', 'Missing keywords', 'Improved summary', '3 improved bullets', 'Top 5 fixes'],
            'why_pay_1_dollar': 'instant payoff', 'build_complexity': 'LOW',
            'marketing_channels': ['Syria FB groups', 'Telegram', 'LinkedIn'],
            'keywords': ['ATS', 'resume', 'CV', 'job', 'keywords'],
            'sample_input': {'cv': 'Node.js developer...', 'job_title': 'Backend Engineer', 'jd': 'Need Node, SQL, AWS'},
            'sample_output_outline': ['Score', 'Missing list', 'Summary rewrite', 'Bullet rewrite', 'Checklist'],
        },
        {
            'project_id': 'upwork-proposal-opener', 'tool_name': 'Upwork Proposal Opener',
            'one_sentence_promise': 'Write a stronger first paragraph for gigs instantly',
            'target_user': 'Freelancers', 'user_intent': 'Send a better proposal intro now',
            'input_fields': ['Gig post', 'Your skill', 'Client pain point'],
            'output_fields': ['Hook line', 'Opening paragraph', 'Proof sentence', 'CTA line'],
            'why_pay_1_dollar': 'instant payoff', 'build_complexity': 'LOW',
            'marketing_channels': ['Telegram', 'Reddit', 'Syria FB groups'],
            'keywords': ['upwork', 'proposal', 'freelance', 'gig', 'client'],
            'sample_input': {'gig': 'Need Shopify speed fix', 'skill': 'Shopify', 'pain': 'slow store'},
            'sample_output_outline': ['Hook', 'Intro', 'Credibility', 'CTA'],
        },
        {
            'project_id': 'exam-quiz-fastmaker', 'tool_name': 'Exam Quiz FastMaker',
            'one_sentence_promise': 'Turn notes into quiz questions in one click',
            'target_user': 'Students', 'user_intent': 'Create revision quiz from notes now',
            'input_fields': ['Notes text', 'Exam subject', 'Difficulty'],
            'output_fields': ['10 MCQs', 'Answer key', 'Weak topics', 'Quick summary'],
            'why_pay_1_dollar': 'instant payoff', 'build_complexity': 'LOW',
            'marketing_channels': ['Telegram', 'Syria FB groups', 'LinkedIn'],
            'keywords': ['exam', 'quiz', 'study', 'notes', 'students'],
            'sample_input': {'notes': 'Photosynthesis...', 'subject': 'Biology', 'difficulty': 'medium'},
            'sample_output_outline': ['Questions', 'Answers', 'Weak areas', 'Summary'],
        },
        {
            'project_id': 'arabic-ad-caption-spark', 'tool_name': 'Arabic Ad Caption Spark',
            'one_sentence_promise': 'Generate high-converting Arabic ad captions instantly',
            'target_user': 'Small businesses', 'user_intent': 'Publish a better social ad now',
            'input_fields': ['Product', 'Audience', 'Offer'],
            'output_fields': ['5 captions', 'CTA options', 'Hashtags', 'Variant tone'],
            'why_pay_1_dollar': 'instant payoff', 'build_complexity': 'LOW',
            'marketing_channels': ['Syria FB groups', 'Telegram', 'LinkedIn'],
            'keywords': ['arabic ads', 'captions', 'small business', 'facebook', 'cta'],
            'sample_input': {'product': 'Perfume', 'audience': 'Women 20-35', 'offer': '20% off'},
            'sample_output_outline': ['Captions', 'CTAs', 'Hashtags', 'Tones'],
        },
        {
            'project_id': 'pdf-action-notes-extract', 'tool_name': 'PDF Action Notes Extractor',
            'one_sentence_promise': 'Extract actionable notes from long text in seconds',
            'target_user': 'Professionals', 'user_intent': 'Get action items from document now',
            'input_fields': ['Document text', 'Context', 'Priority mode'],
            'output_fields': ['Key notes', 'Action items', 'Deadlines', 'Owner suggestions'],
            'why_pay_1_dollar': 'instant payoff', 'build_complexity': 'LOW',
            'marketing_channels': ['LinkedIn', 'Reddit', 'Telegram'],
            'keywords': ['pdf notes', 'action items', 'summary', 'productivity', 'work'],
            'sample_input': {'text': 'Meeting notes...', 'context': 'Sprint planning', 'priority': 'high'},
            'sample_output_outline': ['Notes', 'Actions', 'Deadlines', 'Owners'],
        },
    ]


def niche_research(env: Dict[str, str]):
    ensure_dirs()
    day = today_str()
    out_file = RESEARCH_DIR / f'ideas-{day}.json'

    sys = 'Return STRICT JSON array with exactly 10 ideas. No markdown.'
    usr = (
        'Generate 10 HIGH-CONVERTING micro-tool ideas/day only from these money categories: ' + ', '.join(MONEY_CATEGORIES) + '. '
        'Each item fields exactly: project_id(kebab-case),tool_name,one_sentence_promise(max12words),target_user,user_intent,input_fields(max3),output_fields(max5),why_pay_1_dollar(build instant payoff),build_complexity(LOW),marketing_channels(choose only Syria FB groups|Telegram|Reddit|LinkedIn),keywords(5),sample_input,sample_output_outline. '
        'Hard constraints: buildable in 1 day, single page tool, value <30 seconds, no accounts, no scraping, no marketplaces, no long workflows.'
    )
    raw = openrouter_chat(env, sys, usr)
    try:
        ideas = json.loads(raw)
    except Exception:
        ideas = fallback_ideas() * 2
        ideas = ideas[:10]

    normalized = []
    for idx, it in enumerate(ideas[:10], start=1):
        it = dict(it)
        it['project_id'] = slugify(it.get('project_id') or it.get('tool_name') or f'micro-tool-{idx}')
        it['build_complexity'] = 'LOW'
        it['why_pay_1_dollar'] = 'instant payoff'
        it['input_fields'] = (it.get('input_fields') or [])[:3]
        it['output_fields'] = (it.get('output_fields') or [])[:5]
        it['keywords'] = (it.get('keywords') or [])[:5]
        it['marketing_channels'] = [c for c in (it.get('marketing_channels') or []) if c in ['Syria FB groups', 'Telegram', 'Reddit', 'LinkedIn']]
        if not it['marketing_channels']:
            it['marketing_channels'] = ['Telegram', 'Syria FB groups']
        score = score_idea(it)
        it['score_breakdown'] = score
        it['score'] = score['total']
        normalized.append(it)

    queued = [i for i in normalized if i.get('score', 0) >= 75]
    queue = {'date': day, 'version': 2, 'rules': {'min_score': 75}, 'items': []}
    for q in queued:
        queue['items'].append({'status': 'approved', 'created_at': now_iso(), 'score': q['score'], 'idea': q})

    write_json(out_file, {'date': day, 'ideas': normalized, 'queued_count': len(queued)})
    write_json(QUEUE_FILE, queue)

    top5 = sorted(normalized, key=lambda x: x.get('score', 0), reverse=True)[:5]
    msg = ['🧠 Micro-tool Research (Top 5, filtered for $1 fast conversion)']
    for i, t in enumerate(top5, 1):
        msg.append(f"{i}) {t['project_id']} ({t['score']})\n{t.get('one_sentence_promise')}")
    telegram_send(env, '\n\n'.join(msg))
    log_action('agent1_niche_research', 'run', {'ideas_file': str(out_file), 'generated': len(normalized), 'queued': len(queued)})


# Agent 2

def render_tool_server_js(project_name: str, input_fields: List[str], output_fields: List[str]) -> str:
    return f'''const express=require('express');const cors=require('cors');const Database=require('better-sqlite3');const path=require('path');require('dotenv').config();
const app=express();const PORT=Number(process.env.PORT||3000);const ADMIN_TOKEN=process.env.ADMIN_TOKEN||'';const OPENROUTER_API_KEY=process.env.OPENROUTER_API_KEY||'';const OPENROUTER_MODEL=process.env.OPENROUTER_MODEL||'openai/gpt-4o-mini';
app.use(cors());app.use(express.json({{limit:'1mb'}}));
const db=new Database(path.join(__dirname,'data.sqlite'));db.exec(`CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY,free_date TEXT,free_used INTEGER DEFAULT 0,paid_credits INTEGER DEFAULT 0,updated_at TEXT);CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY AUTOINCREMENT,provider TEXT,provider_ref TEXT UNIQUE,status TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS grants(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,credits INTEGER,note TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT,user_id TEXT,meta_json TEXT,created_at TEXT);`);
const gu=db.prepare('SELECT * FROM users WHERE user_id=?');const uu=db.prepare(`INSERT INTO users(user_id,free_date,free_used,paid_credits,updated_at) VALUES(@user_id,@free_date,@free_used,@paid_credits,@updated_at) ON CONFLICT(user_id) DO UPDATE SET free_date=excluded.free_date,free_used=excluded.free_used,paid_credits=excluded.paid_credits,updated_at=excluded.updated_at`);
const n=()=>new Date().toISOString();const d=()=>new Date().toISOString().slice(0,10);const norm=(x)=>String(x||'').trim();const evt=(t,u,m)=>db.prepare('INSERT INTO events(type,user_id,meta_json,created_at) VALUES(?,?,?,?)').run(t,norm(u)||null,JSON.stringify(m||{{}}),n());
function ensure(u){{u=norm(u);if(!u)return null;let r=gu.get(u);if(!r){{r={{user_id:u,free_date:d(),free_used:0,paid_credits:0,updated_at:n()}};uu.run(r);}}if(r.free_date!==d()){{r.free_date=d();r.free_used=0;r.updated_at=n();uu.run(r);}}return r;}}
function credits(r){{const freeLeft=Math.max(0,3-(r.free_used||0));const paid=Math.max(0,r.paid_credits||0);return {{freeLeft,paid,total:freeLeft+paid}};}}
app.get('/health',(_q,s)=>s.json({{ok:true,service:'{project_name}'}}));
app.get('/',(q,s)=>{{evt('page_view',q.query?.user||null,{{}});s.sendFile(path.join(__dirname,'public','index.html'));}});app.use(express.static(path.join(__dirname,'public')));
app.get('/api/credits',(q,s)=>{{const u=norm(q.query.user);if(!u)return s.status(400).json({{error:'user is required'}});const r=ensure(u);s.json({{user_id:u,...credits(r),freeDailyLimit:3,paidPackCredits:100}});}});
app.post('/api/use',async(q,s)=>{{const u=norm(q.body?.user_id);if(!u)return s.status(400).json({{error:'user_id is required'}});const payload={{ {', '.join([f"'{f}': String(q.body?.{slugify(f).replace('-','_')}||'')" for f in input_fields])} }};const r=ensure(u);let mode='';if((r.free_used||0)<3){{r.free_used+=1;mode='free';}}else if((r.paid_credits||0)>0){{r.paid_credits-=1;mode='paid';}}else return s.status(402).json({{error:'insufficient_credits',message:'Top up required'}});r.updated_at=n();uu.run(r);
let result='';const sections={json.dumps(output_fields)};if(OPENROUTER_API_KEY){{try{{const prompt=`You are a micro-tool engine. Input JSON: ${{JSON.stringify(payload)}}. Return plain text with sections exactly: ${{sections.join(', ')}}`;const rr=await fetch((process.env.OPENROUTER_BASE_URL||'https://openrouter.ai/api/v1')+'/chat/completions',{{method:'POST',headers:{{Authorization:`Bearer ${{OPENROUTER_API_KEY}}`,'Content-Type':'application/json'}},body:JSON.stringify({{model:OPENROUTER_MODEL,messages:[{{role:'system',content:'Fast practical output.'}},{{role:'user',content:prompt}}],temperature:.2}})}});const jd=await rr.json();result=jd?.choices?.[0]?.message?.content||'';}}catch{{}}}}
if(!result){{result=sections.map((x,i)=>`${{i+1}}) ${{x}}:\n- Quick output based on your input`).join('\n\n');}}
evt('use',u,{{mode}});s.json({{ok:true,used:mode,credits:credits(r),result}});}});
app.post('/api/unlock/local',(q,s)=>{{const a=q.headers['authorization']||'';const tok=a.startsWith('Bearer ')?a.slice(7):String(q.body?.admin_token||'');if(!ADMIN_TOKEN||tok!==ADMIN_TOKEN)return s.status(401).json({{error:'unauthorized'}});const u=norm(q.body?.user_id);const c=Math.max(0,Number(q.body?.credits||100));const note=String(q.body?.note||'').slice(0,500);if(!u)return s.status(400).json({{error:'user_id is required'}});const r=ensure(u);r.paid_credits+=c;r.updated_at=n();uu.run(r);db.prepare('INSERT INTO grants(user_id,credits,note,created_at) VALUES(?,?,?,?)').run(u,c,note,n());evt('local_grant',u,{{credits:c,note}});s.json({{ok:true,user_id:u,credited:c,credits:credits(r)}});}});
app.get('/admin/stats',(q,s)=>{{if(!ADMIN_TOKEN||String(q.query.token||'')!==ADMIN_TOKEN)return s.status(401).json({{error:'unauthorized'}});const dau=db.prepare("SELECT COUNT(DISTINCT user_id) n FROM events WHERE date(created_at)=date('now') AND user_id IS NOT NULL AND user_id<>''").get().n||0;const uses=db.prepare("SELECT COUNT(*) n FROM events WHERE type='use' AND date(created_at)=date('now')").get().n||0;const pt=db.prepare("SELECT COUNT(*) n FROM purchases WHERE status='credited' AND date(created_at)=date('now')").get().n||0;const gt=db.prepare("SELECT COUNT(*) n FROM grants WHERE date(created_at)=date('now')").get().n||0;s.json({{dau_today:dau,uses_today:uses,purchases:{{total:0,today:pt}},local_grants:{{total:0,today:gt}}}});}});
app.listen(PORT,()=>console.log('running',PORT));'''


def render_tool_ui_html(idea: Dict[str, Any]) -> str:
    ins = idea.get('input_fields', [])
    promise = idea.get('one_sentence_promise', 'Get instant result.')
    title = idea.get('tool_name', idea.get('project_id'))
    # map ids
    fields = []
    for f in ins:
        fid = slugify(f).replace('-', '_')
        fields.append((f, fid))
    field_html = '\n'.join([f'<label class="small">{n}</label><textarea id="{fid}" rows="3" placeholder="{n}..."></textarea>' for n, fid in fields])
    payload = ','.join([f"{fid}:document.getElementById('{fid}').value" for _, fid in fields])
    sample = idea.get('sample_input') or {}
    sample_js = '\n'.join([f"document.getElementById('{slugify(k).replace('-', '_')}') && (document.getElementById('{slugify(k).replace('-', '_')}').value={json.dumps(str(v))});" for k, v in sample.items()])
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>body{{font-family:Inter,system-ui;background:#f5f7fb;margin:0}}.w{{max-width:760px;margin:24px auto;padding:0 14px}}.c{{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:16px}}textarea{{width:100%;border:1px solid #e2e8f0;border-radius:10px;padding:10px}}.row{{display:flex;gap:8px;flex-wrap:wrap}}button{{padding:10px 14px;border-radius:9px;border:0;background:#2563eb;color:#fff}}button.alt{{background:#fff;color:#0f172a;border:1px solid #e2e8f0}}.out{{margin-top:12px;border:1px solid #e2e8f0;border-radius:12px;padding:12px;white-space:pre-wrap;position:relative}}.blur{{filter:blur(5px)}}.ov{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.6);font-weight:700}}.hide{{display:none}}</style></head><body><div class="w"><div class="c"><h2>{title}</h2><p>{promise}</p>{field_html}<div class="row" style="margin-top:10px"><button id="go" onclick="run()">Generate</button><button class="alt" onclick="fillSample()">Sample input</button></div><p>Free uses left today: <b id="freeLeft">-</b> | Paid credits: <b id="paidCredits">-</b></p><div id="out" class="out">Output preview will appear here.<div id="ov" class="ov hide">Unlock full result for $1</div></div></div></div><script>const k='micro_saas_user_id';let uid=localStorage.getItem(k);if(!uid){{uid='u_'+Math.random().toString(36).slice(2,10);localStorage.setItem(k,uid)}}let last='';async function load(){{const r=await fetch('/api/credits?user='+encodeURIComponent(uid));const d=await r.json();freeLeft.textContent=d.freeLeft;paidCredits.textContent=d.paid;return d;}}function fillSample(){{{sample_js}}}async function run(){{const b=document.getElementById('go');b.disabled=true;const payload={{user_id:uid,{payload}}};const r=await fetch('/api/use',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(payload)}});const d=await r.json();if(!r.ok&&d.error==='insufficient_credits'){{out.textContent=(last||'Preview: quick result...').slice(0,280)+'...';out.classList.add('blur');ov.classList.remove('hide');await load();b.disabled=false;return;}}last=d.result||'';out.textContent=last||'Done';out.classList.remove('blur');ov.classList.add('hide');if(d.credits){{freeLeft.textContent=d.credits.freeLeft;paidCredits.textContent=d.credits.paid;}}b.disabled=false;}}load();</script></body></html>'''


def build_project_from_idea(env: Dict[str, str], idea: Dict[str, Any]) -> Dict[str, Any]:
    project_id = slugify(idea.get('project_id') or idea.get('tool_name') or 'micro-tool')
    base = project_id
    n = 2
    while (PROJECTS_DIR / project_id).exists():
        project_id = f'{base}-{n}'; n += 1

    subprocess.run([str(ROOT / 'scripts' / 'monetize_project.sh'), project_id], check=True)

    pdir = PROJECTS_DIR / project_id
    (pdir / 'project_spec.md').write_text(
        f"# {idea.get('tool_name')}\n\nPromise: {idea.get('one_sentence_promise')}\n\nIntent: {idea.get('user_intent')}\n\nInput fields: {idea.get('input_fields')}\nOutput fields: {idea.get('output_fields')}\n"
    )
    write_json(pdir / 'state' / 'spec.json', {'stack': 'nextjs', 'idea': idea})

    (pdir / 'server.js').write_text(render_tool_server_js(project_id, idea.get('input_fields', []), idea.get('output_fields', [])))
    (pdir / 'public' / 'index.html').write_text(render_tool_ui_html(idea))

    # keep factory /run hook for compatibility
    try:
        requests.post(f"http://127.0.0.1:5680/api/projects/{project_id}/run", auth=(env.get('DASHBOARD_USER', 'admin'), env.get('DASHBOARD_PASS', '')), timeout=20)
    except Exception:
        pass

    subprocess.run([str(ROOT / 'scripts' / 'deploy_project.sh'), project_id], check=True)
    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    url = (reg.get(project_id) or {}).get('url', f'https://{project_id}.petsy.company')
    log_action('agent2_product_builder', 'build_deploy', {'project_id': project_id, 'url': url})
    return {'project_id': project_id, 'url': url}


def product_builder(env: Dict[str, str]):
    q = read_json(QUEUE_FILE, {'items': []})
    idx = next((i for i, it in enumerate(q.get('items', [])) if it.get('status') in ('approved', 'new')), None)
    if idx is None:
        log_action('agent2_product_builder', 'skip', {'reason': 'queue_empty'})
        return {'status': 'skip'}
    idea = q['items'][idx]['idea']
    built = build_project_from_idea(env, idea)
    q['items'][idx].update({'status': 'built', 'built_at': now_iso(), 'project_id': built['project_id'], 'url': built['url']})
    write_json(QUEUE_FILE, q)
    marketing_assets(env, built['project_id'])
    telegram_send(env, f"🏗️ Built {built['project_id']}\n{built['url']}")
    return built


# Agent 3

def marketing_assets(env: Dict[str, str], project_id: str):
    pdir = PROJECTS_DIR / project_id
    mdir = pdir / 'marketing'
    mdir.mkdir(parents=True, exist_ok=True)
    spec = (pdir / 'project_spec.md').read_text() if (pdir / 'project_spec.md').exists() else project_id
    raw = openrouter_chat(
        env,
        'Return strict JSON only. Value-first tone, no hard selling.',
        f"Create marketing for:\n{spec}\nReturn keys: syria_fb_post_1,syria_fb_post_2,reddit_post_feedback,linkedin_post,comment_replies_ar(array5),dm_scripts_ar(array5)",
    )
    try:
        d = json.loads(raw)
    except Exception:
        d = {
            'syria_fb_post_1': f"أداة {project_id} تعطي نتيجة فورية خلال ثواني. شاركوني رأيكم بأفضل استخدام.",
            'syria_fb_post_2': f"إذا بدك نتيجة سريعة بدون تعقيد، جرّب {project_id} وقلّي شو بتحب نطوّر.",
            'reddit_post_feedback': f"Built {project_id} to solve one urgent task in under 30s. Looking for product feedback.",
            'linkedin_post': f"Launched {project_id}: a single-action micro-tool designed for immediate value.",
            'comment_replies_ar': ["ممتاز، جربها وقلي شو النتيجة."] * 5,
            'dm_scripts_ar': ["مرحباً! عملنا أداة سريعة لمشكلتك، إذا بتحب ابعتلك الرابط."] * 5,
        }

    files = {
        'syria_fb_post_1.txt': d.get('syria_fb_post_1', ''),
        'syria_fb_post_2.txt': d.get('syria_fb_post_2', ''),
        'reddit_post.txt': d.get('reddit_post_feedback', ''),
        'linkedin_post.txt': d.get('linkedin_post', ''),
        'comment_replies_ar.txt': '\n\n'.join((d.get('comment_replies_ar') or [])[:5]),
        'dm_scripts_ar.txt': '\n\n'.join((d.get('dm_scripts_ar') or [])[:5]),
    }
    for fn, c in files.items():
        if isinstance(c, (dict, list)):
            c = json.dumps(c, ensure_ascii=False, indent=2)
        (mdir / fn).write_text(str(c))

    fb_preview = str(files.get('syria_fb_post_1.txt', ''))[:600]
    reddit_preview = str(files.get('reddit_post.txt', ''))[:600]
    telegram_send(env, f"📣 Marketing queue for {project_id}\n\nFB#1:\n{fb_preview}\n\nReddit:\n{reddit_preview}")
    log_action('agent3_marketing', 'generate', {'project_id': project_id, 'files': list(files.keys())})


# Agent 4

def analytics(env: Dict[str, str]):
    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    token = env.get('ADMIN_TOKEN', '')
    rows = []
    total_rev = 0
    for pid, meta in reg.items():
        url = (meta or {}).get('url', f'https://{pid}.petsy.company')
        d = {}
        try:
            r = requests.get(f'{url}/admin/stats', params={'token': token}, timeout=20)
            if r.ok: d = r.json()
        except Exception:
            pass
        uses = int(d.get('uses_today') or 0)
        purchases = int(((d.get('purchases') or {}).get('today') or 0))
        conv = round((purchases / uses * 100), 2) if uses else 0.0
        total_rev += purchases
        rows.append({'project_id': pid, 'url': url, 'dau_today': int(d.get('dau_today') or 0), 'uses_today': uses, 'purchases_today': purchases, 'conversion_rate': conv})
    rows.sort(key=lambda x: (x['purchases_today'], x['uses_today']), reverse=True)
    out = REPORTS_DIR / f'metrics-{today_str()}.json'
    write_json(out, {'date': today_str(), 'projects': rows, 'estimated_revenue_today_usd': total_rev})
    top = rows[0]['project_id'] if rows else 'n/a'
    low = [r['project_id'] for r in rows if r['uses_today'] < 10][:5]
    telegram_send(env, f"📊 Metrics\nTop: {top}\nLow: {', '.join(low) if low else 'none'}\nRevenue today est: ${total_rev}")
    log_action('agent4_analytics', 'run', {'file': str(out), 'projects': len(rows)})


# Agent 5

def optimization(env: Dict[str, str]):
    metrics = read_json(REPORTS_DIR / f'metrics-{today_str()}.json', {'projects': []})
    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    q = read_json(QUEUE_FILE, {'date': today_str(), 'version': 2, 'rules': {'min_score': 75}, 'items': []})
    decisions = []

    for p in metrics.get('projects', []):
        pid = p['project_id']
        updated = (reg.get(pid) or {}).get('updated_at')
        age_hours = 0
        if updated:
            try:
                age_hours = int((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(updated.replace('Z', '+00:00'))).total_seconds() / 3600)
            except Exception:
                pass

        status = None
        if age_hours >= 48 and int(p.get('dau_today', 0)) < 5 and int(p.get('purchases_today', 0)) == 0:
            status = 'ARCHIVE_CANDIDATE'
            (PROJECTS_DIR / pid / 'ARCHIVE_CANDIDATE').write_text(now_iso())
        elif p.get('conversion_rate', 0) > 3:
            status = 'WINNER'
            for i in [1, 2]:
                q['items'].append({
                    'status': 'approved', 'created_at': now_iso(), 'score': 80,
                    'idea': {
                        'project_id': f'{pid}-v{i}', 'tool_name': f'{pid} Variant {i}',
                        'one_sentence_promise': 'Instant result for a tighter audience',
                        'target_user': f'Variant audience {i}', 'user_intent': 'Get result now',
                        'input_fields': ['Input A', 'Input B'], 'output_fields': ['Result', 'Fixes'],
                        'why_pay_1_dollar': 'instant payoff', 'build_complexity': 'LOW',
                        'marketing_channels': ['Telegram', 'Syria FB groups'], 'keywords': [pid, 'variant', 'instant', 'microtool', 'fast'],
                        'sample_input': {'a': 'x'}, 'sample_output_outline': ['result']
                    },
                    'source': 'winner_variant'
                })

        if status:
            decisions.append({'project_id': pid, 'status': status})

    write_json(QUEUE_FILE, q)
    out = REPORTS_DIR / f'optimization-{today_str()}.json'
    write_json(out, {'date': today_str(), 'decisions': decisions})
    telegram_send(env, f"🧪 Optimization\n" + ('\n'.join([f"- {d['project_id']}: {d['status']}" for d in decisions]) or 'No actions'))
    log_action('agent5_optimization', 'run', {'file': str(out), 'decisions': decisions})


# Agent 6

def revenue(env: Dict[str, str]):
    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    total_purchases = 0
    total_local = 0
    best, best_p = None, -1
    for pid in reg.keys():
        dbp = PROJECTS_DIR / pid / 'data.sqlite'
        if not dbp.exists():
            continue
        try:
            con = sqlite3.connect(str(dbp)); cur = con.cursor()
            p = int(cur.execute("select count(*) from purchases where status='credited'").fetchone()[0]) if cur.execute("select name from sqlite_master where type='table' and name='purchases'").fetchone() else 0
            g = int(cur.execute("select count(*) from grants").fetchone()[0]) if cur.execute("select name from sqlite_master where type='table' and name='grants'").fetchone() else 0
            con.close()
            total_purchases += p; total_local += g
            if p > best_p: best_p, best = p, pid
        except Exception:
            pass
    est = total_purchases * 1
    out = REPORTS_DIR / f'revenue-{today_str()}.md'
    out.write_text(f"# Revenue Report {today_str()}\n\n- Total purchases: {total_purchases}\n- Total local grants: {total_local}\n- Estimated revenue: ${est}\n- Best selling project: {best or 'n/a'}\n- Recommended focus niche: ATS/CV + Arabic ad copy micro-tools\n")
    telegram_send(env, f"💰 Revenue today\nEstimated ${est}\nBest seller: {best or 'n/a'}\nFocus: ATS + Arabic copy tools")
    log_action('agent6_revenue', 'run', {'file': str(out), 'estimated': est, 'best': best})


def main():
    ensure_dirs()
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('niche-research')
    sub.add_parser('product-builder')
    m = sub.add_parser('marketing'); m.add_argument('--project-id', required=True)
    sub.add_parser('analytics'); sub.add_parser('optimization'); sub.add_parser('revenue')
    args = parser.parse_args(); env = load_env()

    if args.cmd == 'niche-research': niche_research(env)
    elif args.cmd == 'product-builder': product_builder(env)
    elif args.cmd == 'marketing': marketing_assets(env, args.project_id)
    elif args.cmd == 'analytics': analytics(env)
    elif args.cmd == 'optimization': optimization(env)
    elif args.cmd == 'revenue': revenue(env)


if __name__ == '__main__':
    main()
