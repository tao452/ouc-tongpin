const { test } = require('node:test');
const assert = require('node:assert/strict');
const {
  MAX_CONTENT_LENGTH,
  EMOTION_TAGS,
  EMOTION_CODES,
  formatLocalTime,
  formatRemaining,
  normalizePosts,
  buildListQuery,
  validatePost,
  buildPostPayload,
  failureMessage,
  nextCursor,
} = require('../utils/treehole.js');

const samplePost = {
  id: 7,
  content: '今天复习到很晚，希望明天顺利一点。',
  emotionTag: 'ANXIOUS',
  anonymous: true,
  authorMask: 'anon_v1_FbyO6Q08QprdIfQUfvEbcVYshYMxUw8vOFSm1Gy-pBU',
  createdAt: '2026-11-14T15:07:11.860063166',
  expiresAt: '2026-11-15T15:07:11.860063166',
  hugCount: 0,
};

test('情绪标签与后端 PostCreateReq 的 6 个枚举完全一致', () => {
  assert.equal(EMOTION_TAGS.length, 6);
  assert.deepEqual(EMOTION_CODES, [
    'HAPPY', 'CALM', 'ANXIOUS', 'LONELY', 'IRRITABLE', 'DOWN',
  ]);
  assert.ok(EMOTION_TAGS.every((item) => item.label && item.bg));
});

test('列表查询串按契约拼接 emotionTag 与 cursor', () => {
  assert.equal(buildListQuery(), '/api/treehole/posts');
  assert.equal(buildListQuery({ emotionTag: 'CALM' }), '/api/treehole/posts?emotionTag=CALM');
  assert.equal(
    buildListQuery({ emotionTag: 'HAPPY', cursor: '2' }),
    '/api/treehole/posts?emotionTag=HAPPY&cursor=2'
  );
  assert.equal(buildListQuery({ cursor: '' }), '/api/treehole/posts');
});

test('发布前校验：空白、超长、缺情绪、非法情绪都拦下', () => {
  assert.equal(validatePost({ content: '   ', emotionTag: 'HAPPY' }).ok, false);
  assert.equal(validatePost({ content: 'a'.repeat(501), emotionTag: 'HAPPY' }).ok, false);
  assert.equal(validatePost({ content: '还好', emotionTag: '' }).ok, false);
  assert.equal(validatePost({ content: '还好', emotionTag: 'UNKNOWN' }).ok, false);
  assert.equal(MAX_CONTENT_LENGTH, 500);
  const ok = validatePost({ content: '  还好  ', emotionTag: 'CALM' });
  assert.equal(ok.ok, true);
  assert.equal(ok.content, '还好');
});

test('发布载荷去掉首尾空白，匿名缺省为 true', () => {
  assert.deepEqual(
    buildPostPayload({ content: '  今天有点累  ', emotionTag: 'DOWN' }),
    { content: '今天有点累', emotionTag: 'DOWN', anonymous: true }
  );
  assert.deepEqual(
    buildPostPayload({ content: '散了个步', emotionTag: 'HAPPY', anonymous: false }),
    { content: '散了个步', emotionTag: 'HAPPY', anonymous: false }
  );
});

test('列表响应被规范化为页面字段，匿名掩码不展示全串', () => {
  const now = new Date(2026, 10, 14, 15, 10).getTime();
  const posts = normalizePosts([samplePost], now);
  assert.equal(posts.length, 1);
  assert.equal(posts[0].id, 7);
  assert.equal(posts[0].emotionLabel, '焦虑');
  assert.equal(posts[0].anonymous, true);
  assert.ok(posts[0].authorText.startsWith('匿名同学'));
  assert.ok(!posts[0].authorText.includes('anon_v1_'));
  assert.equal(posts[0].createdText, '11-14 15:07');
  assert.equal(posts[0].remainingText, '剩余 23 小时 57 分');
});

test('实名帖显示昵称；脏数据与缺字段被安全处理', () => {
  const posts = normalizePosts([
    { ...samplePost, id: 8, anonymous: false, authorMask: '新用户' },
    null,
    { id: 9 },
    { ...samplePost, id: 10, emotionTag: 'UNKNOWN', createdAt: null, expiresAt: null },
  ]);
  assert.equal(posts.length, 2);
  assert.equal(posts[0].authorText, '新用户');
  assert.equal(posts[0].anonymous, false);
  assert.equal(posts[1].emotionLabel, '其他');
  assert.equal(posts[1].createdText, '');
  assert.equal(posts[1].remainingText, '');
  assert.deepEqual(normalizePosts(null), []);
});

test('时间格式同时兼容 POST 的纳秒串和 GET 的秒级串', () => {
  assert.equal(formatLocalTime('2026-11-14T15:07:11.860063166'), '11-14 15:07');
  assert.equal(formatLocalTime('2026-11-15T15:07:53'), '11-15 15:07');
  assert.equal(formatLocalTime(''), '');
  assert.equal(formatLocalTime(undefined), '');
  assert.equal(formatLocalTime('not-a-date'), '');
});

test('剩余时间按北京时间本地串计算，到期显示焚毁提示', () => {
  const now = new Date(2026, 10, 14, 20, 0).getTime();
  assert.equal(formatRemaining('2026-11-15T15:07:00', now), '剩余 19 小时 7 分');
  assert.equal(formatRemaining('2026-11-14T20:30:00', now), '剩余 30 分钟');
  assert.equal(formatRemaining('2026-11-14T19:00:00', now), '即将焚毁');
  assert.equal(formatRemaining('2026-11-15T21:00:00', now), '剩余约 24 小时');
  assert.equal(formatRemaining(null, now), '');
});

test('400 / 422 / 503 分别给出与后端一致、且说明「未发布」的提示', () => {
  assert.match(failureMessage(422), /没有发布出去/);
  assert.match(failureMessage(503), /没有发布/);
  assert.equal(failureMessage(400, '内容不能超过 500 字符'), '内容不能超过 500 字符');
  assert.equal(failureMessage(400), '内容或情绪标签不合法，请检查后重试。');
  assert.match(failureMessage(0), /请检查网络/);
});

test('分页游标为空时不继续加载', () => {
  assert.equal(nextCursor({ items: [], nextCursor: null }), '');
  assert.equal(nextCursor({ items: [], nextCursor: '2' }), '2');
  assert.equal(nextCursor(null), '');
});
