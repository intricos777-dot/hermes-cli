#!/usr/bin/env python3
# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
"""Export session history from hermes + opencode SQLite stores to redacted JSONL."""
import sqlite3, re, json, hashlib, os, sys, datetime

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

# Ordered: most specific first so generic patterns don't clobber specific ones.
PATTERNS = [
    # Full PEM block (BEGIN..END), then a bare BEGIN header with no END, then a
    # standalone PKCS#8/DER key body (MII...) which can appear without any header.
    ('private_key',  re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----')),
    ('private_key',  re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('private_key',  re.compile(r'\bMII[A-Za-z0-9+/]{40,}={0,2}')),
    ('github_pat',   re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b')),
    ('openai_key',   re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b')),
    ('anthropic_key',re.compile(r'\bsk-ant-[A-Za-z0-9_-]{20,}\b')),
    ('google_key',   re.compile(r'\bAIza[0-9A-Za-z_-]{30,}\b')),
    ('aws_key',      re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('slack',        re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}\b')),
    ('jwt',          re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')),
    ('bearer',       re.compile(r'(?i)\b(bearer\s+)[A-Za-z0-9._-]{20,}')),
    ('generic_secret', re.compile(r'(?i)\b(api[_-]?key|secret|passwd|password|token|access[_-]?token|refresh[_-]?token|agent[_-]?key)\b(\s*[=:]\s*["\']?)([A-Za-z0-9._\-]{16,})')),
]

stats = {}
seen_fps = {}

def fp(v):
    return hashlib.sha256(v.encode(errors='replace')).hexdigest()[:8]

def redact(s):
    if not isinstance(s, str) or not s:
        return s, 0
    n = 0
    for name, pat in PATTERNS:
        def sub(m):
            nonlocal n
            if m.re.groups >= 2 and m.lastindex and m.lastindex >= 2:
                groups = m.groups()
                val = groups[-1]
                pre = ''.join(g for g in groups[:-1] if g)
            else:
                pre, val = m.group(0), m.group(0)
            n += 1
            h = fp(val)
            seen_fps.setdefault(h, {'type': name, 'count': 0})
            seen_fps[h]['count'] += 1
            return f'[{name.upper()}_REDACTED:{h}]'
        s = pat.sub(sub, s)
    return s, n

def scrub(obj):
    """Recursively redact all strings in a decoded JSON structure."""
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return '<binary:' + str(len(bytes(obj))) + ' bytes>'
    if isinstance(obj, str):
        return redact(obj)[0]
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    return obj

def maybe_json(s):
    if not isinstance(s, str):
        return s
    t = s.strip()
    if t[:1] in '[{' and len(t) > 1:
        try:
            return scrub(json.loads(t))
        except Exception:
            return redact(s)[0]
    return redact(s)[0]

def write_jsonl(path, rows):
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    return len(rows)

# ---------------- hermes ----------------
H = '/home/livings/.hermes/state.db'
con = sqlite3.connect(f'file:{H}?mode=ro', uri=True)
con.row_factory = sqlite3.Row

sess = []
for r in con.execute("select * from sessions"):
    d = dict(r)
    d.pop('system_prompt', None)
    for k in ('origin_json', 'model_config'):
        if d.get(k):
            d[k] = maybe_json(d[k])
    sess.append(scrub(d))

msgs = []
for r in con.execute(
    "select id, session_id, role, content, api_content, reasoning, reasoning_content, "
    "tool_calls, tool_name, tool_call_id, timestamp, token_count, finish_reason, "
    "compacted, active, display_kind, display_identity, display_order, platform_message_id "
    "from messages order by session_id, timestamp"
):
    d = dict(r)
    for k in ('content', 'api_content', 'reasoning', 'reasoning_content', 'tool_calls'):
        if d.get(k):
            d[k] = maybe_json(d[k])
    msgs.append(scrub(d))
con.close()

n1 = write_jsonl(f'{OUT}/hermes-sessions.jsonl', sess)
n2 = write_jsonl(f'{OUT}/hermes-messages.jsonl', msgs)
print(f'hermes: {n1} sessions, {n2} messages')

# ---------------- opencode ----------------
O = '/home/livings/.local/share/opencode/opencode.db'
con = sqlite3.connect(f'file:{O}?mode=ro', uri=True)
con.row_factory = sqlite3.Row

oc_sess = []
for r in con.execute(
    "select id, parent_id, slug, directory, path, title, version, share_url, "
    "summary_additions, summary_deletions, cost, tokens_input, tokens_output, "
    "tokens_reasoning, tokens_cache_read, tokens_cache_write, permission, agent, model, "
    "time_created, time_updated, time_archived from session"
):
    d = dict(r)
    if d.get('metadata'):
        d['metadata'] = maybe_json(d['metadata'])
    for k in ('summary_files', 'summary_diffs'):
        if d.get(k):
            d[k] = maybe_json(d[k])
    oc_sess.append(scrub(d))

oc_msg = []
for r in con.execute("select id, session_id, time_created, time_updated, data from message order by session_id, time_created"):
    d = dict(r)
    if d.get('data'):
        try:
            d['data'] = scrub(json.loads(d['data']))
        except Exception:
            d['data'] = redact(d['data'])[0]
    oc_msg.append(scrub(d))

oc_part = []
for r in con.execute("select id, message_id, session_id, time_created, time_updated, data from part order by session_id, id"):
    d = dict(r)
    if d.get('data'):
        try:
            d['data'] = scrub(json.loads(d['data']))
        except Exception:
            d['data'] = redact(d['data'])[0]
    oc_part.append(scrub(d))
con.close()

n3 = write_jsonl(f'{OUT}/opencode-sessions.jsonl', oc_sess)
n4 = write_jsonl(f'{OUT}/opencode-messages.jsonl', oc_msg)
n5 = write_jsonl(f'{OUT}/opencode-parts.jsonl', oc_part)
print(f'opencode: {n3} sessions, {n4} messages, {n5} parts')

# ---------------- manifest ----------------
man = {
    'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sources': {
        'hermes':  {'db': H,  'sessions': n1, 'messages': n2},
        'opencode':{'db': O,  'sessions': n3, 'messages': n4, 'parts': n5},
    },
    'redaction': {
        'policy': 'secrets replaced with [TYPE_REDACTED:sha256[:8]] placeholders',
        'excluded_files': ['auth.json', 'secret.bin', '*.db', '*.db-wal', '*.db-shm', 'cookies', 'keys', 'caches'],
        'distinct_secrets_redacted': len(seen_fps),
        'total_redactions': sum(v['count'] for v in seen_fps.values()),
        'by_type': {},
    },
}
by_type = {}
for v in seen_fps.values():
    by_type[v['type']] = by_type.get(v['type'], 0) + v['count']
man['redaction']['by_type'] = by_type

with open(f'{OUT}/SECRETS-ROTATE.json', 'w') as f:
    json.dump({h: v for h, v in sorted(seen_fps.items(), key=lambda x: -x[1]['count'])}, f, indent=2)

with open(f'{OUT}/MANIFEST.json', 'w') as f:
    json.dump(man, f, indent=2)

print(f"redacted {man['redaction']['total_redactions']} occurrences "
      f"across {man['redaction']['distinct_secrets_redacted']} distinct secrets")
print('by type:', json.dumps(by_type))
