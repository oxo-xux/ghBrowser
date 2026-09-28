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
- `Chrome Proton` / `Brave Proton` — same + pre-installed Proton VPN extension (see below)
- `Auto Cleanup` — weekly 7-day retention (run history + commit squash)

## Proton VPN proxy (Chrome Proton / Brave Proton)

Yes — Proton works as a **browser-level HTTPS proxy**: the extension sets an `https://<server>:4443` proxy with per-session auth, so all in-browser traffic exits via Proton. Verified in the extension code: it does zero local DNS (`chrome.dns` unused) — Chromium sends `CONNECT host:port` and **the Proton exit resolves DNS**, except LAN addresses which go `DIRECT` via container DNS.

What the workflow does:

- Force-installs the official extension (`ExtensionInstallForcelist`, ID `jplgfhpmjnbigmhklmmbgecoobifkmpa`) — the only exception to the `["*"]` extension blocklist
- Managed policy pins: auto-connect on, **WebRTC-leak block locked on** (`disable_non_proxied_udp`, real IP can't leak), SecureCore off, telemetry + crash reports off
- Keeps SafeSearch / Safe Browsing / no-Incognito locks and the AdGuard host firewall

Two things to know before running it:

1. **Login is in-session**: open `account.proton.me` → sign in → click the Proton icon → Connect. Needs a Proton account (extension features are plan-gated).
2. **DNS caveat (checked)**: while VPN is connected, sites resolve via Proton — AdGuard Family does **not** filter VPN traffic. If you need the NSFW guarantee, use the plain Firefox/Brave/Chrome workflows instead.

## Architecture

```
Cloudflare Tunnel (*.trycloudflare.com)
  → python auth proxy :8080 (/auth/login)
    → Firefox/Brave/Chrome :3000
```
