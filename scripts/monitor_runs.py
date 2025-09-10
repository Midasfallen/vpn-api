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
import requests
from pathlib import Path


def api_get(url, token, params=None):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def download_file(url, token, dest: Path):
    headers = {"Authorization": f"token {token}", "Accept": "application/octet-stream"}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)


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
    monitor(args.repo, args.token, poll_interval=args.poll_interval, once=args.once, outdir=args.outdir)


if __name__ == "__main__":
    main()
