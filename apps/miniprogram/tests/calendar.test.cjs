const { test } = require('node:test');
const assert = require('node:assert/strict');
const {
  WEEK,
  EMOTION_COLOR,
  daysInMonth,
  getMonthRange,
  shiftMonth,
  buildMonthGrid,
  normalizeCheckins,
} = require('../utils/calendar.js');

test('月份天数按真实日历计算，包含闰年二月', () => {
  assert.equal(daysInMonth(2026, 11), 30);
  assert.equal(daysInMonth(2026, 2), 28);
  assert.equal(daysInMonth(2024, 2), 29);
  assert.equal(daysInMonth(2000, 2), 29);
  assert.equal(daysInMonth(1900, 2), 28);
  assert.equal(daysInMonth(2026, 12), 31);
  assert.equal(daysInMonth(2026, 4), 30);
});

test('回归：所有月份生成的区间末日都是合法日期（后端 LocalDate.parse 会拒绝 11-31）', () => {
  // JS 的 new Date('2026-11-31') 会静默滚到 12-01，但 Java LocalDate.parse 直接抛 400，
  // 所以必须回读校验，不能只看字符串格式。
  for (let year = 2020; year <= 2030; year++) {
    for (let month = 1; month <= 12; month++) {
      const { from, to } = getMonthRange(year, month);
      const parsed = new Date(`${to}T00:00:00Z`);
      assert.equal(
        parsed.toISOString().slice(0, 10),
        to,
        `${year}-${month} 生成了非法日期 ${to}`
      );
      assert.equal(from.slice(-2), '01');
      assert.equal(to, `${year}-${String(month).padStart(2, '0')}-${String(daysInMonth(year, month)).padStart(2, '0')}`);
    }
  }
});

test('关键回归：2026 年 11 月请求 11-01 ~ 11-30，不再是 11-31', () => {
  assert.deepEqual(getMonthRange(2026, 11), {
    from: '2026-11-01',
    to: '2026-11-30',
  });
});

test('翻月正确处理跨年边界', () => {
  assert.deepEqual(shiftMonth(2026, 1, -1), { year: 2025, month: 12 });
  assert.deepEqual(shiftMonth(2026, 12, 1), { year: 2027, month: 1 });
  assert.deepEqual(shiftMonth(2026, 11, 1), { year: 2026, month: 12 });
  assert.deepEqual(shiftMonth(2026, 11, -12), { year: 2025, month: 11 });
});

test('网格补齐首日空白且每个格子都有唯一 key', () => {
  const cells = buildMonthGrid(2026, 11, { '2026-11-14': 'HAPPY' });
  const first = new Date(2026, 10, 1).getDay();
  assert.equal(cells.length, first + 30);
  // 2026-11-01 恰好是星期日，此时没有前置空格；用个数断言以兼容任意月份。
  assert.equal(cells.filter((c) => c.empty).length, first);
  assert.equal(cells.filter((c) => !c.empty).length, 30);
  assert.equal(new Set(cells.map((c) => c.key)).size, cells.length);

  const marked = cells.find((c) => c.date === '2026-11-14');
  assert.equal(marked.emotion, 'HAPPY');
  assert.equal(marked.color, EMOTION_COLOR.HAPPY);
  assert.equal(cells.find((c) => c.date === '2026-11-15').color, '');
});

test('未知情绪不产生背景色，checkedDates 为空也能渲染', () => {
  const cells = buildMonthGrid(2026, 2, { '2026-02-01': 'UNKNOWN' });
  assert.equal(cells.find((c) => c.date === '2026-02-01').color, '');
  assert.equal(buildMonthGrid(2026, 2, null).filter((c) => !c.empty).length, 28);
  assert.equal(WEEK.length, 7);
});

test('响应规范化：total 是本月条数而非历史累计，异常响应不抛错', () => {
  const normalized = normalizeCheckins({
    items: [
      { checkinDate: '2026-11-14', emotion: 'HAPPY' },
      { checkinDate: '2026-11-15', emotion: 'CALM' },
      { checkinDate: null, emotion: 'DOWN' },
    ],
    streakDays: 2,
    total: 2,
  });
  assert.deepEqual(normalized.checkedDates, {
    '2026-11-14': 'HAPPY',
    '2026-11-15': 'CALM',
  });
  assert.equal(normalized.monthTotal, 2); // 采信契约 total，而不是 items.length
  assert.equal(normalized.streakDays, 2);
  // total 缺失时退回实际条目数，保证页面不会显示 0
  assert.equal(normalizeCheckins({ items: [{ checkinDate: '2026-11-14' }] }).monthTotal, 1);

  const empty = normalizeCheckins(null);
  assert.deepEqual(empty.checkedDates, {});
  assert.equal(empty.monthTotal, 0);
  assert.equal(empty.streakDays, 0);
  assert.deepEqual(normalizeCheckins({ items: 'bad' }).checkedDates, {});
});
