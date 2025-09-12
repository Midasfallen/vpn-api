#!/usr/bin/env python3
"""Monitor GitHub Actions runs for a repo and download artifacts when available.

Usage:
  export GITHUB_TOKEN=ghp_...  # or pass --token
  python scripts/monitor_runs.py --repo Midasfallen/vpn-api --once

The script requires 'requests'.
"""
import argparse
import os
import time
from pathlib import Path

import requests


def api_get(url, token, params=None):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def download_file(url, token, dest: Path):
    # Try with Accept: application/octet-stream first (recommended),
    # but some endpoints may reject that header; on 415 retry without Accept.
    headers = {"Authorization": f"token {token}", "Accept": "application/octet-stream"}
    try:
        with requests.get(url, headers=headers, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
    except requests.exceptions.HTTPError as e:
        status = None
        try:
            status = e.response.status_code
        except Exception:
            pass
        if status == 415:
            # Retry without Accept header (let redirects / storage server decide)
            print("  server returned 415 Unsupported Media Type; retrying without Accept header...")
            headers = {"Authorization": f"token {token}"}
            with requests.get(url, headers=headers, stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
        else:
            # Re-raise with context
            print(f"  failed to download {url}: HTTP {status}")
            raise


def monitor(repo, token, poll_interval=30, once=False, outdir="artifacts/gh_monitor"):
    owner, name = repo.split("/")
    base = f"https://api.github.com/repos/{owner}/{name}"
    seen_runs = set()
    Path(outdir).mkdir(parents=True, exist_ok=True)
    try:
        while True:
            data = api_get(f"{base}/actions/runs", token, params={"branch": "main", "per_page": 50})
            runs = data.get("workflow_runs", [])
            for run in runs:
                run_id = run["id"]
                status = run.get("status")
                conclusion = run.get("conclusion")
                if run_id in seen_runs:
                    continue
                # only process finished runs
                if status != "completed":
                    continue
                print(f"Found completed run {run_id} - conclusion={conclusion}")
                seen_runs.add(run_id)
                # list artifacts
                art_json = api_get(f"{base}/actions/runs/{run_id}/artifacts", token)
                artifacts = art_json.get("artifacts", [])
                if not artifacts:
                    print("  no artifacts")
                    continue
                for a in artifacts:
                    name = a["name"]
                    url = a["archive_download_url"]
                    dest = Path(outdir) / str(run_id) / f"{name}.zip"
                    if dest.exists():
                        print(f"  artifact {name} already downloaded")
                        continue
                    print(f"  downloading artifact {name} to {dest}")
                    download_file(url, token, dest)
            if once:
                break
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Interrupted")


def validate_token(token):
    """Quick check: call the /user endpoint to validate the token and print the authenticated user.

    On 401, raise a SystemExit with a helpful message about PAT scopes and usage.
    """
    url = "https://api.github.com/user"
    try:
        user = api_get(url, token)
        login = user.get("login")
        uid = user.get("id")
        print(f"Authenticated to GitHub as: {login} (id: {uid})")
        return True
    except requests.exceptions.HTTPError as e:
        status = None
        try:
            status = e.response.status_code
        except Exception:
            pass
        print("\nGitHub API authentication failed.")
        if status == 401:
            print(
                "  -> HTTP 401 Unauthorized: token is invalid, expired, or missing required scopes."
            )
            print("  Required scopes:")
            print(
                "    - For classic PATs: 'repo' (for private repos) and 'workflow' or 'repo' to access Actions/artifacts."
            )
            print(
                "    - For fine-grained tokens: give the token 'Repository access' to this repo (Read) and 'Actions' -> Read access."
            )
            print(
                "  Confirm you didn't accidentally include quotes/newlines when passing the token, and that the token is current."
            )
        else:
            print(f"  -> HTTP {status}: {e}")
        # print a tiny diagnostic (no token content)
        print(f"  Diagnostic: token length = {len(token) if token else 0}")
        raise SystemExit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "Midasfallen/vpn-api"))
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    p.add_argument("--poll-interval", type=int, default=30)
    p.add_argument("--once", action="store_true")
    p.add_argument("--outdir", default="artifacts/gh_monitor")
    args = p.parse_args()
    if not args.token:
        print("GITHUB_TOKEN is required (set env var or pass --token)")
        raise SystemExit(1)
    # validate token first to provide clearer error messages for 401
    validate_token(args.token)
    monitor(
        args.repo, args.token, poll_interval=args.poll_interval, once=args.once, outdir=args.outdir
    )


if __name__ == "__main__":
    main()
