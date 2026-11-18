"""Additional HTTP controls for default-dictionary allow phrases; excluded from the 80 count."""
import json
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
samples = [
    ('周末一起去死海旅行', True, []),
    ('学习不要去死记硬背', True, []),
    ('请不要去死胡同', True, []),
    ('废物利用有利于环保', True, []),
    ('废物处理和废物回收', True, []),
    ('去死海旅行然后去死', False, ['HIGH']),
    ('废物利用你这废物', True, ['MEDIUM']),
    ('shabilist', True, []),
]
rows=[]
for number,(text,passed,levels) in enumerate(samples,1):
    request=urllib.request.Request('http://127.0.0.1:18084/api/moderation/check', data=json.dumps({'text':text},ensure_ascii=False).encode(), headers={'Content-Type':'application/json'})
    with opener.open(request, timeout=15) as response:
        code,body=response.status,json.load(response)
    actual_levels=[h['level'] for h in body['hits']]
    ok=code==200 and body['passed']==passed and actual_levels==levels
    rows.append({'id':f'W4-PHRASE-{number:02}', 'time':datetime.now(timezone(timedelta(hours=8))).isoformat(),
                 'request':{'method':'POST','path':'/api/moderation/check','body':{'text':text}},
                 'expected':{'http_status':200,'passed':passed,'hit_levels':levels},
                 'http_status':code,'response':body,'status':'PASS' if ok else 'FAIL',
                 'database_evidence':{'applicable':False,'reason':'无状态审核接口'}})
out=Path('docs/qa/evidence/w4-regression-80/phrase-results.json')
out.write_text(json.dumps({'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                         'excluded_from_original_80':True,'results':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({'additional_phrase_checks':len(rows),'passed':sum(r['status']=='PASS' for r in rows)})
raise SystemExit(0 if all(r['status']=='PASS' for r in rows) else 1)
