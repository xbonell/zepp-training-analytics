# Cloudflare Access Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the outer-rim deploy docs into a concrete Cloudflare Access recipe (email OTP, owner email only, edge-only) so `training.xbonell.com` can be gated before go-live.

**Architecture:** Documentation-only change. No app or API auth code. Access terminates at Cloudflare; the SPA and FastAPI stay auth-free. Operator configures Zero Trust in the Cloudflare dashboard using the expanded checklist in `docs/deploy-outer-rim.md`.

**Tech Stack:** Markdown docs; Cloudflare Zero Trust Access (self-hosted app, One-time PIN); existing `outer-rim` proxied DNS + nginx topology (unchanged).

## Global Constraints

- Edge-only gate: no in-app login, sessions, API keys, or origin JWT verification
- Identity: email one-time PIN; Allow policy = owner email only + Require OTP
- Hostname: `training.xbonell.com` (whole host covers SPA and `/api`)
- Order: HTTPS first → enable Access → verify → then real Zepp token
- Do not use Include → Everyone, domain-wide consumer email, or OTP-only Include without an email restriction
- No compose/nginx/app code changes in this plan
- Spec: `docs/superpowers/specs/2026-08-29-cloudflare-access-gate-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `docs/deploy-outer-rim.md` | Replace thin §1 Cloudflare with full Access recipe; expand §7 verification for Access checks |
| `docs/architecture.md` | One clarifying sentence that Access is edge email-OTP and app has no login |

---

### Task 1: Expand Cloudflare Access recipe in deploy doc

**Files:**
- Modify: `docs/deploy-outer-rim.md` (Prerequisites bullet + entire `## 1. Cloudflare` section)
- Test: manual doc review against spec checklist (no automated test suite for markdown)

**Interfaces:**
- Consumes: decisions from `docs/superpowers/specs/2026-08-29-cloudflare-access-gate-design.md` §§5–7
- Produces: operator-ready Access steps that Task 2’s verification list assumes exist

- [ ] **Step 1: Confirm current §1 is the thin placeholder**

Run:

```bash
sed -n '5,17p' docs/deploy-outer-rim.md
```

Expected: Prerequisites mention Access in one line; §1 has four short steps (DNS, Access one-liner, SSL, order note).

- [ ] **Step 2: Replace Prerequisites Access bullet and rewrite `## 1. Cloudflare`**

In `docs/deploy-outer-rim.md`, change the Prerequisites Access line to:

```markdown
- [ ] Cloudflare Access (OTP + owner email) for `training.xbonell.com` — enable after HTTPS, before real Zepp tokens
```

Replace the entire `## 1. Cloudflare` section with:

```markdown
## 1. Cloudflare

### 1.1 DNS and TLS (before Access)

1. Add DNS record: `training` → VPS IP (**proxied** / orange cloud).
2. Bring up the site containers so nginx-proxy can issue the certificate.
3. Set SSL/TLS mode to **Full (Strict)** after the origin certificate exists.
4. Confirm `https://training.xbonell.com` responds over HTTPS (Access still off is OK at this step).

### 1.2 Enable One-time PIN

In Cloudflare Zero Trust:

1. Open **Settings → Authentication** (login methods).
2. Add **One-time PIN** if it is not already enabled.
3. No other identity provider is required for this app.

If OTP emails are filtered, allowlist Cloudflare’s notify sender using the
address listed in the current [One-time PIN docs](https://developers.cloudflare.com/cloudflare-one/identity/one-time-pin/).

### 1.3 Self-hosted Access application

1. Create an Access application:
   - **Type:** Self-hosted
   - **Application domain:** `training.xbonell.com` (whole hostname — covers `/` and `/api/*`)
   - **Session duration:** long enough for daily personal use (e.g. 1 month)
2. Attach an **Allow** policy:

| Rule type | Selector | Value |
|-----------|----------|-------|
| Include | Emails | Your personal email only (exact address) |
| Require | Login methods | One-time PIN |

3. Do **not**:
   - Use Include → **Everyone**
   - Use “emails ending in” a broad consumer domain (e.g. `@gmail.com`)
   - Use OTP as the only Include rule without an email restriction (anyone could request a PIN)

### 1.4 Order of operations (mandatory)

1. DNS proxied + HTTPS working end-to-end (§1.1).
2. Enable Access application + policy (§1.2–1.3).
3. Verify the gate (§7 Access checks).
4. Only then paste a real Zepp token in Settings.

**Origin reminder:** Keep `zepp-training-api` off the public internet (no
`VIRTUAL_HOST`, no published `:8000`). Access is edge-only; a publicly
reachable origin would bypass it.
```

Leave sections 2–6 unchanged.

- [ ] **Step 3: Spec coverage check for Task 1**

Run:

```bash
rg -n "One-time PIN|Everyone|emails ending|VIRTUAL_HOST|Full \(Strict\)|1 month" docs/deploy-outer-rim.md
```

Expected: matches for OTP, anti-pattern warnings (Everyone / emails ending), origin reminder (`VIRTUAL_HOST`), TLS Full Strict, session duration example.

- [ ] **Step 4: Commit**

```bash
git add docs/deploy-outer-rim.md
git commit -m "$(cat <<'EOF'
docs: expand Cloudflare Access recipe for training host

Spell out OTP IdP, owner-email Allow policy, order of ops, and
anti-patterns so the gate is ready before go-live secrets.

EOF
)"
```

---

### Task 2: Verification checklist + architecture note

**Files:**
- Modify: `docs/deploy-outer-rim.md` (`## 7. Verification`)
- Modify: `docs/architecture.md` (self-hosted paragraph that mentions Access)

**Interfaces:**
- Consumes: Access recipe from Task 1 (§1.2–1.4)
- Produces: go-live checks an operator can tick; architecture wording aligned with edge OTP

- [ ] **Step 1: Replace `## 7. Verification` Access-related items**

Replace the current `## 7. Verification` section with:

```markdown
## 7. Verification

### Access gate (do these first)

- [ ] Incognito → `https://training.xbonell.com` shows Access login / redirect, not the SPA
- [ ] Incognito → `https://training.xbonell.com/api/health` is gated the same way (not a public 200 without login)
- [ ] Owner email + OTP → SPA loads
- [ ] Owner session → `https://training.xbonell.com/api/health` returns OK
- [ ] Non-allowlisted email → no usable session

Revoke access later by removing the email from the Access policy or disabling the application.

### App smoke (after Access works)

- [ ] Settings → connection test succeeds with masked token display
- [ ] Manual sync + normalize completes; dashboard shows data
```

- [ ] **Step 2: Clarify Access in `docs/architecture.md`**

Find the self-hosted paragraph (currently ends with “Cloudflare Access gates the origin”). Change that clause so the sentence reads along these lines (keep surrounding local-first wording intact):

```markdown
nginx serves the static SPA on `training.xbonell.com`, proxies `/api/` to the
`zepp-training-api` container, and Cloudflare Access (email one-time PIN, owner
only) gates the hostname at the edge — the app itself has no login.
```

Exact surrounding sentences before/after Credentials / raw archives may stay as-is; only the Access clause needs this precision.

- [ ] **Step 3: Final spec coverage grep**

Run:

```bash
rg -n "Incognito|Non-allowlisted|one-time PIN|no login" docs/deploy-outer-rim.md docs/architecture.md
```

Expected: Access verification bullets present; architecture mentions one-time PIN and no login.

- [ ] **Step 4: Commit**

```bash
git add docs/deploy-outer-rim.md docs/architecture.md
git commit -m "$(cat <<'EOF'
docs: add Access verification checks and architecture note

Document incognito/API gate expectations and clarify edge OTP
vs in-app auth for the self-hosted deploy.

EOF
)"
```

---

## Spec coverage (plan self-review)

| Spec requirement | Task |
|------------------|------|
| Enable One-time PIN IdP | Task 1 §1.2 |
| Self-hosted app for whole hostname | Task 1 §1.3 |
| Allow owner email + Require OTP | Task 1 §1.3 |
| Session duration note | Task 1 §1.3 |
| Anti-patterns (Everyone / domain / OTP-only Include) | Task 1 §1.3 |
| Order: HTTPS → Access → verify → token | Task 1 §1.4 |
| Origin non-public reminder | Task 1 §1.4 |
| OTP mail allowlist pointer | Task 1 §1.2 |
| Expand `deploy-outer-rim.md` | Tasks 1–2 |
| Optional `architecture.md` clarification | Task 2 |
| Verification table (incognito, API, owner, wrong email) | Task 2 §7 |
| No app/compose code | Global constraints / no tasks touch runtime |

No placeholders; no origin JWT or Tunnel scope creep.
