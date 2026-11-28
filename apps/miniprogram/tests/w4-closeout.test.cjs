const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm')
const { codePointCount, truncateCodePoints } = require('../utils/codepoints')
const flush = async () => { for (let n = 0; n < 12; n++) await Promise.resolve() }
function harness(file, real = false) {
  const pending = [], network = [], toasts = []
  const wx = { showToast: x => toasts.push(x.title), showLoading() {}, hideLoading() {},
    stopPullDownRefresh() {}, request: x => network.push(x), navigateBack() {},
    createCanvasContext: () => new Proxy({}, { get: () => () => {} }) }
  let request = options => new Promise((resolve, reject) => pending.push({ options, resolve, reject }))
  if (real) {
    const module = { exports: {} }
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../utils/request.js'), 'utf8'), {
      module, wx, require: name => name.includes('storage') ? { getToken: () => 'synthetic' }
        : { baseURL: 'https://synthetic.invalid' }
    })
    request = module.exports.request
  }
  let config
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), {
    Page: x => { config = x }, wx, Date, Promise, console: { error() {} }, setTimeout: () => 0,
    require: name => name.includes('request') ? { request }
      : require(path.resolve(path.dirname(path.join(__dirname, '..', file)), name))
  })
  const page = { ...config, data: JSON.parse(JSON.stringify(config.data)),
    setData(values, callback) { Object.assign(this.data, values); if (callback) callback() } }
  return { page, pending, network, toasts }
}
const payload = total => ({ items: [], total, streakDays: total })
test('RECORD-01 首次请求去重，再次进入刷新', async () => {
  const h = harness('pages/checkin/records.js')
  h.page.onLoad(); h.page.onShow(); assert.equal(h.pending.length, 1)
  h.pending[0].resolve(payload(1)); await flush()
  h.page.onShow(); assert.equal(h.pending.length, 2)
})
test('RECORD-02 迟到的成功和失败不覆盖新范围', async () => {
  const h = harness('pages/checkin/records.js')
  h.page.loadRecords(); h.page.changeRange({ currentTarget: { dataset: { range: 30 } } })
  h.pending[1].resolve(payload(8)); await flush()
  h.pending[0].resolve(payload(2)); await flush()
  assert.equal(h.page.data.totalDays, 8); assert.equal(h.page.data.rangeDays, 30)
  h.page.loadRecords(); h.page.loadRecords()
  h.pending[3].resolve(payload(9)); await flush()
  h.pending[2].reject(new Error('old')); await flush()
  assert.equal(h.page.data.error, false); assert.equal(h.toasts.length, 0)
})
test('RECORD-03 切换范围清空列表计数图表', () => {
  const h = harness('pages/checkin/records.js')
  Object.assign(h.page.data, { records: [{ id: 1 }], totalDays: 6, continuousDays: 3, trendData: [1] })
  h.page.changeRange({ currentTarget: { dataset: { range: 30 } } })
  assert.equal(h.page.data.records.length, 0); assert.equal(h.page.data.totalDays, 0)
  assert.equal(h.page.data.trendData.length, 0); assert.equal(h.page.data.continuousDays, 0)
})
test('RECORD-04 失败显示错误和重试，不残留旧数据', async () => {
  const h = harness('pages/checkin/records.js'); h.page.data.records = [{ id: 1 }]
  h.page.loadRecords(); h.pending[0].reject(new Error('outage')); await flush()
  assert.equal(h.page.data.records.length, 0); assert.equal(h.page.data.error, true)
  assert.equal(h.page.data.loading, false)
  h.page.retryLoad(); h.pending[1].resolve(payload(0)); await flush()
  assert.equal(h.page.data.error, false)
})
test('MINE-06 实际请求封装失败只出现一次 Toast', async () => {
  const h = harness('pages/checkin/records.js', true)
  h.page.loadRecords(); h.network[0].success({ statusCode: 503, data: {} }); await flush()
  assert.equal(h.toasts.length, 1)
})
test('R-06 分页失败保留列表游标，局部重试成功', async () => {
  const h = harness('pages/treehole/index.js')
  Object.assign(h.page.data, { posts: [{ id: 'old' }], cursor: '2', hasMore: true })
  h.page.loadPosts(false); h.pending[0].reject(new Error('outage')); await flush()
  assert.equal(h.page.data.moreError, true); assert.equal(h.page.data.cursor, '2')
  assert.equal(h.page.data.posts.length, 1); assert.equal(h.toasts.length, 0)
  h.page.retryMore(); h.pending[1].resolve({ items: [], nextCursor: null }); await flush()
  assert.equal(h.page.data.moreError, false); assert.equal(h.page.data.hasMore, false)
})
test('PAGE-UNICODE 码点安全计数和截断', () => {
  assert.equal(codePointCount('😀'.repeat(200)), 200)
  assert.equal(truncateCodePoints('😀'.repeat(201), 200), '😀'.repeat(200))
  assert.equal(codePointCount('e\u0301'), 2)
})
for (const count of [100, 101, 200, 201]) {
  test(`PAGE-EMOJI-${count} 提交长度及原文保持`, async () => {
    const h = harness('pages/plaza/publish/publish.js')
    Object.assign(h.page.data, { scene: '自习', date: '2030-01-01', time: '10:00',
      location: { address: '合成地点', lat: -90, lng: -180 } })
    const remark = '😀'.repeat(count)
    h.page.onRemarkInput({ detail: { value: remark } }); assert.equal(h.page.data.remarkCount, count)
    const sent = h.page.submitNeed(); assert.equal(h.pending.length, count <= 200 ? 1 : 0)
    if (count <= 200) { assert.equal(h.pending[0].options.data.remark, remark); h.pending[0].resolve({}) }
    await sent
  })
}
test('PAGE-COORD 非数和越界坐标不发请求', async () => {
  for (const [lat,lng] of [[-90.000001,0], [90.000001,0], [NaN,0], [Infinity,0], [0,-180.000001], [0,180.000001]]) {
    const h = harness('pages/plaza/publish/publish.js')
    Object.assign(h.page.data, { scene: '自习', date: '2030-01-01', time: '10:00',
      location: { address: '合成地点', lat, lng } })
    await h.page.submitNeed(); assert.equal(h.pending.length, 0)
  }
})
test('PAGE-CONFIG 体验版拒绝 HTTP，本机指向独立网关', () => {
  const source = fs.readFileSync(path.join(__dirname, '../config.js'), 'utf8')
  const load = (env, baseURL) => {
    const module = { exports: {} }
    vm.runInNewContext(source, { module, require: () => ({ baseURL }),
      wx: { getAccountInfoSync: () => ({ miniProgram: { envVersion: env } }) } })
    return module.exports
  }
  assert.equal(load('develop', 'http://127.0.0.1:18085/').baseURL, 'http://127.0.0.1:18085')
  assert.throws(() => load('trial', 'http://127.0.0.1:18085'), /HTTPS/)
  assert.equal(load('trial', 'https://test.invalid').baseURL, 'https://test.invalid')
})
