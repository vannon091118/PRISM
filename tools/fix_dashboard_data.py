#!/usr/bin/env python3
"""Fix JSON data for HTML embedding - escape backticks and problematic chars."""
import json
import re

with open('docs/screenshots/dashboard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix field names
for proj in data['projects']:
    if 'platforms' in proj:
        proj['platform'] = proj['platforms'][0] if proj['platforms'] else 'unknown'
        del proj['platforms']
    if 'categories' in proj:
        proj['cats'] = proj['categories']
        del proj['categories']

# Escape problematic strings for JS
def escape_for_js(s):
    if not isinstance(s, str):
        return s
    s = s.replace('\\', '\\\\')
    s = s.replace('`', '\\`')
    s = s.replace('${', '\\${')
    s = s.replace("'", "\\'")
    s = s.replace('\n', ' ')
    s = s.replace('\r', '')
    # Remove non-printable chars
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    return s

def escape_obj(obj):
    if isinstance(obj, str):
        return escape_for_js(obj)
    elif isinstance(obj, dict):
        return {k: escape_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [escape_obj(v) for v in obj]
    return obj

data = escape_obj(data)

# Save fixed data
with open('docs/screenshots/dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Now update the HTML
with open('parse_user_inputs/templates/interactive_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

data_js = 'const DATA = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';'
html = re.sub(r'const DATA = \{.*?\};\s*\n', data_js + '\n\n', html, flags=re.DOTALL)

with open('parse_user_inputs/templates/interactive_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Fixed and updated!')
print(f'Stats: {data["stats"]["threads"]} threads, {data["stats"]["answered"]} answered')
print(f'Platforms: {len(data["platforms"])}')
print(f'Projects: {len(data["projects"])}')
