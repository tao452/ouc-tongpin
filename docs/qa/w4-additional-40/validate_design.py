"""Validate the design documents only; never runs the forty business cases."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CATALOGUE=ROOT/'docs/qa/w4-additional-40-test-cases.json'
MARKDOWN=ROOT/'docs/qa/W4-新增40条测试用例设计.md'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])

def read_blobs(ref,paths):
    # One Git process; content is read by declared byte size, not by delimiters in blobs.
    request=''.join(ref+':'+p+'\n' for p in paths).encode('utf-8')
    data=subprocess.check_output(['git','-C',str(ROOT),'cat-file','--batch'],input=request)
    cursor=0; result={}
    for path in paths:
        end=data.index(b'\n',cursor)
        header=data[cursor:end].split()
        assert len(header)==3 and header[1]==b'blob',f'Missing Git source: {path}'
        size=int(header[2]); start=end+1
        result[path]=data[start:start+size]; cursor=start+size+1
    assert cursor==len(data)
    return result

def main():
    if read(CATALOGUE)['artifact_type'] != 'TEST_DESIGN_ONLY':
        from validate_execution import main as validate_execution
        return validate_execution()
    document=read(CATALOGUE); cases=document['cases']; manifest=read(HERE/'baseline-manifest.json')
    base=document['source_commit']
    assert document['artifact_type']=='TEST_DESIGN_ONLY'
    assert len(cases)==document['case_count']==40
    assert [c['id'] for c in cases]==[f'S1-{n:03}' for n in range(81,121)]
    assert len({c['title'] for c in cases})==40
    assert Counter(c['group'] for c in cases)=={'jwt_identity':10,'concurrency':8,'treehole_burn':8,'buddy_boundary':8,'moderation_allow':6}
    assert Counter(c['status'] for c in cases)=={'NOT_RUN':40}
    assert document['status_counts']=={'NOT_RUN':40,'PASS':0,'FAIL':0,'BLOCKED':0}
    assert Counter(c['readiness']['state'] for c in cases)==document['readiness_counts']=={'READY_TO_IMPLEMENT':38,'PENDING_RULE':2}
    assert [c['id'] for c in cases if c['readiness']['state']=='PENDING_RULE']==['S1-113','S1-114']
    original=read(ROOT/document['original_catalogue'])['cases']
    original_ids={c['id'] for c in original}
    assert len(original_ids)==80 and not original_ids.intersection(c['id'] for c in cases)
    markdown=MARKDOWN.read_text(encoding='utf-8')
    matches=list(re.finditer(r'^## (S1-\d{3}) (.+)$',markdown,re.M))
    assert [m.group(1) for m in matches]==[c['id'] for c in cases]
    for index,(case,match) in enumerate(zip(cases,matches)):
        block=markdown[match.end():matches[index+1].start() if index+1<len(matches) else len(markdown)]
        assert match.group(2)==case['title']
        assert case['preconditions'] and case['inputs'] and case['steps'] and case['expected']['assertions']
        assert all(isinstance(s,str) and s.strip() for s in [case['purpose'],*case['preconditions'],*case['steps'],*case['expected']['assertions']])
        assert case['executed'] is False and case['executed_at'] is None and case['actual_result'] is None
        assert case['automation']['implementation_status']=='PLANNED_NOT_IMPLEMENTED'
        assert case['automation']['approach'].strip() and case['automation']['proposed_test_file'] and case['automation']['proposed_test_name']
        assert case['related_original_ids'] and set(case['related_original_ids'])<=original_ids
        assert case['existing_coverage'] and case['coverage_delta'].strip()
        assert case['source_refs'] and set(case['source_refs'])<=document['source_refs'].keys()
        assert all((ROOT/document['source_refs'][ref]).is_file() for ref in case['source_refs'])
        assert case['purpose'] in block and case['automation']['approach'] in block
        assert all(s in block for s in [*case['preconditions'],*case['steps'],*case['expected']['assertions']])
        json_block=re.search(r'输入：\n\n```json\n(.*?)\n```',block,re.S)
        assert json_block and json.loads(json_block.group(1))==case['inputs']
        if case['readiness']['state']=='PENDING_RULE':
            assert case['expected']['approval']=='PENDING' and case['expected']['basis_type']=='PROPOSED_RULE'
            assert case['readiness']['decision'] and case['readiness']['owners']==['M1','M5']
        else:
            assert case['expected']['approval']=='BASELINED' and case['readiness']['decision'] is None

    preserved=manifest['original_80_and_history_git_blob_sha256']
    sources=manifest['design_source_git_blob_sha256']
    assert manifest['source_commit']==base
    for path,content in read_blobs(base,sorted(set(preserved)|set(sources))).items():
        expected=preserved.get(path,sources.get(path))
        assert hashlib.sha256(content).hexdigest()==expected,path
    protected=['docs/qa/s1-test-cases.json','docs/qa/evidence']
    assert not git('diff','--name-only',base,'--',*protected).strip(),'Original catalogue or historical evidence changed'
    assert not git('diff','--name-only',base,'--','apps','services','infra','scripts','.github').strip(),'Business files changed'
    assert git('rev-parse',document['prior_regression_commit']+':docs/qa/evidence/w4-regression-80').decode().strip()==manifest['prior_w4_report']['tree']
    allowed={'docs/qa/w4-additional-40-test-cases.json','docs/qa/W4-新增40条测试用例设计.md'}
    changes=git('-c','core.quotePath=false','diff','--name-only',base).decode('utf-8').splitlines()
    changes+=git('-c','core.quotePath=false','ls-files','--others','--exclude-standard').decode('utf-8').splitlines()
    assert all(p in allowed or p.startswith('docs/qa/w4-additional-40/') for p in changes),changes
    result={'artifact_type':'DESIGN_STATIC_VALIDATION','status':'PASS',
            'validated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'source_commit':base,
            'design_cases':40,'execution_status_counts':document['status_counts'],'business_cases_executed':0,
            'readiness_counts':document['readiness_counts'],'json_markdown_consistent':True,
            'original_80_unchanged':True,'historical_files_unchanged':True,'business_code_unchanged':True,
            'protected_git_blobs_checked':len(preserved),'source_git_blobs_checked':len(sources),
            'note':'PASS 仅指设计文档静态检查；40 条业务用例全部 NOT_RUN，自动化尚未实现。',
            'design_files_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in [CATALOGUE,MARKDOWN,HERE/'automation-plan.md',HERE/'baseline-manifest.json',Path(__file__)]}}
    (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
