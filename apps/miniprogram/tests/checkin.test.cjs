const { test } = require('node:test');
const assert = require('node:assert/strict');
const {
  EMOTION_CODES,
  FALLBACK_WORDS,
  normalizeWords,
  normalizeScale,
  validateCheckin,
  buildCheckinPayload,
} = require('../utils/checkin.js');

test('契约词表被规范化为页面可用的 code/label/color', () => {
  const words = normalizeWords({
    words: [
      { code: 'HAPPY', label: '开心', colorToken: 'emotion.happy' },
      { code: 'CALM', label: '平静', colorToken: 'emotion.calm' },
    ],
    intensityScale: { min: 1, max: 5 },
  });
  assert.equal(words.length, 2);
  assert.equal(words[0].code, 'HAPPY');
  assert.equal(words[0].label, '开心');
  assert.ok(words[0].color.startsWith('#'));
  assert.equal(EMOTION_CODES.includes(words[1].code), true);
});

test('词表为空、缺字段或含非法 code 时回退到本地兜底', () => {
  assert.deepEqual(normalizeWords(null), FALLBACK_WORDS);
  assert.deepEqual(normalizeWords({ words: [] }), FALLBACK_WORDS);
  assert.deepEqual(normalizeWords({ words: [{ code: 'UNKNOWN' }] }), FALLBACK_WORDS);
  assert.equal(FALLBACK_WORDS.length, 6);
});

test('强度量表异常时回退到 1–5', () => {
  assert.deepEqual(normalizeScale({ intensityScale: { min: 1, max: 5 } }), { min: 1, max: 5 });
  assert.deepEqual(normalizeScale(null), { min: 1, max: 5 });
  assert.deepEqual(normalizeScale({ intensityScale: { min: 5, max: 1 } }), { min: 1, max: 5 });
  assert.deepEqual(normalizeScale({ intensityScale: { min: 1, max: 999 } }), { min: 1, max: 5 });
});

test('校验拦截缺情绪词、强度越界与备注超长', () => {
  assert.equal(validateCheckin({ intensity: 3 }).ok, false);
  assert.equal(validateCheckin({ emotion: 'HAPPY', intensity: 0 }).ok, false);
  assert.equal(validateCheckin({ emotion: 'HAPPY', intensity: 6 }).ok, false);
  assert.equal(validateCheckin({ emotion: 'HAPPY', intensity: 3, note: 'x'.repeat(101) }).ok, false);
  assert.equal(validateCheckin({ emotion: 'HAPPY', intensity: 3 }).ok, true);
});

test('payload 只含契约字段并去掉备注首尾空白', () => {
  assert.deepEqual(buildCheckinPayload({ emotion: 'CALM', intensity: 4, note: '  今天还行  ' }), {
    emotion: 'CALM',
    intensity: 4,
    note: '今天还行',
  });
  assert.deepEqual(buildCheckinPayload({ emotion: 'DOWN', intensity: '2', note: '  ' }), {
    emotion: 'DOWN',
    intensity: 2,
  });
});
