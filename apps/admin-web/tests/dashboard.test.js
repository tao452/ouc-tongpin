import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ElementPlus from 'element-plus'
import * as echarts from 'echarts'
import DataBoard from '../src/views/DataBoard.vue'

vi.mock('echarts', () => ({
  init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })),
  graphic: { LinearGradient: vi.fn() },
}))

afterEach(() => vi.clearAllMocks())

describe('数据看板组件', () => {
  it('展示统计卡片，并把趋势和分布数据交给两个图表', () => {
    const wrapper = mount(DataBoard, { global: { plugins: [ElementPlus] } })
    expect(wrapper.findAll('.stat-card')).toHaveLength(4)
    expect(wrapper.text()).toContain('今日打卡次数')
    expect(echarts.init).toHaveBeenCalledTimes(2)
    const trend = echarts.init.mock.results[0].value
    const distribution = echarts.init.mock.results[1].value
    expect(trend.setOption.mock.calls[0][0].series[0].data).toHaveLength(7)
    expect(distribution.setOption.mock.calls[0][0].series[0].data.length).toBeGreaterThan(0)
  })

  it('窗口变化时调整图表，离开页面后销毁图表并解除监听', () => {
    const wrapper = mount(DataBoard, { global: { plugins: [ElementPlus] } })
    const charts = echarts.init.mock.results.map(result => result.value)
    window.dispatchEvent(new Event('resize'))
    charts.forEach(chart => expect(chart.resize).toHaveBeenCalledOnce())
    wrapper.unmount()
    charts.forEach(chart => expect(chart.dispose).toHaveBeenCalledOnce())
    window.dispatchEvent(new Event('resize'))
    charts.forEach(chart => expect(chart.resize).toHaveBeenCalledOnce())
  })
})
