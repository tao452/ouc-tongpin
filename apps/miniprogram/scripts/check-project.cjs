const assert = require('node:assert/strict');
const { readFileSync, existsSync, readdirSync, statSync } = require('node:fs');
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
// 页面跳转静态校验（PR#59 合入后出现「日历页跳到已删除页面」的断链，
// 原有检查只看注册页面的四件套和组件引用，抓不到跨文件跳转，故补此规则）。
// 规则一：/pages/... 目标必须在 app.json 注册；
// 规则二：tabBar 页面必须用 switchTab / reLaunch，不能用 navigateTo / redirectTo。
const registeredPages = new Set(pages);
const tabPages = new Set((app.tabBar?.list || []).map((item) => item.pagePath));
const jsFiles = [];
const collectJs = (dir) => {
  for (const name of readdirSync(dir)) {
    const full = resolve(dir, name);
    if (statSync(full).isDirectory()) collectJs(full);
    else if (name.endsWith('.js')) jsFiles.push(full);
  }
};
collectJs(resolve(root, 'pages'));
let navCount = 0;
for (const file of jsFiles) {
  const content = readFileSync(file, 'utf8');
  const apiRe = /wx\.(navigateTo|switchTab|redirectTo|reLaunch)\s*\(/g;
  let nav;
  while ((nav = apiRe.exec(content)) !== null) {
    const scope = content.slice(nav.index, nav.index + 500);
    const urlMatch = /url:\s*(['"`])([^'"`]+)\1/.exec(scope);
    if (!urlMatch || !urlMatch[2].startsWith('/pages/')) continue;
    const raw = urlMatch[2];
    const pagePath = raw.slice(1).split('?')[0];
    const where = `${relative(root, file)} → ${raw}`;
    assert.ok(registeredPages.has(pagePath), `跳转目标未在 app.json 注册：${where}`);
    if (tabPages.has(pagePath)) {
      assert.ok(
        nav[1] === 'switchTab' || nav[1] === 'reLaunch',
        `tabBar 页必须用 switchTab/reLaunch：${where}（当前 ${nav[1]}）`
      );
    }
    navCount += 1;
  }
}
console.log(`项目配置有效，${pages.length} 个页面及其组件引用通过检查；${navCount} 条页面跳转链路有效。`);
