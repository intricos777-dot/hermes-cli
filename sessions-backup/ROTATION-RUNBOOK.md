<!-- Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work -->
# Credential Rotation Runbook

**Status: NOT DONE. These credentials are still live and must be rotated by hand.**

Redaction removes secrets from files. It does not invalidate them. Anything listed
here was at some point written into a file, a log, or a git commit, and must be
treated as compromised regardless of how well the repo is protected.

I cannot perform these rotations: each requires authenticating to the issuing
service to mint a replacement, and none of these accounts are accessible from
this machine.

## Priority 1 — live keys in active use

| Fingerprint | Type | Where | Action |
|---|---|---|---|
| `b3dbd700` | SSH private key | `~/.ssh/id_ed25519` | Your live SSH key. Not leaked, but if it was ever pasted into a terminal it is exposed. Consider a new key. |
| `33ea101d` | EC private key | `Desktop/cdp_api_key.json`, `.config/kdeconnect/privateKey.pem` | Rotate the CDP/API key it protects. |
| `1a5d44a2` | AWS access key ID | 9 locations incl. `.hermes/.curator_backups/blobs/*` | Disable in IAM, issue replacement. |
| `8365b07e` | JWT | `.hermes/auth.json`, `.hermes/shared/nous_auth.json` | Re-authenticate the Nous portal to mint a new token. |
| `49669825`, `cad81719`, `4528f0bd` | GitHub PATs | session history, skills docs, opencode log | Revoke at github.com/settings/tokens, re-`gh auth login`. |

## Priority 2 — provider API keys in session history

| Fingerprint | Type |
|---|---|
| `5a696d35`, `e8d2a2a0`, `df8c313a`, `f6882d07` | OpenAI |
| `a6f6ff79`, `d04a2104`, `f530817b` | Anthropic |
| `5ec10482`, `6b27ee41`, `5e8a6a8b` | Google |
| `9787577e`, `2b763169`, `646c8552`, `d1add261`, `cc658971` | Slack |
| `670b9d6f`, `ff330437` | JWT (other) |

Revoke each at its provider dashboard, then re-issue.

## Priority 3 — private keys found in session text

`8bcac790` (x7), `9bd6e788` (x29), `55d40943`, `33c19f50`, `779c19b4`, `e2705d5a`,
`7166d06e`, `4940ca53`, `7783a9d3`, `c8c13d01`, `3e1bc2fc`, `f02d7a5c`

Most of these are **test fixtures** — synthetic keys written into test files and
agent transcripts. Confirm provenance before rotating: if a key was generated
solely for a test, deleting the fixture is sufficient. If any was ever used
against a real service, rotate it.

`4940ca53` is a test key in `lin-antimalware/tests/test_dredge.py`. It is **not**
your live SSH key (`b3dbd700`) — verified by comparing full key bodies.

## False positives — do not chase these

`3021d90e` and `03d104c6` are fingerprints of the literal PEM header line
(dashes, `BEGIN`, the words `PRIVATE KEY`, dashes), which is byte-identical for
every PEM key. They group many unrelated keys into one bogus entry and are not
real secrets. A scan that fingerprints only the header cannot distinguish keys —
always hash the full body.

## Also worth knowing

`.local/share/opencode/log/opencode.log` contains many of these, because
scanning output is itself logged. Treat that log as sensitive; it is the one file
where remediation can re-introduce the problem it is fixing.

After rotating, re-run the sweep and confirm the fingerprints are gone rather
than merely redacted.
