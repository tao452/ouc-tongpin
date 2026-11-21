"""Build the W4 report from fresh execution artifacts; never updates historical files."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'docs/qa/evidence/w4-regression-80'
SHA = '7c67518fc91583a3983ea265b85f6d2a54d12eab'
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, text):
    (OUT / name).write_text(text.rstrip() + '\n', encoding='utf-8')
def save(name, value):
    write(name, json.dumps(value, ensure_ascii=False, indent=2))

catalogue_path = ROOT / 'docs/qa/s1-test-cases.json'
history_path = ROOT / 'docs/qa/evidence/regression-20261109/catalogue-results.json'
catalogue, history = read(catalogue_path), read(history_path)
api, java, infra, security = [read(OUT / name) for name in ('api-results.json','java-results.json','stack-results.json','security-results.json')]
historical = {r['case_id']:r for r in history['results']}
current = {r['case_id']:r for r in api if r['case_id'].startswith('S1-')}
current.update({r['case_id']:r for r in java['catalogue_results']})
current.update({r['case_id']:r for r in infra['results'] if r['case_id'].startswith('S1-07')})
assert len(current) == 80 and len(historical) == 80
assert len({c['id'] for c in catalogue['cases']}) == 80
supplemental = {r['case_id']:r for r in api if not r['case_id'].startswith('S1-')}
tested_at = datetime.now(timezone(timedelta(hours=8))).isoformat()

# Capture every actual JUnit method without environment properties or console material.
junit_cases = []
for file in sorted((ROOT / 'services/api-server/target/surefire-reports').glob('TEST-*.xml')):
    for test in ET.parse(file).getroot().findall('testcase'):
        junit_cases.append({'class':test.get('classname'), 'method':test.get('name'), 'seconds':float(test.get('time','0')),
            'status':'FAIL' if test.find('failure') is not None or test.find('error') is not None else ('BLOCKED' if test.find('skipped') is not None else 'PASS'),
            'report_sha256':digest(file)})
save('junit-cases.json', {'source_commit':SHA, 'collected_at':java['executed_at_utc'], 'cases':junit_cases})

privacy_inputs = {
69:{'key':'catalogue-test-key-at-least-32-bytes','user':'synthetic-user-a','purpose':'treehole','repetitions':2},
70:{'users':['synthetic-user-a','synthetic-user-b'],'purpose':'treehole'},
71:{'user':'synthetic-user-a','purposes':['treehole','match']},
72:{'user':'synthetic-user-a','purpose':'treehole','keys':['catalogue-test-key-at-least-32-bytes','catalogue-test-key-at-least-32-bytes-second']},
73:{'secrets':[None,'','too-short']},
74:{'phone':'13800000000','studentId':'202600000001','email':'synthetic@example.com','token':'test-token-only','scope':'synthetic fixture'},
75:{'exception':'IllegalArgumentException','message':'studentId=202600000001','scope':'synthetic fixture'},
}
owners = {}
for n in (1,2,3,5,6): owners[n] = ['M5','M1']
for n in range(7,13): owners[n] = ['M5']
owners.update({30:['M1'],45:['M5'],57:['M1','M6'],58:['M1','M6'],76:['M1','M5','M3'],80:['仓库管理员']})
reasons = {
**{n:'未提供真实微信测试应用、授权账号和有效/失效/复用 code；本栈显式使用模拟平台身份，真实 JWT 已运行，不能据此通过真实平台用例。' for n in (1,2,3,5,6)},
**{n:'校内认证、绑定或截图授权入口尚未实现；已做本次 HTTP 前置探测，不能完成对应业务步骤。' for n in range(7,13)},
30:'已实际建立连续记录并跨缺勤日查询；连续天数与断签归零的最终验收规则仍缺 M1 确认。US-03 折线留空规则不等同于该连续天数规则。',
45:'已对同一真实测试帖子在过期前后访问详情，均为 404；详情路由尚未实现，无法把通用 404 作为过期访问拒绝验收。',
57:'MEDIUM HTTP 技术断言通过。M1 已确认 S1 分级放行规则；原历史记录要求的正式词库/业务验收仍未完成，当前默认仍为 5 词示例库。',
58:'LOW HTTP 技术断言通过。M1 已确认 S1 分级放行规则；原历史记录要求的正式词库/业务验收仍未完成，当前默认仍为 5 词示例库。',
76:'JWT、身份分表、匿名映射和数据库授权技术前置已接入并实际复测；现有 US25 验收要求的 M1/M5 业务材料复核和 M3 独立复现仍未留存，本次保留 BLOCKED。',
80:'当前 Commit 的 CI/quality 成功；历史故障分支 quality 失败记录已重新读取。develop protection API 仍为 404，rulesets 返回空列表，不能确认实际强制保护；待管理员提供 Settings 证据。本次未新建故障分支。',
}
rows = []
for case in catalogue['cases']:
    ident, number = case['id'], int(case['id'].split('-')[1])
    actual = current[ident]
    trace = actual.get('execution_trace', [])
    # Retain independent acceptance gates; attach the newly executed technical evidence.
    supporting = []
    if number == 30: supporting = [supplemental['W4-STREAK-TECHNICAL']]
    if number == 45: supporting = [supplemental['W4-EXPIRY-DETAIL-PREREQUISITE']]
    if number == 76: supporting = [supplemental['W4-IDENTITY-SPLIT'], *security['results']]
    if number == 79: supporting = [supplemental['W4-GATEWAY-TRACE']]
    for support in supporting:
        trace = trace + support.get('execution_trace', [])
    started = actual.get('started_at', java['executed_at_utc'] if 69 <= number <= 75 else infra['started_at'])
    finished = actual.get('finished_at', java['executed_at_utc'] if 69 <= number <= 75 else infra['finished_at'])
    if supporting:
        started = min(started, *[s['started_at'] for s in supporting])
        finished = max(finished, *[s['finished_at'] for s in supporting])
    status = actual['status']
    executed = actual.get('executed', status in ('PASS','FAIL'))
    evidence = ['api-results.json'] if number < 69 or number in (76,80) else (['java-results.json','junit-cases.json','java-suites.json'] if number <= 75 else ['stack-results.json'])
    if number == 76: evidence += ['security-results.json']
    if number == 80: evidence += ['github-checks.json']
    http = [e for e in trace if e['kind'] == 'http']
    db = [e for e in trace if e['kind'] in ('mysql','redis')]
    if number in (30,57,58,76):
        technical = actual.get('technical_assertions') == 'PASS' if number in (57,58) else all(s['status']=='PASS' for s in supporting)
    else:
        technical = None
    row = {'id':ident,'module':case['module'],'title':case['title'],'purpose':case['title'],'priority':case['priority'],'issue':case['issue'],
           'original_preconditions':case['preconditions'],'original_steps':case['steps'],'expected':case['expected'],
           'historical_status':historical[ident]['status'],'historical_reason':historical[ident].get('reason'),
           'status':status,'current_status':status,'attempted':True,'executed':executed,
           'attempt_kind':'full_test' if executed and status != 'BLOCKED' else ('technical_test_and_acceptance_check' if trace else 'prerequisite_review'),
           'started_at':started,'finished_at':finished,'test_time':finished,'current_commit':SHA,
           'actual_inputs':privacy_inputs.get(number, [dict((k,e[k]) for k in ('method','path','query','input','raw_input') if k in e) for e in http]),
           'actual_execution_steps': [f"{e['method']} {e['path']} -> {e['http_status']}" for e in http] or ([actual['observations'][0]['test_method']] if 69<=number<=75 else ['核对当前源码、隔离环境配置及所需外部验收材料']),
           'actual_result':{'observations':actual.get('observations'),'technical_assertions_passed':technical,
                            'supporting_checks':[{'id':s['case_id'],'status':s['status'],'observations':s.get('observations')} for s in supporting]},
           'http_evidence':http or {'applicable':False,'reason':'Java 单元测试' if 69<=number<=75 else '无可执行接口/真实平台凭据，或见关联栈/GitHub 证据'},
           'database_evidence':db or {'applicable':False,'reason':'本条无需数据库写入，或前置依赖阻塞；未使用团队数据库'},
           'evidence_files':evidence,'failure_reason':actual.get('reason') if status=='FAIL' else None,
           'blocked_reason':reasons.get(number,actual.get('reason')) if status=='BLOCKED' else None,
           'owners':owners.get(number,[]) if status=='BLOCKED' else [],
           'transition':historical[ident]['status']+' → '+status}
    if number in (1,2,3,5,6):
        row['actual_inputs']={'WX_MOCK_ENABLED':True,'WX_APPID_provided':False,'WX_SECRET_provided':False,'live_wechat_code':None}
        row['actual_execution_steps']=['核对隔离环境仅开启合成平台身份，未提供真实应用凭据和 code','读取当前 WeChatSessionClient 实现及已执行 WeChatSessionContractTest 的 JUnit 结果；未向微信发送授权请求']
        row['evidence_files']+=['environment-snapshot.json','junit-cases.json']
    if number in (77,78):
        row['actual_inputs']={'project':'ouc-w4-20261118-7c67518','compose_file':'infra/docker-compose.yml','credentials':'独立随机生成，值不归档'}
        row['actual_execution_steps']=(['docker compose config -q：完整 .env', 'docker compose config -q：ANON_ID_SECRET 置空', '检查退出码及输出不含实际密钥'] if number==77 else ['从当前干净源码执行 docker compose build（api/algo/web）','导入已有官方 mysql:8.0 / redis:7-alpine 只读镜像缓存','在独立 daemon/project、新卷中 up -d --no-build --pull never --wait','docker compose ps 核对五服务全部 running / healthy'])
        row['evidence_files']+=['initial-state.json','environment-snapshot.json']
    if number==80:
        github=read(OUT/'github-checks.json')
        row['actual_inputs']={'repository':'tao452/ouc-tongpin','commit':SHA,'endpoints':list(github['endpoints'])}
        row['http_evidence']={key:{'http_status':value['http_status'],'response':value['data']} for key,value in github['endpoints'].items() if not key.endswith('/reviews')}
        row['actual_execution_steps']=['读取当前 Commit 的 CI run 44254115747 及 job 结果','重新读取 PR #53 历史故障实验的 run/job 结论','GET develop protection 和 repository rulesets；未重新提交故障测试分支']
    if 69 <= number <= 75:
        row['timestamp_basis'] = 'JUnit 汇总采集时间；原 XML 不含每个方法的起止时间，耗时见 junit-cases.json'
        row['actual_execution_steps'].insert(0,'mvn -B -q verify；执行 CataloguePrivacyExecutionTest 的对应方法')
    if number==76:
        row['actual_execution_steps'].insert(0,'执行 20 条 US25 HTTP/JWT/数据库角色/运行 PII 专项及 information_schema 分表检查，再核对独立业务复核记录')
    rows.append(row)
assert all(r['executed'] and r['evidence_files'] for r in rows if r['status']=='PASS')
counts, transitions = Counter(r['status'] for r in rows), Counter(r['transition'] for r in rows)
save('results.json', {'schema_version':1,'suite':'W4 original S1 catalogue 80','source_commit':SHA,'generated_at':tested_at,
     'historical_commit':history['source_commit'],'historical_time':history['executed_at_utc'],
     'catalogue_sha256':digest(catalogue_path),'historical_evidence_sha256':digest(history_path),
     'attempted_count':len(rows),'fully_executed_count':sum(r['executed'] and r['status']!='BLOCKED' for r in rows),
     'historical_status_counts':dict(Counter(r['historical_status'] for r in rows)),
     'status_counts':{s:counts[s] for s in ('PASS','FAIL','BLOCKED')},'transitions':dict(transitions),
     'scope':'隔离本地 WSL Docker 五服务 + MySQL/Redis + 真实 JWT；微信平台身份为合成 fixture；保留正式业务和独立复核门槛。',
     'results':rows})

module_names = {'auth':'登录认证','checkin':'情绪打卡','treehole':'匿名树洞','needs':'搭子需求','moderation':'内容审核','privacy':'隐私保护','infra':'基础设施'}
module_table = ['| 模块 | 数量 | PASS | FAIL | BLOCKED |','|---|---:|---:|---:|---:|']
for key, name in module_names.items():
    module_rows = [r for r in rows if r['module']==key]
    c = Counter(r['status'] for r in module_rows)
    module_table.append(f"| {name} | {len(module_rows)} | {c['PASS']} | {c['FAIL']} | {c['BLOCKED']} |")

comparison = ['# 原 80 条回归新旧对照','',f"历史：2026-11-09，`{history['source_commit']}`，55 PASS / 0 FAIL / 25 BLOCKED。",f"本次：{tested_at}，`{SHA}`，{counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['BLOCKED']} BLOCKED。",'', '| 状态变化 | 数量 |','|---|---:|']
for transition in ('PASS → PASS','PASS → FAIL','PASS → BLOCKED','BLOCKED → PASS','BLOCKED → FAIL','BLOCKED → BLOCKED','FAIL → PASS'):
    comparison.append(f'| {transition} | {transitions[transition]} |')
comparison += ['', '历史搭子需求 S1-047–054 已实际发起请求并核对 buddy_demand 行数，接口缺失阻塞解除。',
               'S1-076 的 JWT 和权限技术前置已解除，20 条安全专项及分表检查有本次证据；业务与独立复核仍待补齐。',
               'S1-057/058 的分级规则已有 M1 确认，技术断言本次通过；保留原有正式词库/业务验收门槛。',
               '没有历史 FAIL，因此 FAIL → PASS 为 0；没有把未执行的场景登记为 PASS。','', '| 编号 | 模块 | 测试目的 | 11月9日 | 本次 | 变化 |','|---|---|---|---|---|---|']
comparison += [f"| {r['id']} | {module_names[r['module']]} | {r['title']} | {r['historical_status']} | {r['status']} | {r['transition']} |" for r in rows]
write('comparison.md','\n'.join(comparison))

blocked = ['# 剩余阻塞与责任人','',f"合计 {counts['BLOCKED']} 条。以下责任人是协作角色，不代表已发送通知或已承诺完成日期。",'', '| 编号 | 责任角色 | 本次结果与解除条件 |','|---|---|---|']
blocked += [f"| {r['id']} {r['title']} | {' / '.join(r['owners'])} | {r['blocked_reason']} |" for r in rows if r['status']=='BLOCKED']
blocked += ['', 'M3 还需按 US25 文档独立复现身份、授权与业务入口；本次自动化复测不能登记为 M3 已完成复核。',
            '管理员需提供 develop 的实际分支保护设置及 quality 必须通过的证据。404 和空 rulesets 不足以断言已配置或未配置保护。',
            '后续仅在明确授权的业务范围补充真实微信/PII材料；不向仓库提交真实账号、截图、token 或配置密钥。']
write('blocked-items.md','\n'.join(blocked))

report = ['# W4 原 80 条回归测试报告','',f"测试版本：`{SHA}`（develop，2026-11-18 获取）。本次逐条尝试 80/80，完整执行并判定 {counts['PASS']+counts['FAIL']} 条，其余保留依赖或验收阻塞。",f"结果：**{counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['BLOCKED']} BLOCKED**。历史为 55 PASS / 25 BLOCKED。",'',*module_table,'',
'## 主要发现','',
'- S1-047–054：搭子发布及缺字段、标签 5/6 个、备注 200/201 字边界均实际执行，成功增加一行，非法输入不落库。',
'- 登录、签名 JWT、过期/错误签名/audience、双账号查询与写入隔离、并发身份、数据库只读角色和日志 PII 已执行 20 条安全专项；详见 security-results.json。专项不计入原 80 条数量。',
'- 打卡 6 种情绪、强度、100/101 字备注、日期查询、同日幂等及 8 并发提交均使用真实服务；树洞包含审核故障暂停、匿名响应、分页、过期隐藏和焚毁存储检查。',
'- HIGH 阻断、敏感词变体、正常英文短语豁免、422/413 边界使用 HTTP 实测；MEDIUM/LOW 技术通过与正式词库业务验收分开记录。',
'- 另对“去死海 / 去死记硬背 / 去死胡同 / 废物利用”等正常短语与同句真实敏感词做 8 条 HTTP 正反控制，8/8 通过，见 phrase-results.json；不增加原目录数量。',
'- 隐私目录 7 条由当前源码 Maven/JUnit 实际执行；Java 全套 141 项，0 失败、0 错误、0 跳过。',
'- 五服务从干净源码构建、空卷初始化；完整配置、缺密钥配置、全部健康及 Nginx 7 项 smoke 有本次结果。',
'- 当前提交 GitHub CI 的 guard、stack、quality 成功；按文档变更跳过的模块 job 不登记为实际执行。保护设置仍待管理员证明。',
'', '## 执行命令','', '```powershell', 'mvn -B -q verify  # 在 services/api-server 内执行', 'python scripts/qa/collect_java_evidence.py --reports services/api-server/target/surefire-reports --output qa-private/w4/java-results.json', 'python -X utf8 docs/qa/evidence/w4-regression-80/run-local.py', 'python -X utf8 docs/qa/evidence/w4-regression-80/run-phrase-checks.py', 'python -X utf8 docs/qa/evidence/w4-regression-80/sanitize-evidence.py', 'python -X utf8 docs/qa/evidence/w4-regression-80/assemble.py', '```','',
'Docker 构建与回收命令、网络重试和隔离边界见 environment.md。run-local.py 是本次证据适配器，仅连接指定 WSL daemon/project，调用原有断言并附加输入、响应、SQL/Redis 和时间记录；未伪造 GITHUB_ACTIONS。',
'', '## 证据与判定','',
'results.json 保留原编号、测试目的、步骤和预期；逐条链接历史状态、当前状态、测试时间、测试 Commit、实际输入/步骤、响应及数据库证据。BLOCKED 记录本次前置检查与缺少的条件；不能完成原场景的 HTTP 404 不算 PASS。',
'api-results.json、stack-results.json、java-results.json、security-results.json 为当前执行材料；junit-cases.json 为去除系统属性和控制台材料的 JUnit 方法清单。仅使用合成身份和新建卷，凭证在证据中脱敏。',
'原目录和历史证据的 SHA-256 记录在 results.json / manifest.json；原目录及历史文件不变。报告提交与测试目标提交区分记录，业务代码无改动。',
'', '## 后续安排','',
'可以进入新增 40 条测试的设计阶段。优先设计 JWT/跨用户访问、重试与并发、搭子时区与审核、焚毁竞态、正常短语和网关权限的补充用例；独立编号并关联本报告。现有阻塞继续按 blocked-items.md 补证，本报告不代表这些业务或管理员验收已完成。']
write('test-report.md','\n'.join(report))
write('pr-description.md',f'''### 改了什么

完成原 80 条回归复测与逐条证据整理，保留原编号和历史记录。搭子需求 8 条历史阻塞解除；JWT/身份隔离专项已复测，剩余真实微信、业务确认和管理员事项单列。

### 怎么自测

干净 develop `{SHA[:7]}`，隔离 Docker 五服务运行原目录断言及 `run-local.py`。80/80 条逐条尝试，{counts['PASS']} PASS、{counts['FAIL']} FAIL、{counts['BLOCKED']} BLOCKED；Maven 141 项通过，另执行 20 条安全专项。详见 test-report.md 与 results.json。

### 影响面与回滚

仅新增 W4 测试报告、证据及复现适配器，不影响业务模块。原目录与历史记录不变，回滚只需撤销本次报告提交。''')
print(json.dumps({'count':len(rows),'status_counts':dict(counts),'transitions':dict(transitions)},ensure_ascii=False))
