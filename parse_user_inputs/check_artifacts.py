import sys, json, urllib.request, os
sys.stdout.reconfigure(encoding='utf-8')

resp = urllib.request.urlopen('http://127.0.0.1:55703/api/projects', timeout=5)
data = json.loads(resp.read())

print('=== FREEBUFF ARTEFAKTE ===')
total_deliveries = 0
total_branches = 0
total_completed = 0

for proj in data['projects']:
    name = os.path.basename(proj.get('path', '')) or 'root'
    for t in proj.get('threads', []):
        title = t.get('title', '')[:50]
        deliveries = t.get('deliveries', [])
        branch = t.get('branch')
        outcome = t.get('lastTurnOutcome')
        model = t.get('model')
        
        if deliveries:
            total_deliveries += len(deliveries)
            for d in deliveries:
                kind = d.get('kind', '')
                status = d.get('status', '')
                url = d.get('url', '')
                number = d.get('number', '')
                print(f'  [{name}] {title}')
                print(f'    DELIVERY: {kind} #{number} status={status}')
                if url:
                    print(f'    URL: {url}')
        
        if branch:
            total_branches += 1
            print(f'  [{name}] {title}')
            print(f'    BRANCH: {branch[:80]}')
        
        if outcome == 'completed':
            total_completed += 1

print(f'\nZusammenfassung:')
print(f'  Deliveries (PRs): {total_deliveries}')
print(f'  Branches: {total_branches}')
print(f'  Completed: {total_completed}')

# Auch Git-Commits checken
from parse_user_inputs.sources.git_reader import read_commits
for proj in data['projects']:
    name = os.path.basename(proj.get('path', '')) or 'root'
    if name in ('snippet-empire', 'user_inputs_parser'):
        proj_path = proj.get('path', '')
        commits = read_commits(proj_path, max_count=10)
        if commits:
            print(f'\n  [{name}] Git Commits: {len(commits)}')
            for c in commits[:3]:
                print(f'    {c["hash"]} {c["message"][:50]} +{c["insertions"]}/-{c["deletions"]}')
