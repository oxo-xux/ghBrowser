# ghBrowser

Password-protected cloud browser running in GitHub Actions with Cloudflare free tunnel.

No bot. No n8n. No Discord. Just Actions.

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
| `emulator_device` (Android only) | `GAPPS` | `GAPPS` (Play Store) or `VANILLA` |
| `screen` (Android only) | `1920x1080` | `1920x1080` / `1280x720` / `720x1280` |

URL appears in the job log and in the run Summary.

### 3. Login

Open URL → enter password → full browser.

- Default password source: `BASIC_AUTH_PASSWORD` secret
- Or enter a custom `vnc_password` at dispatch time
- Or set `auth_mode=none` for open access

## Workflows

- `Firefox` / `Brave` / `Chrome` — LinuxServer desktop browser + login page + Cloudflare tunnel
- `Android` — dockerify Android + scrcpy-web + login page + Cloudflare tunnel
- `Clean History` — manual wipe of completed run history (`confirm=DELETE-ALL`)
- `Auto Cleanup` — weekly 7-day retention (run history + commit squash)

## Architecture

```
Cloudflare Tunnel (*.trycloudflare.com)
  → python auth proxy :8080 (/auth/login)
    → Firefox/Brave/Chrome :3000 or scrcpy-web :8000
```
