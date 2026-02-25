#!/usr/bin/env python3
"""
Scout publisher for FundFish blog.
Reads JSON from stdin, writes a markdown file to the blog/ directory, and git pushes.
Netlify auto-deploys on push.

Input JSON:
{
  "title": "...",
  "description": "...",
  "content": "...",  // markdown body
  "tags": ["...", "..."],
  "date": "YYYY-MM-DD"  // optional, defaults to today
}
"""

import sys, json, os, re, subprocess
from datetime import date

def slugify(title):
    slug = title.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:80]

data = json.loads(sys.stdin.read())
today = data.get('date', str(date.today()))
title = data['title']
slug = data.get('slug') or slugify(title)
description = data.get('description', '')
tags = data.get('tags', [])
content = data['content']

# Frontmatter
frontmatter = f"""---
title: "{title}"
date: "{today}"
description: "{description}"
tags: [{', '.join(f'"{t}"' for t in tags)}]
---

"""

blog_dir = os.path.expanduser('~/projects/perscholas-fundraising-demo/frontend/content')
filename = f"{today}-{slug}.md"
filepath = os.path.join(blog_dir, filename)

# Write the file
with open(filepath, 'w') as f:
    f.write(frontmatter + content)

print(f"Written: {filepath}")

# Git add + commit + push
repo_dir = os.path.expanduser('~/projects/perscholas-fundraising-demo')
subprocess.run(['git', 'add', f'frontend/content/{filename}'], cwd=repo_dir, check=True)
subprocess.run(['git', 'commit', '-m', f'feat(blog): add "{title}"'], cwd=repo_dir, check=True)
subprocess.run(['git', 'push'], cwd=repo_dir, check=True)
print("Pushed to git — Netlify will rebuild automatically")
print(json.dumps({"slug": slug, "file": filename, "url": f"https://fundfish.pro/blog/{slug}"}))
