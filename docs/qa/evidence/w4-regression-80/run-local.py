"""W4 evidence adapter. Run from the clean repository root with Python 3.11+ on Windows.

Uses original assertions unchanged against an owned disposable WSL Docker project.
Does not set GITHUB_ACTIONS or edit the original catalogue, runners or business code.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'docs/qa/evidence/w4-regression-80'
PROJECT = 'ouc-w4-20261118-7c67518'
BASE = 'http://127.0.0.1:18084'
COMMIT = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert COMMIT == '7c67518fc91583a3983ea265b85f6d2a54d12eab', 'Pin the tested revision'
assert os.name == 'nt', 'This adapter uses the Windows -> WSL Docker transport'
sys.path.insert(0, str(ROOT / 'scripts/qa'))
os.environ.update(TEST_BASE_URL=BASE, PYTHONUTF8='1')
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))

def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Every original docker subprocess is routed to this specific daemon and project.
native_run = subprocess.run
def docker_transport(command, *args, **kwargs):
    if isinstance(command, (list, tuple)) and command and command[0] == 'docker':
        parts = list(command[1:])
        if parts[0] == 'compose':
            parts[1:1] = ['--project-name', PROJECT]
        forwarded = ['env', 'ANON_ID_SECRET='] if kwargs.get('env', {}).get('ANON_ID_SECRET') == '' else []
        command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--exec', *forwarded, 'docker',
                   '--host', 'unix:///var/run/docker.sock', *parts]
    if kwargs.get('text') and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
        kwargs['errors'] = 'replace'
    return native_run(command, *args, **kwargs)
subprocess.run = docker_transport

import regression_http as http
from regression_stack import Stack
import regression_auth, regression_checkin, regression_treehole, regression_match
import regression_moderation, regression_plan
import execute_stack_cases
import run_us25_security

trace = []
active = None
execution = []

def safe(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if any(part in k.lower() for part in ('token', 'password', 'secret')) else safe(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    return value

original_request = http.Client.request
def request(self, path, payload=None, raw=None, headers=None, method=None):
    start = now()
    status, body = original_request(self, path, payload, raw, headers, method)
    parsed = urllib.parse.urlsplit(path)
    query = urllib.parse.parse_qs(parsed.query)
    entry = {'kind': 'http', 'time': start, 'method': method or ('POST' if payload is not None or raw is not None else 'GET'),
             'path': parsed.path, 'query': safe(query), 'authenticated': self.token is not None,
             'input': safe(payload), 'http_status': status, 'response': safe(body)}
    if raw is not None:
        entry['raw_input'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                              'text': raw.decode('utf-8', errors='replace') if len(raw) < 200 else None,
                              'construction': "b'x' * 16385" if raw == b'x' * 16385 else None}
    if headers:
        entry['header_names'] = sorted(headers)
    if active is not None:
        trace.append(entry)
    return status, body
http.Client.request = request

original_sql = Stack.sql
def sql(self, statement):
    result = original_sql(self, statement)
    if active is not None:
        trace.append({'kind': 'mysql', 'time': now(), 'sql': statement, 'output': result})
    return result
Stack.sql = sql
original_redis = Stack.redis
def redis(self, *arguments):
    result = original_redis(self, *arguments)
    if active is not None:
        trace.append({'kind': 'redis', 'time': now(), 'arguments': list(arguments), 'output': result})
    return result
Stack.redis = redis

original_case = http.Runner.run
def run(self, identifier, check, scope='HTTP + isolated MySQL/Redis, authenticated test account'):
    global active
    active = identifier
    offset, start = len(trace), now()
    original_case(self, identifier, check, scope)
    row = self.results[-1]
    row.update(started_at=start, finished_at=now(), source_commit=COMMIT,
               execution_trace=trace[offset:], executed=True)
    execution.append(row)
    save('execution-progress.json', execution)
    print(identifier, row['status'], row.get('reason') or '', flush=True)
    active = None
http.Runner.run = run

def main():
    global active
    stack = Stack()
    # Precondition: only our project, empty new database, explicit fixture identity provider.
    ps = subprocess.check_output(['docker', 'compose', '--env-file', '.env', '-f', 'infra/docker-compose.yml', 'ps', '--format', 'json'], text=True)
    assert PROJECT in ps
    assert stack.count('users') == 0 and stack.count('checkin') == 0
    initial = {'recorded_at': now(), 'source_commit': COMMIT, 'project': PROJECT,
               'database_rows': {t: stack.count(t) for t in ('users', 'auth', 'checkin', 'treehole_post', 'treehole_archive', 'buddy_demand')},
               'services': [json.loads(line) for line in ps.splitlines() if line.strip()]}
    # Avoid embedding resolved Compose environment/credentials.
    initial['services'] = [{k: r.get(k) for k in ('Service', 'State', 'Health', 'Image', 'Project', 'Publishers')} for r in initial['services']]
    save('initial-state.json', initial)
    client = http.Client(BASE).authenticate()
    runner = http.Runner(client)
    for module in (regression_auth, regression_checkin, regression_treehole, regression_moderation, regression_match):
        module.register(runner, stack)
    regression_plan.register_blocked(runner)
    for row in runner.results:
        row.setdefault('started_at', now())
        row.setdefault('finished_at', now())
        row.setdefault('source_commit', COMMIT)
        row.setdefault('executed', False)
        row.setdefault('execution_trace', [])
    save('api-results.json', runner.results)

    # Probe each blocked student-verification prerequisite separately with synthetic inputs.
    for number, data in [(7, {'studentId': 'SYNTHETIC-W4-001'}), (8, {'studentId': 'SYNTHETIC-W4-001'}), (9, {}), (10, {'status': 'REJECTED'}), (11, {'studentId': 'SYNTHETIC-W4-001'}), (12, None)]:
        row = next(r for r in runner.results if r['case_id'] == f'S1-{number:03}')
        active, offset = row['case_id'], len(trace)
        row['started_at'] = now()
        actor = http.Client(BASE) if number in (11, 12) else client
        path = '/api/auth/student-verify' if number != 12 else '/api/auth/student-verify/screenshot/synthetic-w4'
        status, _ = actor.request(path, data)
        row.update(finished_at=now(), execution_trace=trace[offset:], prerequisite_attempted=True,
                   reason='校内认证与截图授权接口尚未实现；HTTP 前置探测不能代替原业务步骤。')
        active = None

    # Exercise streak behavior; retain BLOCKED because current streak-reset rule lacks M1 sign-off.
    def streak_probe():
        actor = http.Client(BASE).authenticate()
        from datetime import date
        today = date.fromisoformat(stack.execute('exec', '-T', 'api', 'date', '+%F'))
        for delta in (3, 2):
            status, _ = actor.request('/api/emotions/checkins', {'emotion': 'CALM', 'intensity': 3, 'checkinDate': (today - timedelta(days=delta)).isoformat()})
            http.expect(status == 200, 'streak fixture failed')
        actor.request('/api/emotions/checkins')
    runner.run('W4-STREAK-TECHNICAL', streak_probe)

    def expiry_detail_probe():
        status, post = client.request('/api/treehole/posts', {'content': 'W4 expiry detail fixture', 'emotionTag': 'CALM'})
        http.expect(status == 201, 'detail probe publication failed')
        path = '/api/treehole/posts/' + str(post['id'])
        fresh, _ = client.request(path)
        stack.sql("UPDATE treehole_post SET expires_at='2000-01-01' WHERE id=" + str(int(post['id'])))
        expired, _ = client.request(path)
        http.expect(fresh == expired == 404, 'Detail route changed; inspect implementation')
        client.observations.append({'fresh_detail_http': fresh, 'expired_detail_http': expired, 'expiry_acceptance': False})
    runner.run('W4-EXPIRY-DETAIL-PREREQUISITE', expiry_detail_probe)

    # Original infrastructure script, through the same transport, without altering source.
    old_argv = sys.argv
    stack_started = now()
    sys.argv = ['execute_stack_cases.py', '--output', str(OUT / 'stack-results.json')]
    try:
        execute_stack_cases.main()
    finally:
        sys.argv = old_argv
    infrastructure = json.loads((OUT / 'stack-results.json').read_text(encoding='utf-8'))
    infrastructure.update(started_at=stack_started, finished_at=now())
    save('stack-results.json', infrastructure)

    def gateway_probe():
        for path, payload, expected in [('/', None, 200), ('/api/moderation/check', {'text':'傻 逼'}, 200),
                ('/api/moderation/check', {'text':'一起去图书馆'}, 200), ('/api/moderation/check', {'text':' '}, 422),
                ('/api/emotions/checkins', None, 200), ('/internal/health', None, 404),
                ('/api/moderation/check', {'text':'好'*6000}, 413)]:
            status, _ = client.request(path, payload)
            http.expect(status == expected, 'gateway recheck failed')
    runner.run('W4-GATEWAY-TRACE', gateway_probe)

    # Run actual JWT, owner isolation, DB-role and PII assertions on this owned stack.
    values = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    diagnostics = {}
    security, pii = run_us25_security.execute(BASE, values, diagnostics)
    save('security-results.json', {'executed_at': now(), 'source_commit': COMMIT,
         'results': security, 'runtime_pii_scan': pii, 'database_initialization': diagnostics.get('database_initialization'),
         'live_wechat_verified': False, 'independent_business_review': 'pending'})

    def split_schema():
        schema = stack.sql("SELECT TABLE_NAME,COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN ('users','auth','treehole_post','treehole_identity','treehole_public') ORDER BY TABLE_NAME,ORDINAL_POSITION")
        http.expect('treehole_identity\tuser_id' in schema and 'auth\tstudent_no' in schema, 'Private tables missing')
        http.expect('treehole_post\tuser_id' not in schema, 'Identity in public content table')
        http.expect('users\tstudent_no' not in schema and 'users\tphone' not in schema, 'Identity fields not separated')
        http.expect(all(r['status'] == 'PASS' for r in security), 'Security prerequisites failed')
        client.observations.append({'security_checks': 20, 'all_passed': True, 'anonymous_mapping_private': True})
    runner.run('W4-IDENTITY-SPLIT', split_schema)
    save('api-results.json', runner.results)
    save('final-state.json', {'recorded_at': now(), 'source_commit': COMMIT,
         'database_rows': {t: stack.count(t) for t in ('users','auth','checkin','treehole_post','treehole_archive','buddy_demand')},
         'queue_entries': int(stack.redis('ZCARD','treehole:burn_queue'))})
    print('Catalogue HTTP:', dict(Counter(r['status'] for r in runner.results if r['case_id'].startswith('S1-'))))

if __name__ == '__main__':
    main()
