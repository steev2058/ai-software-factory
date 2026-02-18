#!/usr/bin/env python3
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List

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
        STATE_FILE.write_text(json.dumps({'chats': {}}, ensure_ascii=False, indent=2))
    return json.loads(STATE_FILE.read_text())


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


def read_status(project_id: str) -> str:
    p = PROJECTS_ROOT / project_id / 'state' / 'status.json'
    if not p.exists():
        return 'لا يوجد status.json بعد.'
    try:
        d = json.loads(p.read_text())
    except Exception:
        return p.read_text()[:400]
    return json.dumps(d, ensure_ascii=False, indent=2)


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
        save_state(st)
        await q.edit_message_text(f"🚀 تشغيل {pid}\nHTTP {res['code']}\n{json.dumps(res['data'], ensure_ascii=False)}")
        return

    if data.startswith('status:'):
        pid = data.split(':', 1)[1]
        await q.edit_message_text(f"📊 حالة {pid}\n```\n{read_status(pid)}\n```", parse_mode='Markdown')
        return


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
        await update.message.reply_text('آخر المشاريع:\n' + '\n'.join(f"- {x}" for x in ids), reply_markup=MAIN_KB)
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

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
