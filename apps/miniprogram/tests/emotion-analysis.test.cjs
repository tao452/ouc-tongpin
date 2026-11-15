const { test } = require('node:test');
const assert = require('node:assert/strict');
const {
  RANGE_DAYS,
  EMOTIONS,
  normalizeRange,
  getWindowRange,
  buildAnalysis,
} = require('../utils/emotion-analysis.js');
const { EMOTION_CODES, EMOTION_COLOR } = require('../utils/checkin.js');

const TODAY = new Date(2026, 10, 15); // 2026-11-15，本地时间，避免 UTC 偏移影响

function item(date, emotion, intensity) {
  return { checkinDate: date, emotion, intensity };
}

function utcDays(a, b) {
  const [ay, am, ad] = a.split('-').map(Number);
  const [by, bm, bd] = b.split('-').map(Number);
  return (Date.UTC(by, bm - 1, bd) - Date.UTC(ay, am - 1, ad)) / 86400000;
}

test('窗口只接受 7 / 30 天，非法值回落 7 天', () => {
  assert.deepEqual(RANGE_DAYS, [7, 30]);
  assert.equal(normalizeRange(7), 7);
  assert.equal(normalizeRange(30), 30);
  assert.equal(normalizeRange('30'), 30);
  assert.equal(normalizeRange(31), 7);
  assert.equal(normalizeRange(undefined), 7);
});

test('近 7 天是含今天的滚动窗口，to 恒为今天，共 7 个点', () => {
  assert.deepEqual(getWindowRange(7, TODAY), {
    from: '2026-11-09',
    to: '2026-11-15',
  });

  const result = buildAnalysis([], 7, TODAY);
  assert.equal(result.trendData.length, 7);
  assert.equal(result.trendData[0].date, '2026-11-09');
  assert.equal(result.trendData[6].date, '2026-11-15');
  assert.equal(result.trendData[6].label, '11/15');
  assert.equal(result.from, '2026-11-09');
  assert.equal(result.to, '2026-11-15');
});

test('近 30 天跨月 / 跨年由 Date 自动进位，不手拼月末', () => {
  assert.deepEqual(getWindowRange(30, new Date(2027, 0, 2)), {
    from: '2026-12-04',
    to: '2027-01-02',
  });
  assert.deepEqual(getWindowRange(30, new Date(2026, 2, 1)), {
    from: '2026-01-31',
    to: '2026-03-01',
  });
  assert.deepEqual(getWindowRange(7, new Date(2026, 2, 1)), {
    from: '2026-02-23',
    to: '2026-03-01',
  });
  assert.equal(buildAnalysis([], 30, new Date(2027, 0, 2)).trendData.length, 30);
});

test('回归 B14：2020–2030 每月抽样的窗口端日都是合法日期且间隔恰好 N-1 天', () => {
  for (let year = 2020; year <= 2030; year++) {
    for (let month = 1; month <= 12; month++) {
      const last = new Date(year, month, 0).getDate();
      for (const day of [1, 15, last]) {
        const today = new Date(year, month - 1, day);
        for (const days of RANGE_DAYS) {
          const { from, to } = getWindowRange(days, today);
          assert.equal(to, `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`);
          // 非法日期（如 11-31）回读后会被 JS 静默滚到下个月，这里用回读 + 间隔双重校验
          assert.equal(utcDays(from, to), days - 1, `${from} ~ ${to} 不是 ${days} 天窗口`);
          for (const value of [from, to]) {
            const [y, m, d] = value.split('-').map(Number);
            const parsed = new Date(y, m - 1, d);
            assert.equal(parsed.getFullYear(), y);
            assert.equal(parsed.getMonth() + 1, m);
            assert.equal(parsed.getDate(), d);
          }
        }
      }
    }
  }
});

test('空态：不画 0 值折线、不显示 0% 分布图，未打卡天数单独给出', () => {
  const result = buildAnalysis([], 7, TODAY);
  assert.equal(result.analysisTotal, 0);
  assert.equal(result.missingDays, 7);
  assert.equal(result.hasData, false);
  assert.ok(result.trendData.every((p) => p.intensity === null && p.missing === true));
  assert.ok(result.trendData.every((p) => p.intensity !== 0), '不能把断签补成强度 0');
  assert.ok(result.distributionData.every((d) => d.count === 0 && d.percent === 0));
});

test('只有 1 条记录：折线单点、该项 100%，其余显示 0%', () => {
  const result = buildAnalysis([item('2026-11-15', 'HAPPY', 4)], 7, TODAY);
  assert.equal(result.analysisTotal, 1);
  assert.equal(result.missingDays, 6);
  assert.equal(result.trendData.filter((p) => p.intensity !== null).length, 1);
  assert.equal(result.trendData[6].intensity, 4);
  assert.equal(result.distributionData.find((d) => d.code === 'HAPPY').percent, 100);
  assert.ok(result.distributionData.filter((d) => d.code !== 'HAPPY').every((d) => d.percent === 0));
});

test('中间断签：折线留空断开，不出现强度 0 的假低谷', () => {
  const result = buildAnalysis([
    item('2026-11-09', 'CALM', 3),
    item('2026-11-11', 'DOWN', 2),
    item('2026-11-15', 'HAPPY', 5),
  ], 7, TODAY);
  assert.equal(result.analysisTotal, 3);
  assert.equal(result.missingDays, 4);
  assert.equal(result.trendData[0].intensity, 3);
  assert.equal(result.trendData[1].intensity, null); // 11-10 断签
  assert.equal(result.trendData[2].intensity, 2);
  assert.equal(result.trendData[6].intensity, 5);
  assert.ok(result.trendData.every((p) => p.intensity === null || p.intensity >= 1));
});

test('全部同一情绪：分布 100%，不除零、不 NaN', () => {
  const result = buildAnalysis([
    item('2026-11-13', 'ANXIOUS', 2),
    item('2026-11-14', 'ANXIOUS', 4),
    item('2026-11-15', 'ANXIOUS', 5),
  ], 7, TODAY);
  assert.equal(result.analysisTotal, 3);
  const anxious = result.distributionData.find((d) => d.code === 'ANXIOUS');
  assert.equal(anxious.count, 3);
  assert.equal(anxious.percent, 100);
  assert.ok(result.distributionData.every((d) => Number.isFinite(d.percent)));
});

test('强度边界 1 / 5 正常保留，不自动缩放纵轴', () => {
  const result = buildAnalysis([
    item('2026-11-14', 'LONELY', 1),
    item('2026-11-15', 'IRRITABLE', 5),
  ], 7, TODAY);
  assert.equal(result.trendData[5].intensity, 1);
  assert.equal(result.trendData[6].intensity, 5);
});

test('回归 B16：同日多条只取当日唯一一条，不做平均', () => {
  const result = buildAnalysis([
    item('2026-11-15', 'HAPPY', 2),
    item('2026-11-15', 'DOWN', 4),
  ], 7, TODAY);
  assert.equal(result.analysisTotal, 1, '幂等下一天最多一条，不能算成 2 条');
  assert.equal(result.trendData[6].intensity, 2, '不能取 (2+4)/2 = 3');
  assert.equal(result.trendData[6].emotion, 'HAPPY');
  assert.equal(result.distributionData.find((d) => d.code === 'HAPPY').count, 1);
  assert.equal(result.distributionData.find((d) => d.code === 'DOWN').count, 0);
});

test('非法 / 越界 / 窗口外 / 空响应一律忽略，不污染统计', () => {
  const result = buildAnalysis([
    null,
    item('2026-11-15', 'UNKNOWN', 3),
    item('2026-11-15', 'HAPPY', 0),
    item('2026-11-15', 'HAPPY', 6),
    item('2026-11-14', 'CALM', 3.5),
    item('2026-11-01', 'DOWN', 4), // 7 天窗口外
    item('bad-date', 'HAPPY', 3),
    item('2026-11-15', 'CALM', 3),
  ], 7, TODAY);
  assert.equal(result.analysisTotal, 1);
  assert.equal(result.trendData[6].intensity, 3);
  assert.equal(result.trendData[6].emotion, 'CALM');
  assert.deepEqual(buildAnalysis(null, 7, TODAY).distributionData.map((d) => d.percent), [0, 0, 0, 0, 0, 0]);
});

test('六种情绪固定顺序与颜色，不按占比动态排序', () => {
  const result = buildAnalysis([item('2026-11-15', 'DOWN', 2)], 7, TODAY);
  assert.deepEqual(result.distributionData.map((d) => d.code), EMOTION_CODES);
  assert.deepEqual(EMOTIONS.map((e) => e.code), EMOTION_CODES);
  result.distributionData.forEach((d) => {
    assert.equal(d.color, EMOTION_COLOR[d.code]);
  });
});

test('分布按有效记录条数计占比，未打卡日不进分母', () => {
  const result = buildAnalysis([
    item('2026-11-09', 'HAPPY', 3),
    item('2026-11-10', 'CALM', 4),
    item('2026-11-11', 'HAPPY', 2),
  ], 7, TODAY);
  assert.equal(result.analysisTotal, 3, '分母是 3 条记录而不是 7 天');
  assert.equal(result.missingDays, 4);
  assert.equal(result.distributionData.find((d) => d.code === 'HAPPY').percent, 67);
  assert.equal(result.distributionData.find((d) => d.code === 'CALM').percent, 33);
  assert.equal(result.distributionData.reduce((sum, d) => sum + d.count, 0), 3);
});

test('切换 7 ↔ 30 天按各自窗口重新聚合，不串数据', () => {
  const items = [
    item('2026-10-20', 'DOWN', 2), // 只在 30 天窗口内
    item('2026-11-14', 'HAPPY', 4),
    item('2026-11-15', 'CALM', 3),
  ];
  const week = buildAnalysis(items, 7, TODAY);
  const month = buildAnalysis(items, 30, TODAY);
  assert.equal(week.from, '2026-11-09');
  assert.equal(month.from, '2026-10-17');
  assert.equal(week.trendData.length, 7);
  assert.equal(month.trendData.length, 30);
  assert.equal(week.analysisTotal, 2);
  assert.equal(month.analysisTotal, 3);
  assert.equal(week.trendData.find((p) => p.date === '2026-10-20'), undefined);
  assert.equal(month.trendData.find((p) => p.date === '2026-10-20').intensity, 2);
});
