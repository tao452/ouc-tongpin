import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ElementPlus, { ElMessage } from 'element-plus'
import Login from '../src/views/Login.vue'

vi.mock('element-plus', async importOriginal => ({
  ...await importOriginal(), ElMessage: { success: vi.fn() },
}))

afterEach(() => vi.useRealTimers())

describe('登录表单的当前模拟交互', () => {
  it('空表单显示校验错误，不显示登录成功', async () => {
    const wrapper = mount(Login, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()
    await vi.waitFor(() => expect(wrapper.findAll('.el-form-item__error')).toHaveLength(2))
    expect(ElMessage.success).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('后台管理系统')
  })

  it('模拟提交等待完成后恢复按钮，控制台不输出账号或密码', async () => {
    vi.useFakeTimers()
    const log = vi.spyOn(console, 'log').mockImplementation(() => {})
    const wrapper = mount(Login, { global: { plugins: [ElementPlus] } })
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('synthetic-user')
    await inputs[1].setValue('synthetic-password')
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.login-btn').classes()).toContain('is-loading')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()
    expect(ElMessage.success).toHaveBeenCalledOnce()
    expect(wrapper.find('.login-btn').classes()).not.toContain('is-loading')
    expect(log).not.toHaveBeenCalled()
  })
})
