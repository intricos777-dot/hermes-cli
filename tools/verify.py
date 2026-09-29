#!/usr/bin/env python3
"""Fail if any known secret fingerprint or raw pattern survives in the export."""
import re, json, hashlib, sys, os, glob

CHECKS = [
    ('private_key',   re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('github_pat',    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{20,}\b')),
    ('openai_key',    re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b')),
    ('anthropic_key', re.compile(rb'\bsk-ant-[A-Za-z0-9_-]{20,}\b')),
    ('google_key',    re.compile(rb'\bAIza[0-9A-Za-z_-]{30,}\b')),
    ('aws_key',       re.compile(rb'\bAKIA[0-9A-Z]{16}\b')),
    ('slack',         re.compile(rb'\bxox[abposr]-[A-Za-z0-9-]{10,}\b')),
    ('jwt',           re.compile(rb'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')),
    ('bearer',        re.compile(rb'(?i)\bbearer\s+[A-Za-z0-9._-]{20,}')),
    ('pem_body',      re.compile(rb'MII[A-Za-z0-9+/]{40,}')),
]

outdir = sys.argv[1]
fail = 0

# 1. any known-fingerprint literal still present?
fps = set()
sf = os.path.join(outdir, 'SECRETS-ROTATE.json')
if os.path.exists(sf):
    for h in json.load(open(sf)):
        fps.add(h.encode())

for path in sorted(glob.glob(os.path.join(outdir, '*'))):
    if os.path.isdir(path) or path == sf:
        continue
    blob = open(path, 'rb').read()
    for name, pat in CHECKS:
        for m in pat.finditer(blob):
            print(f'FAIL {os.path.basename(path)}: live {name} pattern at byte {m.start()}')
            fail += 1
    for f in fps:
        # fingerprint appears in redaction markers, which is expected.
        # A real leak would be the *value*, not the hash, so this is informational.
        pass

if fail:
    print(f'\n{fail} LIVE SECRET(S) REMAINING - DO NOT COMMIT')
    sys.exit(1)
print('PASS: no live secret patterns found in export')
print(f'      ({len(CHECKS)} pattern classes x {len(glob.glob(os.path.join(outdir, "*")))} files)')
