#!/usr/bin/env python3
import json
import os
import re
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

ROOT = Path('/srv/ai-software-factory')
PROJECTS_ROOT = ROOT / 'projects'
STATE_FILE = ROOT / 'telegram_bot' / 'state.json'


def load_env(path: Path) -> Dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def ensure_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({'chats': {}, 'watch': {}, 'last_notified': {}}, ensure_ascii=False, indent=2))
    st = json.loads(STATE_FILE.read_text())
    st.setdefault('chats', {})
    st.setdefault('watch', {})
    st.setdefault('last_notified', {})
    return st


def save_state(state: Dict[str, Any]):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def mk_project_id() -> str:
    return time.strftime('prj_%Y%m%d%H%M%S', time.gmtime())


def detect_stack(spec: str) -> str:
    s = spec.lower()
    if 'laravel' in s:
        return 'laravel'
    if 'flutter' in s:
        return 'flutter'
    return 'nextjs'


def create_project(project_id: str, spec: str = ''):
    p = PROJECTS_ROOT / project_id
    (p / 'tasks').mkdir(parents=True, exist_ok=True)
    (p / 'state').mkdir(parents=True, exist_ok=True)
    (p / 'repo').mkdir(parents=True, exist_ok=True)
    (p / 'logs').mkdir(parents=True, exist_ok=True)
    if spec:
        (p / 'project_spec.md').write_text(spec)
    stack = detect_stack(spec) if spec else 'nextjs'
    (p / 'state' / 'spec.json').write_text(json.dumps({'stack': stack}, ensure_ascii=False, indent=2))


def list_projects(limit: int = 8) -> List[str]:
    if not PROJECTS_ROOT.exists():
        return []
    ids = [x.name for x in PROJECTS_ROOT.iterdir() if x.is_dir() and x.name.startswith('prj_')]
    ids.sort(reverse=True)
    return ids[:limit]


def run_project(project_id: str, env: Dict[str, str]) -> Dict[str, Any]:
    user = env.get('DASHBOARD_USER', '')
    pw = env.get('DASHBOARD_PASS', '')
    url = f"http://127.0.0.1:5680/api/projects/{project_id}/run"
    r = requests.post(url, auth=(user, pw), timeout=25)
    try:
        data = r.json()
    except Exception:
        data = {'status_code': r.status_code, 'text': r.text[:300]}
    return {'code': r.status_code, 'data': data}


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


def project_progress(project_id: str) -> Dict[str, Any]:
    p = PROJECTS_ROOT / project_id
    status_p = p / 'state' / 'status.json'
    spec_p = p / 'project_spec.md'
    repo_p = p / 'repo'
    zip_p = p / f'{project_id}.zip'
    logs_p = p / 'logs' / 'build.log'

    phase = 'NOT_STARTED'
    updated_at = None
    if status_p.exists():
        try:
            s = json.loads(status_p.read_text())
            phase = (s.get('phase') or 'RUNNING').upper()
            updated_at = s.get('updated_at')
        except Exception:
            phase = 'RUNNING'

    # milestones
    milestones: List[Tuple[str, bool]] = [
        ('المواصفات محفوظة', spec_p.exists()),
        ('بدء التنفيذ', phase in ('RUNNING', 'PASSED', 'FAILED')),
        ('بناء الملفات الأساسية', repo_p.exists() and any(repo_p.rglob('*'))),
        ('تسجيل اللوج', logs_p.exists()),
        ('إنشاء ملف التسليم ZIP', zip_p.exists()),
        ('اكتمال التنفيذ', phase == 'PASSED'),
    ]

    weights = [10, 15, 25, 15, 20, 15]
    percent = 0
    for i, (_, done) in enumerate(milestones):
        if done:
            percent += weights[i]

    if phase == 'FAILED':
        percent = max(percent, 35)
    if phase == 'PASSED':
        percent = 100

    # ETA heuristic (dynamic and practical)
    now = datetime.now(timezone.utc)
    created_ts = None
    if p.exists():
        created_ts = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    updated = _parse_iso(updated_at) if updated_at else None
    ref = updated or created_ts or now
    elapsed_min = max(1, int((now - ref).total_seconds() / 60)) if ref else 1

    if phase == 'PASSED':
        eta = 'خلص ✅'
    elif phase == 'FAILED':
        eta = 'متوقف بسبب خطأ ❌'
    elif percent < 20:
        eta = 'تقريباً 12-18 دقيقة'
    elif percent < 40:
        eta = 'تقريباً 8-12 دقيقة'
    elif percent < 60:
        eta = 'تقريباً 5-8 دقائق'
    elif percent < 80:
        eta = 'تقريباً 3-5 دقائق'
    else:
        eta = 'تقريباً 1-3 دقائق'

    done_list = [name for name, ok in milestones if ok]
    pending_list = [name for name, ok in milestones if not ok]

    return {
        'phase': phase,
        'percent': min(100, max(0, percent)),
        'eta': eta,
        'done': done_list,
        'pending': pending_list,
        'updated_at': updated_at,
        'elapsed_hint_min': elapsed_min,
    }


def format_progress(project_id: str) -> str:
    pr = project_progress(project_id)
    bar_fill = max(0, min(10, int(round((pr['percent'] or 0) / 10))))
    bar = '█' * bar_fill + '░' * (10 - bar_fill)
    done = '\n'.join([f'✅ {x}' for x in pr['done'][:6]]) or '—'
    pending = '\n'.join([f'⏳ {x}' for x in pr['pending'][:4]]) or '—'
    return (
        f"📊 حالة المشروع: {project_id}\n"
        f"• الحالة: {pr['phase']}\n"
        f"• التقدم: {bar} {pr['percent']}%\n"
        f"• الوقت التقديري المتبقي: {pr['eta']}\n"
        f"• آخر تحديث: {pr['updated_at'] or 'غير متوفر'}\n\n"
        f"المنجز:\n{done}\n\n"
        f"المتبقي:\n{pending}"
    )


MAIN_KB = ReplyKeyboardMarkup(
    [["🆕 مشروع جديد", "📝 إضافة مواصفات"], ["🚀 تشغيل مشروع", "📊 حالة المشروع"], ["📁 مشاريعي", "❓مساعدة"]],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلًا 👋\nصار البوت أسهل باستخدام الأزرار.\nاختر من القائمة:",
        reply_markup=MAIN_KB,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الاستخدام السريع:\n"
        "1) 🆕 مشروع جديد\n"
        "2) 📝 إضافة مواصفات\n"
        "3) 🚀 تشغيل مشروع\n"
        "4) 📊 حالة المشروع",
        reply_markup=MAIN_KB,
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    env = context.bot_data['env']
    chat_id = str(q.message.chat_id)
    st = ensure_state()
    chat = st['chats'].setdefault(chat_id, {})
    data = q.data or ''

    if data.startswith('run:'):
        pid = data.split(':', 1)[1]
        res = run_project(pid, env)
        chat['last_project_id'] = pid
        st['watch'].setdefault(pid, [])
        if chat_id not in st['watch'][pid]:
            st['watch'][pid].append(chat_id)
        save_state(st)
        await q.edit_message_text(f"🚀 تشغيل {pid}\nHTTP {res['code']}\n{json.dumps(res['data'], ensure_ascii=False)}")
        return

    if data.startswith('status:'):
        pid = data.split(':', 1)[1]
        await q.edit_message_text(format_progress(pid))
        return


def monitor_notifications(token: str):
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    while True:
        try:
            st = ensure_state()
            watch = st.get('watch', {})
            last = st.get('last_notified', {})

            for pid, chats in list(watch.items()):
                if not chats:
                    continue
                pr = project_progress(pid)
                phase = pr.get('phase', 'UNKNOWN')

                if phase in ('PASSED', 'FAILED') and last.get(pid) != phase:
                    text = (
                        f"🔔 تحديث المشروع {pid}\n"
                        f"الحالة: {phase}\n"
                        f"التقدم: {pr.get('percent', 0)}%\n"
                        f"التقدير: {pr.get('eta', '-')}"
                    )
                    for cid in chats:
                        try:
                            requests.post(api, json={'chat_id': int(cid), 'text': text}, timeout=10)
                        except Exception:
                            pass
                    last[pid] = phase

            st['last_notified'] = last
            save_state(st)
        except Exception:
            pass

        time.sleep(60)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (update.message.text or '').strip()
    env = context.bot_data['env']
    chat_id = str(update.message.chat_id)
    st = ensure_state()
    chat = st['chats'].setdefault(chat_id, {})

    if msg in ('/help', '❓مساعدة'):
        await help_cmd(update, context)
        return

    if msg == '🆕 مشروع جديد':
        pid = mk_project_id()
        create_project(pid, '')
        chat['last_project_id'] = pid
        chat['pending_spec_for'] = pid
        st['watch'].setdefault(pid, [])
        if chat_id not in st['watch'][pid]:
            st['watch'][pid].append(chat_id)
        save_state(st)
        await update.message.reply_text(
            f"✅ تم إنشاء مشروع: {pid}\n\nأرسل الآن وصف المشروع/المواصفات في رسالة واحدة وأنا أحفظها مباشرة.",
            reply_markup=MAIN_KB,
        )
        return

    if msg == '📝 إضافة مواصفات':
        pid = chat.get('last_project_id')
        if not pid:
            await update.message.reply_text('ما عندك مشروع بعد. اضغط 🆕 مشروع جديد أولًا.', reply_markup=MAIN_KB)
            return
        chat['pending_spec_for'] = pid
        save_state(st)
        await update.message.reply_text(f"أرسل مواصفات المشروع الآن لـ {pid}", reply_markup=MAIN_KB)
        return

    if msg == '🚀 تشغيل مشروع':
        ids = list_projects()
        if not ids:
            await update.message.reply_text('ما في مشاريع بعد. ابدأ بـ 🆕 مشروع جديد', reply_markup=MAIN_KB)
            return
        kb = [[InlineKeyboardButton(f"🚀 {pid}", callback_data=f"run:{pid}")] for pid in ids[:8]]
        await update.message.reply_text('اختر مشروع للتشغيل:', reply_markup=InlineKeyboardMarkup(kb))
        return

    if msg == '📁 مشاريعي':
        ids = list_projects(12)
        if not ids:
            await update.message.reply_text('ما في مشاريع بعد.', reply_markup=MAIN_KB)
            return
        lines = []
        for x in ids:
            pr = project_progress(x)
            lines.append(f"- {x} | {pr['phase']} | {pr['percent']}%")
        await update.message.reply_text('آخر المشاريع:\n' + '\n'.join(lines), reply_markup=MAIN_KB)
        return

    if msg == '📊 حالة المشروع':
        ids = list_projects(8)
        if not ids:
            await update.message.reply_text('ما في مشاريع بعد.', reply_markup=MAIN_KB)
            return
        kb = [[InlineKeyboardButton(f"📊 {pid}", callback_data=f"status:{pid}")] for pid in ids[:8]]
        await update.message.reply_text('اختر مشروع لمعرفة الحالة:', reply_markup=InlineKeyboardMarkup(kb))
        return

    pending = chat.get('pending_spec_for')
    if pending:
        spec = msg
        create_project(pending, spec)
        chat['pending_spec_for'] = None
        save_state(st)
        await update.message.reply_text(f"✅ تم حفظ المواصفات للمشروع {pending}\nالآن اضغط 🚀 تشغيل مشروع", reply_markup=MAIN_KB)
        return

    # fallback: quick text as new project spec
    if len(msg) > 20 and not msg.startswith('/'):
        pid = mk_project_id()
        create_project(pid, msg)
        chat['last_project_id'] = pid
        st['watch'].setdefault(pid, [])
        if chat_id not in st['watch'][pid]:
            st['watch'][pid].append(chat_id)
        save_state(st)
        await update.message.reply_text(f"✅ أنشأت مشروع جديد وحفظت المواصفات: {pid}\nاضغط 🚀 تشغيل مشروع", reply_markup=MAIN_KB)
        return

    await update.message.reply_text('اختر زر من القائمة 👇', reply_markup=MAIN_KB)


def main():
    env = load_env(ROOT / '.env')
    token = env.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN missing in /srv/ai-software-factory/.env')

    app = Application.builder().token(token).build()
    app.bot_data['env'] = env

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    t = threading.Thread(target=monitor_notifications, args=(token,), daemon=True)
    t.start()

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
