# Cloudflare Access Gate Design

**Date:** 2026-08-29  
**Status:** Approved (brainstorming)  
**Scope:** Operator recipe to put `training.xbonell.com` behind Cloudflare
Access (email one-time PIN, owner email only) before go-live — edge gate only,
no in-app auth.

## 1. Goal

Before the public deploy holds real Zepp credentials or health data, lock the
hostname so only the owner can reach the SPA and `/api` after proving identity
via Cloudflare Access.

**Success criteria**

- Unauthenticated visits to `https://training.xbonell.com` (any path, including
  `/api/*`) hit the Access login wall, not the app
- Owner authenticates with email OTP and reaches the dashboard + API
- Non-allowlisted emails cannot obtain a usable session
- Recipe lives in `docs/deploy-outer-rim.md` and matches existing single-user
  deploy assumptions (no application login code)

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| Audience | Single user (owner only) |
| Situation | Not deployed yet; Access recipe ready before go-live |
| Gate depth | Edge only (Cloudflare Access); no origin JWT / in-app auth |
| Identity | Email one-time PIN (simplest solid option for solo use) |
| Policy | Allow exact owner email; require OTP login method |
| Topology | Unchanged: proxied DNS → outer-rim nginx-proxy → site nginx → static + `/api` |
| Deliverable | Docs / operator checklist expansion (not app code) |

## 3. Out of scope

- In-app login, sessions, API keys, or Access JWT verification at the origin
- Google / GitHub / other IdPs (can add later without changing app code)
- Cloudflare Tunnel or other topology changes vs `outer-rim`
- Terraform / API automation of Zero Trust resources
- Multi-user or shared access

## 4. Runtime behavior

```text
Browser
  → training.xbonell.com
  → Cloudflare (DNS + Access)
       ├─ no valid Access session → redirect to *.cloudflareaccess.com
       │    ├─ allowlisted email → OTP email → PIN → session cookie → origin
       │    └─ other email → no usable access (no PIN / deny)
       └─ valid Access session → outer-rim :443 → training nginx
            ├─ /       static Vite build
            └─ /api/*  zepp-training-api (internal network only)
```

Access terminates at the edge. The React app and FastAPI remain auth-free for
v1, as already specified in the self-hosted deploy design.

## 5. Access configuration

### Identity provider

- Enable **One-time PIN** under Cloudflare Zero Trust login methods before
  relying on OTP for this application
- No additional IdP required for this cut

### Application

| Field | Value |
|---|---|
| Type | Self-hosted |
| Application domain | `training.xbonell.com` (whole hostname; covers SPA and `/api`) |
| Session duration | Long enough for daily personal use (e.g. ~1 month); adjustable later |

### Policy

| Action | Rule type | Selector | Value |
|---|---|---|---|
| Allow | Include | Emails | Owner’s personal email address only |
| Allow | Require | Login methods | One-time PIN |

Do **not** use Include → Everyone, or “emails ending in” a broad consumer domain.
Do **not** attach OTP as the only Include rule without an email restriction
(that would let any address request a PIN).

### Order of operations

1. DNS `training` → VPS IP, Cloudflare proxy on
2. HTTPS end-to-end (Let’s Encrypt + SSL mode Full Strict once origin cert exists)
3. Enable Access application + policy above
4. Verify the gate (see §7)
5. Only then paste a real Zepp token in Settings

Access must be on before real secrets; Access must not block HTTPS bring-up
(enable after TLS works).

## 6. Documentation changes (this repo)

Expand `docs/deploy-outer-rim.md` section **1. Cloudflare** from a one-liner into
a step-by-step Access recipe:

- Enable One-time PIN IdP
- Create self-hosted app for `training.xbonell.com`
- Allow policy (owner email + require OTP)
- Session duration note
- Explicit warnings against Everyone / domain-wide email / OTP-only Include
- Verification checklist items
- Ops note: if OTP mail is filtered, allowlist Cloudflare’s notify sender per
  current Cloudflare docs at setup time
- Reminder: origin must stay non-public (API only on compose `web` network; no
  published `:8000`)

Optional one-line clarification in `docs/architecture.md` if Access wording is
still vague — no code or compose changes in this cut.

Outer-rim compose/nginx snippets stay as they are; Access is configured in the
Cloudflare dashboard (or Zero Trust UI), not in this monorepo’s runtime.

## 7. Verification

| Check | Expected |
|---|---|
| Incognito → `https://training.xbonell.com` | Access login / redirect, not SPA |
| Incognito → `https://training.xbonell.com/api/health` | Same gate (not a public 200 without login) |
| Owner email + OTP | SPA loads; `/api/health` OK with Access session |
| Non-allowlisted email | No usable session |

Revoke access by removing the email from the policy or disabling/deleting the
Access application.

## 8. Relationship to prior design

This spec implements the Access gate already assumed by
`2026-08-27-self-hosted-settings-deploy-design.md` (“Cloudflare Access is the
only login gate”). It does not reopen app-auth or topology decisions; it only
makes the operator recipe concrete for pre-go-live setup.
