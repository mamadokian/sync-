#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

TOKEN = os.environ['GITHUB_TOKEN']
SOURCE_OWNER = os.environ.get('SOURCE_OWNER', 'source-org')
SOURCE_REPO = os.environ.get('SOURCE_REPO', 'source-repo')
PRIVATE_OWNER = os.environ.get('PRIVATE_OWNER', 'your-username')
PRIVATE_REPO = os.environ.get('PRIVATE_REPO', 'your-private-repo')

def log(msg):
    print(msg, flush=True)

def api_call(method, path, data=None):
    url = f'https://api.github.com/{path}'
    headers = {
        'Authorization': f'token {TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'repo-sync',
    }
    body = json.dumps(data).encode() if data else None
    if body:
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        if e.code in (404, 422):
            return None, e.code
        log(f'API error: {e.code} {e.reason}')
        return None, e.code

def get_branches(owner, repo):
    branches = {}
    page = 1
    while True:
        log(f'Fetching page {page}...')
        data, status = api_call('GET', f'repos/{owner}/{repo}/branches?per_page=100&page={page}')
        if not data or status != 200:
            break
        for b in data:
            branches[b['name']] = b['commit']['sha']
        if len(data) < 100:
            break
        page += 1
        # Rate limit safety: 100 requests per minute for authenticated
        if page % 30 == 0:
            log('Rate limit pause...')
            time.sleep(2)
    return branches

def delete_branch_api(owner, repo, branch):
    encoded = urllib.parse.quote(branch, safe='')
    api_call('DELETE', f'repos/{owner}/{repo}/git/refs/heads/{encoded}')

def git(*args):
    cmd = ['git'] + list(args)
    log(f'$ {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True, text=True, cwd='/app/repo-mirror.git')
    if result.stdout:
        log(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        log(f'ERROR: {result.stderr.strip()}')
    return result.returncode == 0

def main():
    log(f'=== Sync started at {time.strftime("%Y-%m-%d %H:%M:%S")} ===')
    
    mirror = '/app/repo-mirror.git'
    if not os.path.isdir(mirror):
        os.makedirs(mirror, exist_ok=True)
        subprocess.run(['git', 'init', '--bare', mirror], check=True)
        git('remote', 'add', 'source', f'https://github.com/{SOURCE_OWNER}/{SOURCE_REPO}.git')
        git('remote', 'add', 'private', f'https://{TOKEN}@github.com/{PRIVATE_OWNER}/{PRIVATE_REPO}.git')
    
    log('Getting source branches...')
    source = get_branches(SOURCE_OWNER, SOURCE_REPO)
    log(f'  Source: {len(source)} branches')
    
    log('Getting private branches...')
    private = get_branches(PRIVATE_OWNER, PRIVATE_REPO)
    log(f'  Private: {len(private)} branches')
    
    to_fetch = [b for b, sha in source.items() if b not in private or private[b] != sha]
    to_delete = [b for b in private if b not in source]
    
    log(f'Update/create: {len(to_fetch)}, Delete: {len(to_delete)}')
    
    if not to_fetch and not to_delete:
        log('Nothing to do.')
        return
    
    # Fetch only changed branches (batches of 100 to reduce git calls)
    batch = 100
    for i in range(0, len(to_fetch), batch):
        chunk = to_fetch[i:i+batch]
        log(f'Fetching batch {i//batch + 1}/{(len(to_fetch)-1)//batch + 1} ({len(chunk)} branches)...')
        # Fetch as refs, not full clone
        refs = [f'+refs/heads/{b}:refs/heads/{b}' for b in chunk]
        git('fetch', 'source', *refs)
    
    # Push to private
    for i in range(0, len(to_fetch), batch):
        chunk = to_fetch[i:i+batch]
        log(f'Pushing batch {i//batch + 1}...')
        refs = [f'+{b}:{b}' for b in chunk]
        git('push', 'private', *refs)
    
    # Delete removed branches
    for b in to_delete:
        log(f'Deleting {b}')
        if not git('push', 'private', '--delete', b):
            delete_branch_api(PRIVATE_OWNER, PRIVATE_REPO, b)
    
    log('=== Sync completed ===')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(f'FATAL: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
