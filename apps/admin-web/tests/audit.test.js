import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ElementPlus, { ElMessage, ElMessageBox } from 'element-plus'
import Audit from '../src/views/Audit.vue'

vi.mock('element-plus', async importOriginal => ({
  ...await importOriginal(),
  ElMessage: { success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

function page() {
  return mount(Audit, { global: { plugins: [ElementPlus] } })
}

async function selectFirst(wrapper) {
  await flushPromises()
  await wrapper.find('tbody input[type="checkbox"]').setValue(true)
}

describe('审核工作台的当前本地交互', () => {
  it('没有选择时禁止批量操作', () => {
    const wrapper = page()
    expect(wrapper.findAll('tbody tr')).toHaveLength(6)
    wrapper.findAll('.header-actions button').forEach(button => {
      expect(button.attributes('disabled')).toBeDefined()
    })
  })

  it('选择一条后批量通过，只移除所选记录', async () => {
    const wrapper = page()
    await selectFirst(wrapper)
    await wrapper.find('.header-actions button').trigger('click')
    await flushPromises()
    expect(ElMessage.success).toHaveBeenCalledWith(expect.stringContaining('1001'))
    expect(wrapper.findAll('tbody tr')).toHaveLength(5)
    expect(wrapper.text()).not.toContain('张三')
    expect(wrapper.text()).toContain('李四')
  })

  it('取消驳回时保留原记录', async () => {
    ElMessageBox.confirm.mockRejectedValueOnce('cancel')
    const wrapper = page()
    await selectFirst(wrapper)
    await wrapper.findAll('.header-actions button')[1].trigger('click')
    await flushPromises()
    expect(ElMessageBox.confirm).toHaveBeenCalledOnce()
    expect(ElMessage.warning).not.toHaveBeenCalled()
    expect(wrapper.findAll('tbody tr')).toHaveLength(6)
  })

  it('确认驳回后移除所选记录并反馈结果', async () => {
    ElMessageBox.confirm.mockResolvedValueOnce('confirm')
    const wrapper = page()
    await selectFirst(wrapper)
    await wrapper.findAll('.header-actions button')[1].trigger('click')
    await flushPromises()
    expect(ElMessage.warning).toHaveBeenCalledWith(expect.stringContaining('1001'))
    expect(wrapper.findAll('tbody tr')).toHaveLength(5)
  })
})
