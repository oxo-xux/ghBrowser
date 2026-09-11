# ghBrowser

Password-protected cloud browser running in GitHub Actions with Cloudflare free tunnel.

## Setup

### 1. Add GitHub Secret

**Settings > Secrets > Actions > New repository secret:**

| Secret | Value |
|---|---|
| `BASIC_AUTH_PASSWORD` | Your login password |

### 2. Run

**Actions > Run Browser > Run workflow**

URL appears in the job log and summary.

### 3. Login

Open URL → enter password → full Firefox browser.

## Architecture

```
Cloudflare Tunnel (*.trycloudflare.com)
  → nginx (basic auth + login page)
    → LinuxServer Firefox (port 3000)
```
