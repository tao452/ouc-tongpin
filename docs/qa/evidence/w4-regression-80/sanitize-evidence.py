import hashlib,json,re
from pathlib import Path

root=Path.cwd(); out=root/'docs/qa/evidence/w4-regression-80'
def scrub(value):
    if isinstance(value,dict):
        if value.get('kind')=='mysql' and isinstance(value.get('output'),str) and re.search(r'\b(?:FROM|UPDATE)\s+auth\b',value.get('sql',''),re.I) and any(s in value.get('sql','').lower() for s in ('openid','student_no','phone')):
            raw=value.get('output','')
            value={**value,'sql':re.sub(r"'[^']*'","'[SYNTHETIC REDACTED]'",value['sql']),
                   'output':{'redacted':True,'sha256':hashlib.sha256(raw.encode()).hexdigest(),
                             'rows':len(raw.splitlines()),'reason':'私有身份字段仅保留摘要和行数'}}
        return {k:scrub(v) for k,v in value.items()}
    if isinstance(value,list):return [scrub(v) for v in value]
    return value
for name in ('api-results.json','security-results.json','execution-progress.json'):
    path=out/name
    if not path.exists(): continue
    data=scrub(json.loads(path.read_text(encoding='utf-8')))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=out/'stack-results.json'; data=json.loads(path.read_text(encoding='utf-8'))
data.setdefault('original_runner_scope_label',data['scope'])
data['scope']='Local owned WSL Docker stack; original Compose and HTTP assertions'
data['transport']='Windows Python -> WSL root docker, explicit project ouc-w4-20261118-7c67518'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# A progress file duplicates final evidence; retain it only in the private execution directory.
progress=out/'execution-progress.json'
if progress.exists(): progress.replace(root/'qa-private/w4/execution-progress.json')
print('Private identity SQL evidence redacted; final assertions and counts preserved')
