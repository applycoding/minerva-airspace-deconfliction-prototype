"""Measured campaign reports; screenshots are embedded for offline review."""
import base64
from datetime import datetime, timezone
import html
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

LIMITS = [
    'Simulation only; never flown. No physical aircraft, autopilot, radio or live air traffic control was exercised. Outdoor range testing and Range Control integration remain for later readiness work.',
    'Altitudes use a flat ground reference, with 750 m AMSL for SITL home. No terrain elevation, wind shear, terrain masking, multipath or antenna radiation patterns are modelled. Uniform surface wind and gust limits apply.',
    'RF uses ITU-R P.525 free-space screening, fixed 2 m GCS receivers and a 10 m near-field clamp; it is not a coverage prediction.',
    'Zones, crewed plans and METARs come from local files. The shipped Handbook issue ends on 29 October 2026 and needs rechecking before operational use. NOTAM overrides are manual; Flight Levels are unsupported.',
    'Loopback MAVLink UDP is unencrypted and unauthenticated; message signing is not verified. Local socket testing does not establish physical datalink performance.',
    'The spatial grid planner is bounded to 40000 expansions and a 9.5 s search deadline, not globally optimal. Dense intersecting traffic may require operator intervention.',
    "These tests are engineering evidence offered towards a readiness assessment; the assessment itself is the applicant's responsibility. Windows source and frozen results require execution on Windows and cannot be inferred from Linux results."
]


def environment():
    versions={}
    for package,module in [('PySide6-Essentials','PySide6'),('shapely','shapely'),('pyproj','pyproj'),('numpy','numpy')]:
        try: version=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: version=getattr(importlib.import_module(module),'__version__','unknown')
        versions[package]=version
    cpu=platform.processor()
    if not cpu and Path('/proc/cpuinfo').exists():
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'): cpu=line.split(':',1)[1].strip();break
    return dict(os_name=platform.platform(),platform_tag='windows-2022' if os.name=='nt' and os.getenv('GITHUB_ACTIONS') else 'ubuntu-24.04' if os.getenv('GITHUB_ACTIONS') else 'local',cpu_model=cpu or platform.machine(),cpu_count=os.cpu_count(),python_version=platform.python_version(),frozen_executable=bool(getattr(sys,'frozen',False)),package_versions=versions)


def provenance():
    sha=os.environ.get('GITHUB_SHA')
    if not sha:
        try: sha=subprocess.check_output(['git','rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True,timeout=5).strip()
        except (OSError,subprocess.SubprocessError): sha='unavailable'
    names=('GITHUB_SERVER_URL','GITHUB_REPOSITORY','GITHUB_RUN_ID')
    url='/'.join([os.environ[n].rstrip('/') for n in names[:2]])+'/actions/runs/'+os.environ[names[2]] if all(os.getenv(n) for n in names) else None
    return dict(git_commit_sha=sha,run_url=url,generated_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))


def write_reports(root,report):
    root=Path(root)
    (root/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    lines=['# MINERVA integrated scenario campaign','',report['statement'],'',report['verdict_line'],'',
           f"Author: Arpan Bom. UTC: {report['generated_at_utc']}. Git: {report['git_commit_sha']}.",'',
           '| Scenario | Status | Wall seconds |','| --- | --- | --- |']
    for s in report['scenarios']: lines.append(f"| {s['scenario_id']} | {s['status']} | {s['wall_time_s']:.3f} |")
    for s in report['scenarios']:
        lines.extend(['',f"## {s['scenario_id']}",'',s.get('reason',''),'','| Target | Expected | Measured | Pass |','| --- | --- | --- | --- |'])
        for t in s['targets']:
            measured=json.dumps(t['measured'],ensure_ascii=False).replace('|','/')
            lines.append(f"| {t['description']} | {t['expected']} | {measured} | {t['passed']} |")
        if s.get('error'): lines.extend(['','```',s['error'],'```'])
    lines.extend(['','## Limits','']+['- '+limit for limit in LIMITS])
    markdown='\n'.join(lines)+'\n'; (root/'report.md').write_text(markdown,encoding='utf-8')
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><title>MINERVA campaign</title><style>body{font:15px system-ui;margin:2em;max-width:1500px}pre{white-space:pre-wrap}img{max-width:100%;border:1px solid #888}summary{cursor:pointer}</style><h1>MINERVA integrated scenario campaign</h1>', '<pre>'+html.escape(markdown)+'</pre>']
    for s in report['scenarios']:
        for filename in s['screenshots']:
            data=base64.b64encode((root/filename).read_bytes()).decode('ascii')
            parts.append(f'<details><summary>{html.escape(filename)}</summary><img alt="{html.escape(filename)}" src="data:image/png;base64,{data}"></details>')
    parts.append('</html>'); (root/'report.html').write_text('\n'.join(parts),encoding='utf-8')
