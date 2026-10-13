# ghBrowser

Password-protected cloud browser running in GitHub Actions with Cloudflare free tunnel.

No bot. No n8n. No Discord. Just Actions.

No content filtering. Sessions resolve DNS through Cloudflare (`1.1.1.1`) for speed.

## Setup

### 1. Add GitHub Secret

**Settings > Secrets > Actions > New repository secret:**

| Secret | Value |
|---|---|
| `BASIC_AUTH_PASSWORD` | Your login password |

### 2. Run

**Actions > Firefox / Brave / Chrome / Android > Run workflow**

Inputs:

| Input | Default | Notes |
|---|---|---|
| `duration` | `60` | 5-360 minutes |
| `auth_mode` | `password` | `password` or `none` |
| `vnc_password` | empty | Custom password for this run. Empty = use `BASIC_AUTH_PASSWORD` secret |
| `android_version` | `11.0` | Android only: `9.0`, `10.0`, `11.0`, `12.0`, `13.0`, `14.0` |

URL appears in the job log and in the run Summary.

### 3. Login

Open URL → enter password → full browser. Redesigned sign-in with show/hide password, Caps Lock warning, and loading state.

- Default password source: `BASIC_AUTH_PASSWORD` secret
- Or enter a custom `vnc_password` at dispatch time
- Or set `auth_mode=none` for open access

## DNS

Every session pins DNS to **Cloudflare** for fast resolution:

| Layer | What it does |
|---|---|
| Container DNS | `--dns=1.1.1.1 --dns=1.0.0.1` |
| Host resolver | `/etc/resolv.conf` rewritten to Cloudflare so nothing leaks to runner DNS |

No content filtering, SafeSearch enforcement, or extension lockdown is applied. Anyone with the URL and password gets an unrestricted browser.

## Workflows

- `Firefox` / `Brave` / `Chrome` — LinuxServer desktop browser + login page + Cloudflare tunnel
- `Android` — ugphone-style cloud phone (Samsung Galaxy S10 emulator + noVNC web + login page + Cloudflare tunnel). Same password inputs as browsers, plus `android_version` to pick the Android release.
- `Auto Cleanup` — weekly 7-day retention (run history + commit squash)

## Troubleshooting

- **"You are using an unsupported command-line flag: --no-sandbox"** (Brave/Chrome infobar): the LinuxServer image hardcodes `--no-sandbox` in `/usr/bin/wrapped-brave`. The flag is required in the container, so the infobar is suppressed with `BRAVE_CLI=--test-type`.
- **Tor Browser installs but never launches** (spinner on "Launch torbrowser"): the Tor app runs under PRoot, and Docker's default seccomp profile blocks `ptrace` without `CAP_SYS_PTRACE`. Sessions are started with `--cap-add=SYS_PTRACE`; the "Verify proot-apps" step prints `selkies-proot check` output if it still fails.
- **Exit 143 during "Start tunnel"**: the runner host killed the step (GitHub maintenance/eviction or manual cancel) — not a workflow bug. Just re-run. If the log ends with the "runner shutdown" message, that confirms it.
- **Page stops loading mid-session**: the free tunnel dropped. The keep-alive loop health-checks the public URL every minute and restarts `cloudflared` automatically — grab the new URL from the log/Summary ("Tunnel restarted").

## Architecture

```
Cloudflare Tunnel (*.trycloudflare.com)
  → python auth proxy :8080 (/auth/login)
    → Firefox/Brave/Chrome :3000 (KasmVNC web)
    → Android :6080 (noVNC web → emulator)
```
