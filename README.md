# ghBrowser

Password-protected cloud browser running in GitHub Actions with Cloudflare free tunnel.

No bot. No n8n. No Discord. Just Actions.

FamilySafe filtering is forced on every session: AdGuard Family DNS, SafeSearch locked on, NSFW blocked.

## Setup

### 1. Add GitHub Secret

**Settings > Secrets > Actions > New repository secret:**

| Secret | Value |
|---|---|
| `BASIC_AUTH_PASSWORD` | Your login password |

### 2. Run

**Actions > Firefox / Brave / Chrome > Run workflow**

Inputs:

| Input | Default | Notes |
|---|---|---|
| `duration` | `60` | 5-360 minutes |
| `auth_mode` | `password` | `password` or `none` |
| `vnc_password` | empty | Custom password for this run. Empty = use `BASIC_AUTH_PASSWORD` secret |

URL appears in the job log and in the run Summary.

### 3. Login

Open URL → enter password → full browser. Redesigned sign-in with show/hide password, Caps Lock warning, and loading state.

- Default password source: `BASIC_AUTH_PASSWORD` secret
- Or enter a custom `vnc_password` at dispatch time
- Or set `auth_mode=none` for open access

## FamilySafe filtering (forced, no bypass)

Every session pins DNS to **AdGuard Family Protection** and locks the browser down:

| Layer | What it does |
|---|---|
| Container DNS | `--dns=94.140.14.15 --dns=94.140.15.16` (Family: blocks adult + gambling, forces SafeSearch) |
| Host firewall | iptables drops all port 53 except AdGuard, drops DNS-over-TLS (853); IPv6 DNS blocked too |
| Host resolver | `/etc/resolv.conf` rewritten to AdGuard so nothing leaks to runner DNS |
| Firefox policy | DoH disabled + locked, proxy locked to system, `about:config` blocked, top adult domains blocklisted |
| Chrome / Brave policy | Secure DNS off, Google SafeSearch + YouTube SafetyMode forced, Safe Browsing enhanced, all extensions blocked, Incognito + Guest disabled |
| Self-test | Each run queries AdGuard DoH for an adult domain and confirms it resolves to `0.0.0.0` |

The user inside the browser has no shell, cannot install VPN/proxy extensions, and cannot switch the browser to private DNS — there is no settings path around the filter.

AdGuard Family endpoints: `94.140.14.15`, `94.140.15.16`, DoH `https://family.adguard-dns.com/dns-query`.

## Workflows

- `Firefox` / `Brave` / `Chrome` — LinuxServer desktop browser + login page + Cloudflare tunnel
- `Auto Cleanup` — weekly 7-day retention (run history + commit squash)

## Troubleshooting

- **Exit 143 during "Start tunnel"**: the runner host killed the step (GitHub maintenance/eviction or manual cancel) — not a workflow bug. Just re-run. If the log ends with the "runner shutdown" message, that confirms it.
- **Page stops loading mid-session**: the free tunnel dropped. The keep-alive loop health-checks the public URL every minute and restarts `cloudflared` automatically — grab the new URL from the log/Summary ("Tunnel restarted").

## Architecture

```
Cloudflare Tunnel (*.trycloudflare.com)
  → python auth proxy :8080 (/auth/login)
    → Firefox/Brave/Chrome :3000
```
