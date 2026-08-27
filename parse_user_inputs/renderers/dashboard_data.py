"""
parse_user_inputs.renderers.dashboard_data
==========================================
Generates dashboard data JSON from real scan results.
Used by the interactive dashboard HTML.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from parse_user_inputs.models import Thread


def generate_dashboard_data(
    threads_by_platform: dict[str, list[Thread]],
) -> dict[str, Any]:
    """
    Generates complete dashboard data from real scan results.
    
    Returns:
        Dict with stats, platforms, projects, timeline, noAgent
    """
    # Collect all threads
    all_threads: list[Thread] = []
    for platform, threads in threads_by_platform.items():
        all_threads.extend(threads)
    
    # Stats
    total = len(all_threads)
    answered = sum(1 for t in all_threads if t.has_agent_response)
    open_count = sum(1 for t in all_threads if not t.has_agent_response and not t.has_interrupts)
    interrupts = sum(1 for t in all_threads if t.has_interrupts)
    rate = (answered / total * 100) if total > 0 else 0
    
    # Platforms
    platforms = []
    platform_colors = {
        'freebuff': '#8b5cf6',
        'claude_code': '#f59e0b',
        'hermes': '#3b82f6',
        'codex': '#10b981',
        'cursor': '#ef4444',
        'gemini_cli': '#06b6d4',
        'gemini_desktop': '#ec4899',
        'kilo_code': '#f97316',
        'cline': '#a855f7',
        'roo_code': '#22d3ee',
        'copilot': '#64748b',
        'aider': '#84cc16',
    }
    
    for platform_id, threads in threads_by_platform.items():
        if threads:
            platforms.append({
                'id': platform_id,
                'name': platform_id.replace('_', ' ').title(),
                'count': len(threads),
                'color': platform_colors.get(platform_id, '#6b7280'),
            })
    
    # Sort by count descending
    platforms.sort(key=lambda p: -p['count'])
    
    # Projects (group by project name)
    projects_dict: dict[str, dict] = {}
    for thread in all_threads:
        proj_name = thread.project or 'unknown'
        if proj_name not in projects_dict:
            projects_dict[proj_name] = {
                'name': proj_name,
                'threads': 0,
                'platforms': set(),
                'categories': {},
                'threadList': [],
            }
        
        proj = projects_dict[proj_name]
        proj['threads'] += 1
        proj['platforms'].add(thread.platform)
        
        for cat in thread.categories:
            proj['categories'][cat] = proj['categories'].get(cat, 0) + 1
        
        # Add thread summary (max 10 per project)
        if len(proj['threadList']) < 10:
            user_input = thread.user_input[:200] if thread.user_input else ''
            agent_reaction = thread.agent_reaction[:200] if thread.agent_reaction else ''
            
            proj['threadList'].append({
                'id': thread.id,
                'title': thread.title[:80],
                'platform': thread.platform,
                'date': thread.date,
                'cats': thread.categories[:5],
                'user': user_input,
                'agent': agent_reaction,
                'commit': thread.git_commits[0]['hash'] if thread.git_commits else None,
            })
    
    # Convert sets to lists and assign colors
    projects = []
    proj_colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#f97316']
    for i, (name, data) in enumerate(sorted(projects_dict.items(), key=lambda x: -x[1]['threads'])):
        data['platforms'] = list(data['platforms'])
        data['color'] = proj_colors[i % len(proj_colors)]
        projects.append(data)
    
    # Timeline (group by date)
    timeline_dict: dict[str, list] = {}
    for thread in all_threads:
        if thread.git_commits:
            for commit in thread.git_commits:
                date = commit.get('date', '')[:10]
                if date and date != '?':
                    if date not in timeline_dict:
                        timeline_dict[date] = []
                    timeline_dict[date].append({
                        'hash': commit.get('hash', '?')[:7],
                        'msg': commit.get('message', '?')[:60],
                        'proj': thread.project or '?',
                    })
    
    timeline = []
    for date in sorted(timeline_dict.keys(), reverse=True)[:10]:
        commits = timeline_dict[date]
        # Deduplicate by hash
        seen = set()
        unique_commits = []
        for c in commits:
            if c['hash'] not in seen:
                seen.add(c['hash'])
                unique_commits.append(c)
        timeline.append({
            'date': date,
            'commits': unique_commits[:10],
        })
    
    # No-agent threads
    no_agent = []
    for thread in all_threads:
        if not thread.has_agent_response:
            no_agent.append({
                'title': thread.title[:60],
                'platform': thread.platform,
                'date': thread.date,
                'user': (thread.user_input or '')[:100],
            })
    
    return {
        'stats': {
            'threads': total,
            'answered': answered,
            'open': open_count,
            'interrupts': interrupts,
            'rate': round(rate, 1),
        },
        'platforms': platforms,
        'projects': projects,
        'timeline': timeline,
        'noAgent': no_agent[:20],
    }


def save_dashboard_data(data: dict[str, Any], output_path: str) -> None:
    """Saves dashboard data as JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Dashboard data saved to: {output_path}")


def generate_and_save(threads_by_platform: dict[str, list[Thread]], output_path: str) -> None:
    """Generates and saves dashboard data."""
    data = generate_dashboard_data(threads_by_platform)
    save_dashboard_data(data, output_path)
    
    # Print summary
    print(f"\n=== Dashboard Data Summary ===")
    print(f"Stats: {data['stats']['threads']} threads, {data['stats']['answered']} answered, {data['stats']['rate']}% rate")
    print(f"Platforms: {len(data['platforms'])}")
    for p in data['platforms']:
        print(f"  {p['name']}: {p['count']}")
    print(f"Projects: {len(data['projects'])}")
    for p in data['projects'][:10]:
        print(f"  {p['name']}: {p['threads']} threads")
    print(f"Timeline: {len(data['timeline'])} days")
    print(f"No-agent: {len(data['noAgent'])} threads")
