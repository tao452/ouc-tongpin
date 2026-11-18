const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');

function harness() {
  const calls = { requests: [], show: 0, hide: 0, toasts: 0 };
  const storage = new Map();
  const wx = {
    request: options => calls.requests.push(options),
    showLoading: () => calls.show++, hideLoading: () => calls.hide++,
    showToast: () => calls.toasts++,
    setStorageSync: (key, value) => storage.set(key, value),
    getStorageSync: key => storage.get(key), removeStorageSync: key => storage.delete(key),
  };
  function load(file, dependencies = {}) {
    const module = { exports: {} };
    vm.runInNewContext(readFileSync(resolve(__dirname, '..', file), 'utf8'), {
      module, wx, require: name => {
        assert.ok(name in dependencies, `Unexpected import: ${name}`);
        return dependencies[name];
      }, console: { error() {} },
    }, { filename: file });
    return module.exports;
  }
  const tokens = load('utils/storage.js');
  const { request } = load('utils/request.js', {
    './storage.js': tokens, '../config.js': { baseURL: 'https://test.invalid' },
  });
  return { calls, tokens, request };
}

test('token 可以保存、读取和移除，空值不会覆盖已有 token', () => {
  const { tokens } = harness();
  assert.equal(tokens.getToken(), '');
  tokens.setToken('synthetic-token');
  tokens.setToken('');
  assert.equal(tokens.getToken(), 'synthetic-token');
  tokens.removeToken();
  assert.equal(tokens.getToken(), '');
});

test('请求携带 token、方法和数据，成功后关闭 loading', async () => {
  const { calls, tokens, request } = harness();
  tokens.setToken('synthetic-token');
  const pending = request({ url: '/checkins', method: 'post', data: { intensity: 3 } });
  const sent = calls.requests[0];
  assert.equal(sent.url, 'https://test.invalid/checkins');
  assert.equal(sent.method, 'POST');
  assert.equal(sent.header.Authorization, 'Bearer synthetic-token');
  assert.equal(sent.data.intensity, 3);
  sent.success({ statusCode: 201, data: { id: 1 } });
  assert.equal((await pending).id, 1);
  assert.equal(calls.show, 1);
  assert.equal(calls.hide, 1);
});

test('无 token 时不附加 Authorization', async () => {
  const { calls, request } = harness();
  const pending = request({ url: '/public', showLoading: false });
  assert.equal('Authorization' in calls.requests[0].header, false);
  calls.requests[0].success({ statusCode: 200, data: {} });
  await pending;
  assert.equal(calls.show + calls.hide, 0);
});

test('GET 网络失败只重试一次，最终失败关闭 loading 并提示', async () => {
  const { calls, request } = harness();
  const pending = request({ url: '/checkins' });
  calls.requests[0].fail({ errMsg: 'network' });
  assert.equal(calls.requests.length, 2);
  calls.requests[1].fail({ errMsg: 'network' });
  await assert.rejects(pending, err => err.message.includes('网络连接失败'));
  assert.equal(calls.requests.length, 2);
  assert.equal(calls.hide, 1);
  assert.equal(calls.toasts, 1);
});

test('POST 网络失败不自动重试，避免重复写入', async () => {
  const { calls, request } = harness();
  const pending = request({ url: '/checkins', method: 'POST' });
  calls.requests[0].fail({ errMsg: 'timeout' });
  await assert.rejects(pending);
  assert.equal(calls.requests.length, 1);
  assert.equal(calls.hide, 1);
});

test('HTTP 401 保留错误状态，不按成功响应处理或重试', async () => {
  const { calls, request } = harness();
  const pending = request({ url: '/private' });
  calls.requests[0].success({ statusCode: 401, data: { code: 'UNAUTHORIZED' } });
  await assert.rejects(pending, err => err.statusCode === 401 && err.data.code === 'UNAUTHORIZED');
  assert.equal(calls.requests.length, 1);
  assert.equal(calls.hide, 1);
});

test('并发请求全部结束后只关闭一次 loading', async () => {
  const { calls, request } = harness();
  const first = request({ url: '/first' });
  const second = request({ url: '/second' });
  assert.equal(calls.show, 1);
  calls.requests[0].success({ statusCode: 200, data: {} });
  await first;
  assert.equal(calls.hide, 0);
  calls.requests[1].success({ statusCode: 200, data: {} });
  await second;
  assert.equal(calls.hide, 1);
});
