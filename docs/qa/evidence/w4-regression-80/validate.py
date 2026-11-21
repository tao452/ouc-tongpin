"""Check report completeness, provenance, invariants and accidental credential retention."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

root=Path.cwd(); out=root/'docs/qa/evidence/w4-regression-80'
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
report=read(out/'results.json'); rows=report['results']
catalogue=read(root/'docs/qa/s1-test-cases.json')['cases']
history=read(root/'docs/qa/evidence/regression-20261109/catalogue-results.json')['results']
cases={c['id']:c for c in catalogue}; previous={r['case_id']:r for r in history}
assert len(rows)==80 and {r['id'] for r in rows}==set(cases)
for row in rows:
    case=cases[row['id']]
    assert row['title']==case['title'] and row['expected']==case['expected'] and row['original_steps']==case['steps']
    assert row['historical_status']==previous[row['id']]['status']
    assert row['status'] in ('PASS','FAIL','BLOCKED') and row['attempted']
    assert row['current_commit']==report['source_commit']
    assert row['actual_execution_steps'] and all((out/f).is_file() for f in row['evidence_files'])
    datetime.fromisoformat(row['test_time'])
    if row['status']=='PASS': assert row['executed']
    if row['status']=='BLOCKED': assert row['blocked_reason'] and row['owners']
    if row['status']=='FAIL': assert row['failure_reason']
counts=Counter(r['status'] for r in rows)
assert all(report['status_counts'][k]==counts[k] for k in ('PASS','FAIL','BLOCKED'))
assert Counter(r['module'] for r in rows)==Counter(c['module'] for c in catalogue)
assert read(out/'java-results.json')['java_test_totals']=={'tests':141,'failures':0,'errors':0,'skipped':0}
assert len(read(out/'junit-cases.json')['cases'])==141
security=read(out/'security-results.json')['results']
assert len(security)==20 and all(r['status']=='PASS' for r in security)
phrases=read(out/'phrase-results.json')['results']
assert len(phrases)==8 and all(r['status']=='PASS' for r in phrases)
cleanup=read(out/'cleanup.json')
assert cleanup['exit_code']==0 and all(not cleanup[k] for k in ('remaining_containers','remaining_volumes','remaining_networks'))
assert len(cleanup['existing_demo_read_only_check'])==5
originals=['docs/qa/s1-test-cases.json','docs/qa/evidence/regression-20261109']
assert subprocess.run(['git','diff','--exit-code','--',*originals],capture_output=True).returncode==0
assert subprocess.run(['git','diff','--exit-code','--','apps','infra','services','scripts'],capture_output=True).returncode==0
required=['results.json','comparison.md','test-report.md','blocked-items.md','environment.md']
assert all((out/f).is_file() for f in required)
files=[p for p in out.iterdir() if p.is_file() and p.suffix in ('.md','.json','.py') and p.name not in ('manifest.json','validation.json')]
# Archive text in LF so the byte hashes also verify in Git/Linux checkouts.
for path in files:
    path.write_bytes(path.read_text(encoding='utf-8').encode('utf-8'))
assert all(p.stat().st_size<=5242880 for p in files)
text='\n'.join(p.read_text(encoding='utf-8') for p in files)
env=root/'.env'
values=dict(line.split('=',1) for line in env.read_text().splitlines() if '=' in line) if env.exists() else {}
secret_hits=sum(value in text for name,value in values.items() if any(x in name for x in ('SECRET','PASSWORD')) and len(value)>=12)
assert secret_hits==0
assert not re.search(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{16,}',text)
assert ('studentNo='+'SYNTHETICSTUDENT001 phone='+'13900001234') not in text
inputs=('docs/qa/s1-test-cases.json','docs/qa/evidence/regression-20261109/catalogue-results.json','packages/contract/openapi.yaml','infra/docker-compose.yml','services/api-server/Dockerfile','services/algo/Dockerfile','infra/Dockerfile.web','scripts/qa/regression_plan.py')
manifest={'source_commit':report['source_commit'],'input_worktree_sha256':{p:sha(root/p) for p in inputs},
          'input_git_blob_sha256':{p:hashlib.sha256(subprocess.check_output(['git','show',report['source_commit']+':'+p])).hexdigest() for p in inputs},
          'evidence_sha256':{p.name:sha(p) for p in sorted(files)},
          'note':'证据经脱敏并统一 LF 后归档；输入同时记录工作区字节与 Git blob 哈希，兼容 CRLF。manifest/validation 自身不参与相互哈希。测试目标提交与随后报告提交分开。'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
validation={'status':'PASS','validated_at':datetime.now().astimezone().isoformat(),'original_cases':80,
            'status_counts':{k:counts[k] for k in ('PASS','FAIL','BLOCKED')},'original_fields_preserved':True,
            'historical_evidence_unchanged':True,'business_tracked_files_unchanged':True,
            'all_passes_have_execution_evidence':True,'source_commit_consistent':True,
            'configured_secret_literal_hits':secret_hits,'jwt_literal_hits':0,
            'temporary_stack_removed':True,'existing_demo_healthy':True,'manifest_files':len(files)}
(out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(validation,ensure_ascii=False))
