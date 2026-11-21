/* Observational page probes. Completion is not a claim that recorded defects are fixed. */
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const crypto = require('node:crypto')
const cp = require('node:child_process')
const root = path.resolve(__dirname, '../..')
const appRoot = path.join(root, 'apps/miniprogram')
const analysis = require(path.join(appRoot, 'utils/emotion-analysis.js'))
const treehole = require(path.join(appRoot, 'utils/treehole.js'))
const flush = async () => { for (let i = 0; i < 16; i++) await Promise.resolve() }
function harness(file, realRequest = false) {
  const pending = []; const toasts = []; const network = []
  const wx = {
    showToast: x => toasts.push(x.title), showLoading() {}, hideLoading() {},
    request: x => network.push(x), stopPullDownRefresh() {},
    createCanvasContext: () => new Proxy({}, { get: () => () => {} }),
    navigateBack() {}, showModal() {}
  }
  let request
  if (realRequest) {
    const module = { exports: {} }
    vm.runInNewContext(fs.readFileSync(path.join(appRoot, 'utils/request.js'), 'utf8'), {
      module, wx, console: { error() {} }, require: name => name.includes('storage')
        ? { getToken: () => '' } : { baseURL: 'http://synthetic.invalid' }
    })
    request = module.exports.request
  } else request = options => new Promise((resolve, reject) => pending.push({ options, resolve, reject }))
  let config
  vm.runInNewContext(fs.readFileSync(path.join(appRoot, file), 'utf8'), {
    Page: value => { config = value }, wx, Date, Promise, setTimeout: () => 0,
    console: { error() {}, log() {} },
    require: name => name.includes('emotion-analysis') ? analysis
      : name.includes('utils/treehole') ? treehole : { request }
  }, { filename: file })
  const page = { ...config, data: structuredClone(config.data),
    setData(changes, done) { Object.assign(this.data, changes); if (done) done.call(this) } }
  return { page, pending, toasts, network }
}
function payload(note = 'synthetic-record') {
  const now = new Date(); const day = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  return { items: [{ id: 'qa-owned', checkinDate: day, emotion: 'CALM', intensity: 3, note }], total: 1, streakDays: 1 }
}
async function main() {
  const rows = []
  let h = harness('pages/checkin/records.js')
  h.page.onLoad(); h.page.onShow(); h.pending[0].resolve(payload()); await flush()
  rows.push({ id: 'RECORD-01', status: h.pending.length > 1 ? 'REPRODUCED' : 'NOT_REPRODUCED',
    actual: { requestsAfterFirstEntry: h.pending.length }, owner: 'M2' })
  h = harness('pages/checkin/records.js'); h.page.loadRecords()
  h.page.changeRange({ currentTarget: { dataset: { range: 30 } } })
  h.pending[0].resolve(payload('old-window')); await flush()
  rows.push({ id: 'RECORD-02', status: h.page.data.rangeDays !== 30 ? 'REPRODUCED' : 'NOT_REPRODUCED',
    actual: { requestedRange: 30, displayedRangeAfterOldResponse: h.page.data.rangeDays,
      followupUrl: h.pending[1] && h.pending[1].options.url }, owner: 'M2' })
  h = harness('pages/checkin/records.js'); h.page.data.records = [{ id: 'old' }]; h.page.data.totalDays = 9
  h.page.changeRange({ currentTarget: { dataset: { range: 30 } } })
  rows.push({ id: 'RECORD-03', status: h.page.data.records.length ? 'REPRODUCED' : 'NOT_REPRODUCED',
    actual: { oldRecordsWhileLoading: h.page.data.records.length, oldTotalWhileLoading: h.page.data.totalDays }, owner: 'M2' })
  h = harness('pages/checkin/records.js'); h.page.data.records = [{ id: 'old' }]
  h.page.loadRecords(); h.pending[0].reject(new Error('synthetic failure')); await flush()
  rows.push({ id: 'RECORD-04', status: h.page.data.error && h.page.data.records.length ? 'REPRODUCED' : 'NOT_REPRODUCED',
    actual: { error: h.page.data.error, remainingOldRecords: h.page.data.records.length }, owner: 'M2' })
  h = harness('pages/checkin/records.js', true); h.page.loadRecords()
  h.network[0].success({ statusCode: 503, data: { message: 'synthetic outage' } }); await flush()
  rows.push({ id: 'MINE-06', status: h.toasts.length > 1 ? 'REPRODUCED' : 'NOT_REPRODUCED',
    actual: { toastCount: h.toasts.length, toastSources: ['request.js', 'records.js'] }, owner: 'M2' })
  h = harness('pages/treehole/index.js', true)
  h.page.data.posts = [{ id: 'owned-existing' }]; h.page.data.cursor = '2'; h.page.data.hasMore = true
  h.page.loadPosts(false); h.network[0].success({ statusCode: 503, data: {} }); await flush()
  rows.push({ id: 'R-06', status: 'PARTIAL_FEEDBACK', actual: { toastCount: h.toasts.length,
    inlineError: h.page.data.error, postsPreserved: h.page.data.posts.length, cursor: h.page.data.cursor }, owner: 'M2' })
  h = harness('pages/plaza/publish/publish.js'); Object.assign(h.page.data, { scene: '自习', date: '2034-01-15', time: '10:00',
    location: { address: '图书馆', lat: 36.16, lng: 120.4 } })
  h.page.submitNeed()
  const sent = h.pending[0].options
  rows.push({ id: 'PLAZA-01', status: 'PAYLOAD_CHECKED_INTEGRATION_PENDING',
    actual: { route: sent.url, time: sent.data.time, requiredFields: Object.keys(sent.data),
      backendPositiveControl: 'PR91 S1-047 and PR92 HTTP tests; fresh WeChat end-to-end not executed' }, owner: 'M3/M4, M5' })
  rows.push({ id: 'MINE-05', status: 'LOCAL_CONNECTION_RECHECK_PENDING',
    actual: { configuredBaseURL: require(path.join(appRoot, 'config.js')).baseURL,
      ownedStackPort: 18085, note: 'Isolated API positive controls do not verify the configured 8080 frontend environment' }, owner: 'M3/M4' })
  const sourceFiles = ['pages/checkin/records.js', 'utils/request.js', 'pages/treehole/index.js', 'pages/plaza/publish/publish.js']
  const report = { testedAt: new Date().toISOString(), sourceCommit: cp.execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
    method: 'Node VM executing actual page/request code with controlled deferred promises; not WeChat GUI',
    guiRecheck: 'BLOCKED: developer tool did not expose a targetable window', issues: rows,
    sourceSha256: Object.fromEntries(sourceFiles.map(file => [file, crypto.createHash('sha256').update(fs.readFileSync(path.join(appRoot, file))).digest('hex')])) }
  const output = process.argv[process.argv.indexOf('--output') + 1]
  if (!output || output === process.argv[0]) throw new Error('--output required')
  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true })
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(rows.map(r => ({ id: r.id, status: r.status, actual: r.actual })), null, 2))
}
main().catch(error => { console.error(error); process.exitCode = 2 })
