#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path('/srv/ai-software-factory')
RESEARCH_DIR = ROOT / 'research'
REPORTS_DIR = ROOT / 'reports'
PROJECTS_DIR = ROOT / 'projects'
WORKFLOWS_DIR = ROOT / 'workflows' / 'n8n'
QUEUE_FILE = RESEARCH_DIR / 'build-queue.json'
AGENT_LOG = REPORTS_DIR / 'agent-actions.jsonl'


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def today_str():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')


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
    env.update({k: os.environ[k] for k in os.environ.keys() if k not in env})
    return env


def log_action(agent: str, action: str, result: Dict[str, Any]):
    ensure_dirs()
    row = {'ts': now_iso(), 'agent': agent, 'action': action, 'result': result}
    with AGENT_LOG.open('a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def telegram_send(env: Dict[str, str], text: str):
    token = env.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = env.get('TELEGRAM_TARGET_CHAT_ID', '564358288')
    if not token:
        log_action('system', 'telegram_skip', {'reason': 'token_missing'})
        return
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    requests.post(url, json={'chat_id': int(chat_id), 'text': text[:3900]}, timeout=20)


def openrouter_chat(env: Dict[str, str], system: str, user: str, model: str = None) -> str:
    key = env.get('OPENROUTER_API_KEY', '')
    base = env.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    model = model or env.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    if not key:
        return ''
    r = requests.post(
        f'{base}/chat/completions',
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json={
            'model': model,
            'temperature': 0.3,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
        },
        timeout=60,
    )
    if not r.ok:
        return ''
    return (r.json().get('choices') or [{}])[0].get('message', {}).get('content', '') or ''


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:40] or f'tool-{int(dt.datetime.now().timestamp())}'


def read_json(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def write_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# Agent 1

def niche_research(env: Dict[str, str]):
    ensure_dirs()
    day = today_str()
    out = RESEARCH_DIR / f'ideas-{day}.json'

    system = 'Return STRICT JSON array with exactly 5 objects. No markdown.'
    user = (
        'Generate 5 micro-SaaS ideas for: job seekers, freelancers, students, Arabic market, global remote workers. '
        'Each item fields: tool_name,target_user,problem_solved,why_pay_1usd,marketing_keywords(array),spec_hint.'
    )
    txt = openrouter_chat(env, system, user)
    ideas = []
    try:
        ideas = json.loads(txt)
    except Exception:
        ideas = [
            {
                'tool_name': 'ATS CV Checker',
                'target_user': 'Job seekers',
                'problem_solved': 'CVs fail ATS filters and never get interviews',
                'why_pay_1usd': 'Instant practical score + fixes before applying',
                'marketing_keywords': ['ATS', 'CV', 'resume', 'job application'],
                'spec_hint': 'input CV + job title + JD, output score + fixes',
            },
            {
                'tool_name': 'Freelance Proposal Polisher',
                'target_user': 'Freelancers',
                'problem_solved': 'Low response rate to proposals',
                'why_pay_1usd': 'Higher close rate with tailored proposals',
                'marketing_keywords': ['Upwork', 'proposal', 'freelance clients'],
                'spec_hint': 'input gig + profile, output tailored proposal',
            },
            {
                'tool_name': 'Study Plan Sprint',
                'target_user': 'Students',
                'problem_solved': 'Unstructured studying and missed deadlines',
                'why_pay_1usd': 'Saves time and boosts exam confidence',
                'marketing_keywords': ['study plan', 'exam prep', 'students'],
                'spec_hint': 'input subjects/dates, output weekly plan',
            },
            {
                'tool_name': 'Arabic Invoice Generator',
                'target_user': 'Arabic freelancers',
                'problem_solved': 'Manual invoices waste time',
                'why_pay_1usd': 'Fast bilingual invoice docs for clients',
                'marketing_keywords': ['invoice', 'Arabic business', 'freelancer'],
                'spec_hint': 'input client/items, output invoice text',
            },
            {
                'tool_name': 'Remote Interview Simulator',
                'target_user': 'Global remote workers',
                'problem_solved': 'Poor interview readiness',
                'why_pay_1usd': 'Practice likely questions and improve answers',
                'marketing_keywords': ['remote jobs', 'interview prep', 'behavioral'],
                'spec_hint': 'input role/company, output mock Q&A',
            },
        ]

    ideas = ideas[:5]
    write_json(out, {'date': day, 'ideas': ideas})
    queue = read_json(QUEUE_FILE, {'items': []})
    for i in ideas:
        queue['items'].append({'status': 'new', 'created_at': now_iso(), 'idea': i})
    write_json(QUEUE_FILE, queue)

    top3 = ideas[:3]
    lines = ['🧠 Niche Research (Top 3)']
    for i, it in enumerate(top3, start=1):
        lines.append(f"{i}) {it.get('tool_name')} — {it.get('target_user')}\nWhy $1: {it.get('why_pay_1usd')}")
    telegram_send(env, '\n\n'.join(lines))
    log_action('agent1_niche_research', 'run', {'ideas_file': str(out), 'count': len(ideas)})


# Agent 2

def build_project_from_idea(env: Dict[str, str], idea: Dict[str, Any], auto_deploy=True) -> Dict[str, Any]:
    project_id = slugify(idea.get('tool_name', 'micro-tool'))
    # avoid collision
    base = project_id
    i = 2
    while (PROJECTS_DIR / project_id).exists():
        project_id = f'{base}-{i}'
        i += 1

    # /new equivalent
    (PROJECTS_DIR / project_id / 'tasks').mkdir(parents=True, exist_ok=True)
    (PROJECTS_DIR / project_id / 'state').mkdir(parents=True, exist_ok=True)
    (PROJECTS_DIR / project_id / 'repo').mkdir(parents=True, exist_ok=True)
    (PROJECTS_DIR / project_id / 'logs').mkdir(parents=True, exist_ok=True)

    # monetize template
    subprocess.run([str(ROOT / 'scripts' / 'monetize_project.sh'), project_id], check=True)

    # /spec equivalent
    spec = {
        'stack': 'nextjs',
        'prd': f"{idea.get('tool_name')}: {idea.get('problem_solved')}",
        'tasks': [
            {'title': 'Build core UI', 'description': 'Keep conversion-focused single page'},
            {'title': 'Connect monetization', 'description': 'Use existing credits/paywall'},
        ],
    }
    write_json(PROJECTS_DIR / project_id / 'state' / 'spec.json', spec)
    (PROJECTS_DIR / project_id / 'project_spec.md').write_text(
        f"# {idea.get('tool_name')}\n\nTarget: {idea.get('target_user')}\n\nProblem: {idea.get('problem_solved')}\n\nWhy pay $1: {idea.get('why_pay_1usd')}\n"
    )

    # /run equivalent (existing factory run hook)
    user = env.get('DASHBOARD_USER', 'admin')
    pw = env.get('DASHBOARD_PASS', '')
    try:
        requests.post(f'http://127.0.0.1:5680/api/projects/{project_id}/run', auth=(user, pw), timeout=20)
    except Exception:
        pass

    if auto_deploy:
        subprocess.run([str(ROOT / 'scripts' / 'deploy_project.sh'), project_id], check=True)

    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    url = (reg.get(project_id) or {}).get('url', f'https://{project_id}.petsy.company')
    result = {'project_id': project_id, 'url': url}
    log_action('agent2_product_builder', 'build_deploy', result)
    return result


def product_builder(env: Dict[str, str], auto_approve_top=True) -> Dict[str, Any]:
    q = read_json(QUEUE_FILE, {'items': []})
    pick_idx = None
    for idx, it in enumerate(q['items']):
        if it.get('status') in ('approved', 'new'):
            pick_idx = idx
            break
    if pick_idx is None:
        log_action('agent2_product_builder', 'skip', {'reason': 'queue_empty'})
        return {'status': 'skip'}

    if auto_approve_top and q['items'][pick_idx]['status'] == 'new':
        q['items'][pick_idx]['status'] = 'approved'

    idea = q['items'][pick_idx]['idea']
    built = build_project_from_idea(env, idea, auto_deploy=True)
    try:
        marketing_assets(env, built['project_id'])
    except Exception as e:
        log_action('agent2_product_builder', 'marketing_trigger_failed', {'project_id': built.get('project_id'), 'error': str(e)})
    q['items'][pick_idx]['status'] = 'built'
    q['items'][pick_idx]['project_id'] = built['project_id']
    q['items'][pick_idx]['url'] = built['url']
    q['items'][pick_idx]['built_at'] = now_iso()
    write_json(QUEUE_FILE, q)
    telegram_send(env, f"🏗️ Product built: {built['project_id']}\nURL: {built['url']}")
    return built


# Agent 3

def marketing_assets(env: Dict[str, str], project_id: str):
    pdir = PROJECTS_DIR / project_id
    mdir = pdir / 'marketing'
    mdir.mkdir(parents=True, exist_ok=True)
    spec = (pdir / 'project_spec.md').read_text() if (pdir / 'project_spec.md').exists() else project_id

    prompt = f"Generate concise marketing assets for this product:\n{spec}\nReturn JSON object with keys: reddit_post,x_thread,linkedin_post,arabic_fb_post,producthunt_blurb,headline,paywall_a,paywall_b"
    txt = openrouter_chat(env, 'Return strict JSON only.', prompt)
    try:
        data = json.loads(txt)
    except Exception:
        data = {
            'reddit_post': f"Built {project_id} to solve a specific pain point quickly. Looking for feedback.",
            'x_thread': f"1/ I launched {project_id}. It helps users get results in minutes.\n2/ Free 3/day.\n3/ $1 unlocks 100 credits.",
            'linkedin_post': f"We launched {project_id} as a focused micro-SaaS with instant value and simple pricing.",
            'arabic_fb_post': f"أطلقنا {project_id} لحل مشكلة محددة بسرعة. مجاني 3 مرات يوميًا ثم 1$ مقابل 100 رصيد.",
            'producthunt_blurb': f"{project_id}: focused micro-SaaS with immediate output and pay-as-you-go credits.",
            'headline': 'Get better results in minutes, not hours.',
            'paywall_a': 'Unlock 100 credits for just $1.',
            'paywall_b': 'Out of free uses? Continue instantly with 100 credits for $1.',
        }

    files = {
        'reddit_post.txt': data.get('reddit_post', ''),
        'x_thread.txt': data.get('x_thread', ''),
        'linkedin_post.txt': data.get('linkedin_post', ''),
        'arabic_fb_post.txt': data.get('arabic_fb_post', ''),
        'producthunt_blurb.txt': data.get('producthunt_blurb', ''),
        'landing_headline.txt': data.get('headline', ''),
        'paywall_copy_a.txt': data.get('paywall_a', ''),
        'paywall_copy_b.txt': data.get('paywall_b', ''),
    }
    for fn, content in files.items():
        (mdir / fn).write_text(content)

    summary = (
        f"📣 Marketing assets ready for {project_id}\n"
        f"Best 2 (manual post):\n\n"
        f"X:\n{files['x_thread.txt'][:700]}\n\n"
        f"LinkedIn:\n{files['linkedin_post.txt'][:700]}"
    )
    telegram_send(env, summary)
    log_action('agent3_marketing', 'generate', {'project_id': project_id, 'dir': str(mdir)})


# Agent 4

def analytics(env: Dict[str, str]):
    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    token = env.get('ADMIN_TOKEN', '')
    rows = []
    total_rev = 0
    for pid, meta in reg.items():
        url = (meta or {}).get('url', f'https://{pid}.petsy.company')
        try:
            r = requests.get(f'{url}/admin/stats', params={'token': token}, timeout=20)
            d = r.json() if r.ok else {}
        except Exception:
            d = {}
        purchases_today = int(((d.get('purchases') or {}).get('today') or 0))
        uses_today = int(d.get('uses_today') or 0)
        conv = round((purchases_today / uses_today * 100), 2) if uses_today else 0.0
        total_rev += purchases_today * 1
        rows.append({
            'project_id': pid,
            'url': url,
            'dau_today': int(d.get('dau_today') or 0),
            'uses_today': uses_today,
            'purchases_today': purchases_today,
            'conversion_rate': conv,
        })

    rows.sort(key=lambda x: x['purchases_today'], reverse=True)
    out = REPORTS_DIR / f'metrics-{today_str()}.json'
    write_json(out, {'date': today_str(), 'projects': rows, 'estimated_revenue_today_usd': total_rev})

    top = rows[0]['project_id'] if rows else 'n/a'
    low = [r['project_id'] for r in rows if r['uses_today'] < 10][:5]
    telegram_send(env, f"📊 Metrics\nTop project: {top}\nLow-performing: {', '.join(low) if low else 'none'}\nEstimated revenue today: ${total_rev}")
    log_action('agent4_analytics', 'run', {'file': str(out), 'projects': len(rows), 'revenue_today': total_rev})


# Agent 5

def optimization(env: Dict[str, str]):
    metrics = read_json(REPORTS_DIR / f'metrics-{today_str()}.json', {'projects': []})
    decisions = []
    q = read_json(QUEUE_FILE, {'items': []})

    for p in metrics.get('projects', []):
        pid = p['project_id']
        status = None
        if p.get('uses_today', 0) < 10:
            # check age >=3d
            reg = read_json(PROJECTS_DIR / 'registry.json', {})
            updated = (reg.get(pid) or {}).get('updated_at')
            old_enough = False
            if updated:
                try:
                    dt0 = dt.datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    old_enough = (dt.datetime.now(dt.timezone.utc) - dt0).days >= 3
                except Exception:
                    pass
            if old_enough:
                status = 'LOW_TRAFFIC'

        if p.get('conversion_rate', 0) > 3:
            status = 'WINNER'

        if status == 'WINNER':
            # generate 2 variants and queue for builder
            for n in [1, 2]:
                idea = {
                    'tool_name': f"{pid}-variant-{n}",
                    'target_user': f"Variant audience {n} for {pid}",
                    'problem_solved': 'Winner pattern replication to nearby niche',
                    'why_pay_1usd': 'Proven intent from winner baseline',
                    'marketing_keywords': [pid, 'variant', 'micro-saas'],
                    'spec_hint': f'Clone core of {pid} with audience angle {n}',
                }
                q['items'].append({'status': 'approved', 'created_at': now_iso(), 'idea': idea, 'source': 'optimization_winner'})
        elif status == 'LOW_TRAFFIC':
            # archive marker only (no delete)
            (PROJECTS_DIR / pid / 'ARCHIVED').write_text(now_iso())

        if status:
            decisions.append({'project_id': pid, 'status': status})

    write_json(QUEUE_FILE, q)
    out = REPORTS_DIR / f'optimization-{today_str()}.json'
    write_json(out, {'date': today_str(), 'decisions': decisions})
    telegram_send(env, f"🧪 Optimization decisions: {len(decisions)}\n" + '\n'.join([f"- {d['project_id']}: {d['status']}" for d in decisions[:20]]))
    log_action('agent5_optimization', 'run', {'file': str(out), 'decisions': decisions})


# Agent 6

def revenue(env: Dict[str, str]):
    reg = read_json(PROJECTS_DIR / 'registry.json', {})
    total_purchases = 0
    total_local = 0
    best = None
    best_p = -1

    for pid, meta in reg.items():
        dbp = PROJECTS_DIR / pid / 'data.sqlite'
        if not dbp.exists():
            continue
        try:
            import sqlite3
            con = sqlite3.connect(str(dbp))
            cur = con.cursor()
            p = cur.execute("select count(*) from purchases where status='credited'").fetchone()[0]
            g = cur.execute("select count(*) from grants").fetchone()[0]
            total_purchases += int(p)
            total_local += int(g)
            if p > best_p:
                best_p = p
                best = pid
            con.close()
        except Exception:
            pass

    est = total_purchases * 1
    out = REPORTS_DIR / f'revenue-{today_str()}.md'
    out.write_text(
        f"# Revenue Report {today_str()}\n\n"
        f"- Total purchases: {total_purchases}\n"
        f"- Total local grants: {total_local}\n"
        f"- Estimated revenue (USD): ${est}\n"
        f"- Best selling project: {best or 'n/a'}\n"
        f"- Recommended focus niche: job seekers / ATS optimization\n"
    )
    telegram_send(env, f"💰 Revenue today\nEstimated: ${est}\nBest seller: {best or 'n/a'}\nFocus: ATS/job-seekers")
    log_action('agent6_revenue', 'run', {'file': str(out), 'estimated': est, 'best': best})


def full_cycle_demo(env: Dict[str, str]):
    niche_research(env)
    built = product_builder(env, auto_approve_top=True)
    if built.get('project_id'):
        marketing_assets(env, built['project_id'])
        analytics(env)
        optimization(env)
        revenue(env)
        return built
    return {'status': 'no_build'}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('niche-research')
    sub.add_parser('product-builder')
    m = sub.add_parser('marketing')
    m.add_argument('--project-id', required=True)
    sub.add_parser('analytics')
    sub.add_parser('optimization')
    sub.add_parser('revenue')
    sub.add_parser('full-cycle-demo')

    args = parser.parse_args()
    env = load_env()

    if args.cmd == 'niche-research':
        niche_research(env)
    elif args.cmd == 'product-builder':
        product_builder(env, auto_approve_top=True)
    elif args.cmd == 'marketing':
        marketing_assets(env, args.project_id)
    elif args.cmd == 'analytics':
        analytics(env)
    elif args.cmd == 'optimization':
        optimization(env)
    elif args.cmd == 'revenue':
        revenue(env)
    elif args.cmd == 'full-cycle-demo':
        built = full_cycle_demo(env)
        print(json.dumps(built, ensure_ascii=False))


if __name__ == '__main__':
    main()
