# ghBrowser

Password-protected cloud browser running in GitHub Actions with Cloudflare free tunnel.

## How It Works

- GitHub Actions spins up a full XFCE desktop + Firefox browser
- Nginx adds basic password protection
- Cloudflare free quick tunnel gives you a public `*.trycloudflare.com` URL
- Runs for **5 hours 50 minutes** per workflow dispatch
- **No server, no Cloudflare account needed** — everything runs in GitHub Actions

## Setup

### 1. Add GitHub Secret

Go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|---|---|
| `BASIC_AUTH_PASSWORD` | Your login password (any string, e.g. `mypassword123`) |

### 2. Run

Go to **Actions > Run Browser > Run workflow** and click "Run workflow".

The browser URL will appear in:
- The job log output
- The job summary page

### 3. Access

Open the URL → enter:
- **Username:** `admin`
- **Password:** your `BASIC_AUTH_PASSWORD` secret value

## Local Usage

```bash
docker compose up -d
# Open http://localhost:3000
# No password in local mode
```

## Architecture

```
Cloudflare Free Tunnel (*.trycloudflare.com)
    → Nginx (basic auth, port 8080)
        → LinuxServer Webtop (XFCE + Firefox, port 3000)
```

All running inside a GitHub Actions runner for 5h 50min.
