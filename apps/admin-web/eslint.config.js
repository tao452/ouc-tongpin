import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**'] },
  { files: ['**/*.{js,ts,vue}'], extends: [js.configs.recommended] },
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      globals: { ...globals.browser, ...globals.node },
    },
  },
  { files: ['**/*.ts'], extends: [...tseslint.configs.recommended] },
  {
    files: ['**/*.vue'],
    languageOptions: { parserOptions: { parser: tseslint.parser } },
    rules: { 'vue/multi-word-component-names': 'off' },
  },
  {
    files: ['src/**/*.{js,ts,vue}'],
    rules: { 'no-console': ['error', { allow: ['warn', 'error'] }] },
  },
)
