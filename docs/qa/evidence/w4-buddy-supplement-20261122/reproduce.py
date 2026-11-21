"""Reproduce the eight original publishing checks on a fresh owned test stack."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import UTC,datetime

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'scripts/qa'))
from regression_http import Client,Runner
from regression_stack import Stack
import regression_match

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--project',required=True);p.add_argument('--base-url',required=True)
 p.add_argument('--env-file',required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();assert a.project.startswith('ouc-w4-')
 stack=Stack();stack.command=('docker','compose','--project-name',a.project,'--env-file',a.env_file,'-f','infra/docker-compose.yml')
 ps=stack.execute('ps','--format','json');assert a.project in ps
 assert all(stack.count(t)==0 for t in ['users','auth','checkin','treehole_post','treehole_archive','buddy_demand'])
 started=datetime.now(UTC).isoformat();runner=Runner(Client(a.base_url).authenticate())
 regression_match.register(runner,stack)
 rows=[r for r in runner.results if r['case_id'] in {f'S1-{n:03}' for n in range(47,55)}]
 assert len(rows)==8
 report={'source_application_commit':'99712e400ed725060ef8e0b3c44d699c5d1c14f2',
  'checkout_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'started_at':started,'finished_at':datetime.now(UTC).isoformat(),'results':rows,
  'scope':'real HTTP and real MySQL assertions; use a newly created owned Compose project'}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
 return int(any(r['status']!='PASS' for r in rows))
if __name__=='__main__':raise SystemExit(main())
