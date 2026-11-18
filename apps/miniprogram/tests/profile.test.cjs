const { test } = require('node:test');
const assert = require('node:assert/strict');
const {
  LIMITS,
  normalizeProfile,
  validateProfile,
  parseTagInput,
  buildPayload,
} = require('../utils/profile.js');

test('空态：首次进入或脏数据不会让页面白屏', () => {
  assert.deepEqual(normalizeProfile(null), {
    nickname: '', avatarUrl: '', bio: '', interestTags: [], skillTags: [],
  });
  assert.deepEqual(normalizeProfile({ interestTags: 'not-an-array' }), {
    nickname: '', avatarUrl: '', bio: '', interestTags: [], skillTags: [],
  });
  const empty = validateProfile({});
  assert.equal(empty.valid, false);
  assert.ok(empty.errors[0].includes('昵称'));
});

test('请求体严格等于 openapi 契约的 5 个字段', () => {
  const payload = buildPayload({
    nickname: '  林同学  ',
    avatarUrl: 'https://example.invalid/a.png',
    bio: '喜欢夜跑',
    interestTags: ['跑步'],
    skillTags: ['Python'],
    unexpected: 'should-not-leak',
  });
  assert.deepEqual(Object.keys(payload).sort(), [
    'avatarUrl', 'bio', 'interestTags', 'nickname', 'skillTags',
  ]);
  assert.equal(payload.nickname, '林同学');
  assert.equal('unexpected' in payload, false);
});

test('标签去空、去重、限量、单条截断', () => {
  const result = normalizeProfile({
    nickname: 'A',
    interestTags: [' 跑步 ', '', '跑步', '摄影', '超长标签'.repeat(10)],
    skillTags: ['Python', 'Python', 'Vue'],
  });
  assert.deepEqual(result.skillTags, ['Python', 'Vue']);
  assert.equal(result.interestTags.length, 3);
  assert.ok(result.interestTags.every(tag => tag.length <= LIMITS.tag));
  assert.equal(new Set(result.interestTags).size, result.interestTags.length);
});

test('异常与边界：超长昵称、超长简介、标签超限都有明确提示', () => {
  const tooLong = validateProfile({
    nickname: 'A'.repeat(LIMITS.nickname + 1),
    bio: 'B'.repeat(LIMITS.bio + 1),
    interestTags: Array.from({ length: LIMITS.tags + 1 }, (_, i) => `标签${i}`),
  });
  assert.equal(tooLong.valid, false);
  assert.equal(tooLong.errors.length, 3);
  assert.ok(tooLong.errors.some(e => e.includes('昵称')));
  assert.ok(tooLong.errors.some(e => e.includes('简介')));
  assert.ok(tooLong.errors.some(e => e.includes('最多')));
});

test('校验不会悄悄吞掉超长输入（裁剪只发生在 normalize）', () => {
  const raw = { nickname: 'C'.repeat(50), bio: '', interestTags: [] };
  assert.equal(validateProfile(raw).valid, false);
  assert.equal(normalizeProfile(raw).nickname.length, LIMITS.nickname);
});

test('批量输入支持中英文逗号、顿号与空格', () => {
  assert.deepEqual(parseTagInput('跑步，摄影、Python 吉他'), ['跑步', '摄影', 'Python', '吉他']);
  assert.deepEqual(parseTagInput('   '), []);
});

test('正常资料通过校验，可直接提交', () => {
  const result = validateProfile({
    nickname: '林同学',
    bio: '热爱夜跑和摄影',
    interestTags: ['跑步'],
    skillTags: ['Python'],
  });
  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, []);
  assert.equal(result.profile.nickname, '林同学');
});
