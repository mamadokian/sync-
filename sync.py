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
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        if e.code in (404, 422):
            return None, e.code
        raise

def get_branches(owner, repo):
    branches = {}
    page = 1
    while True:
        data, _ = api_call('GET', f'repos/{owner}/{repo}/branches?per_page=100&page={page}')
        if not data:
            break
        for b in data:
            branches[b['name']] = b['commit']['sha']
        if len(data) < 100:
            break
        page += 1
    return branches

def delete_branch_api(owner, repo, branch):
    encoded = urllib.parse.quote(branch, safe='')
    api_call('DELETE', f'repos/{owner}/{repo}/git/refs/heads/{encoded}')

def git(*args):
    cmd = ['git'] + list(args)
    print(f'$ {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    print(f'Starting sync at {time.strftime("%Y-%m-%d %H:%M:%S")}')
    
    mirror = '/app/repo-mirror.git'
    if not os.path.isdir(mirror):
        os.makedirs(mirror, exist_ok=True)
        subprocess.run(['git', 'init', '--bare', mirror], check=True)
        os.chdir(mirror)
        git('remote', 'add', 'source', f'https://github.com/{SOURCE_OWNER}/{SOURCE_REPO}.git')
        git('remote', 'add', 'private', f'https://{TOKEN}@github.com/{PRIVATE_OWNER}/{PRIVATE_REPO}.git')
    else:
        os.chdir(mirror)
    
    print('Getting source branches...')
    source = get_branches(SOURCE_OWNER, SOURCE_REPO)
    print(f'  {len(source)} branches')
    
    print('Getting private branches...')
    private = get_branches(PRIVATE_OWNER, PRIVATE_REPO)
    print(f'  {len(private)} branches')
    
    to_fetch = [b for b, sha in source.items() if b not in private or private[b] != sha]
    to_delete = [b for b in private if b not in source]
    
    print(f'Update/create: {len(to_fetch)}, Delete: {len(to_delete)}')
    
    # Fetch only changed branches (batches of 50)
    batch = 50
    for i in range(0, len(to_fetch), batch):
        chunk = to_fetch[i:i+batch]
        refs = [f'{b}:{b}' for b in chunk]
        git('fetch', 'source', *refs)
    
    # Force-push to mirror exactly
    for i in range(0, len(to_fetch), batch):
        chunk = to_fetch[i:i+batch]
        refs = [f'+{b}:{b}' for b in chunk]
        git('push', 'private', *refs)
    
    # Delete branches removed from source
    for b in to_delete:
        print(f'Deleting {b}')
        if not git('push', 'private', '--delete', b):
            delete_branch_api(PRIVATE_OWNER, PRIVATE_REPO, b)
    
    print('Done')

if __name__ == '__main__':
    main()
