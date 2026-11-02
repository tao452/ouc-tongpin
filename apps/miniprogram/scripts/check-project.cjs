const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const { resolve, isAbsolute, relative } = require('node:path');

const root = resolve(__dirname, '..');
const app = JSON.parse(readFileSync(resolve(root, 'app.json'), 'utf8'));
const project = JSON.parse(readFileSync(resolve(root, 'project.config.json'), 'utf8'));
assert.equal(project.compileType, 'miniprogram', '项目类型必须是 miniprogram');
assert.ok(app.pages?.length, '主包必须声明页面');
const pages = [...app.pages];
for (const pkg of app.subPackages || app.subpackages || []) {
  for (const page of pkg.pages) pages.push(`${pkg.root}/${page}`);
}
assert.equal(new Set(pages).size, pages.length, '页面路径不能重复');
for (const page of pages) {
  const path = resolve(root, page);
  const rel = relative(root, path);
  assert.ok(!isAbsolute(rel) && rel !== '..' && !rel.startsWith('..\\') && !rel.startsWith('../'), '页面必须在项目内');
  for (const ext of ['js', 'json', 'wxml', 'wxss']) {
    assert.ok(existsSync(`${path}.${ext}`), `页面文件缺失：${page}.${ext}`);
  }
  const config = JSON.parse(readFileSync(`${path}.json`, 'utf8'));
  for (const component of Object.values(config.usingComponents || {})) {
    if (component.startsWith('plugin://')) continue;
    let componentPath;
    if (component.startsWith('.')) componentPath = resolve(path, '..', component);
    else if (component.startsWith('/')) componentPath = resolve(root, component.slice(1));
    else {
      const parts = component.split('/');
      const packageLength = component.startsWith('@') ? 2 : 1;
      const packageRoot = resolve(root, 'node_modules', ...parts.slice(0, packageLength));
      const metadata = JSON.parse(readFileSync(resolve(packageRoot, 'package.json'), 'utf8'));
      componentPath = resolve(packageRoot, metadata.miniprogram || '', ...parts.slice(packageLength));
    }
    assert.ok(existsSync(`${componentPath}.json`), `组件配置缺失：${component}`);
  }
}
console.log(`项目配置有效，${pages.length} 个页面及其组件引用通过检查。`);
