import { build } from 'esbuild';
import { readFile, writeFile, mkdir, copyFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
process.chdir(dirname(fileURLToPath(import.meta.url)));
const out = '../plugins/opl-image/miniapp';
await mkdir(out, { recursive: true });
const ui = await build({ entryPoints: ['app.js'], bundle: true, format: 'esm', platform: 'browser', write: false, minify: true, legalComments: 'inline' });
const template = await readFile('index.html', 'utf8');
const style = await readFile('dsh-theme.css', 'utf8') + '\n' + await readFile('style.css', 'utf8');
await writeFile(out + '/index.html', template.replace('/* STYLE */', () => style).replace('/* SCRIPT */', () => ui.outputFiles[0].text.replace(/<\/script/gi, '<\\/script')));
await copyFile('DSH-LICENSE.txt', out + '/DSH-LICENSE.txt');
await build({ entryPoints: ['server.mjs'], outfile: out + '/server.mjs', bundle: true, platform: 'node', format: 'esm', target: 'node22', legalComments: 'inline', banner: { js: 'import { createRequire as _createRequire } from "node:module"; const require = _createRequire(import.meta.url);' } });
let notices = 'OPL Image Lab third-party notices\n\n';
const lock = JSON.parse(await readFile('package-lock.json', 'utf8'));
for (const [path, entry] of Object.entries(lock.packages)) {
  if (!path || entry.dev) continue;
  const pkg = JSON.parse(await readFile(path + '/package.json', 'utf8'));
  notices += `${pkg.name} ${pkg.version} (${pkg.license || entry.license || 'See upstream'})\n`;
  for (const file of (await readdir(path)).filter(name => /^(licen[sc]e|copying|notice)(\.|$)/i.test(name))) {
    try { notices += await readFile(path + '/' + file, 'utf8') + '\n'; } catch {}
  }
  notices += '\n';
}
await writeFile(out + '/THIRD_PARTY_NOTICES.txt', notices.replace(/\r\n/g, '\n').replace(/[ \t]+$/gm, '').trimEnd() + '\n');
const manifestPath = '../plugins/opl-image/opl-package.json';
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
const runtimeFiles = ['scripts/settings.py', 'scripts/image_tasks.py', 'scripts/manage.py', 'scripts/redirect.py', 'scripts/download_model.py', 'custom_nodes/qwen_rapid/__init__.py', 'custom_nodes/qwen_rapid/image_io.py', 'custom_nodes/qwen_rapid/workbench_http.py', 'custom_nodes/qwen_rapid/web/workbench.js', 'custom_nodes/qwen_rapid/example_workflows/QwenPhoto.json', 'custom_nodes/qwen_rapid/example_workflows/QwenTextToImage.json', 'workflows/edit-api.json', 'model-profile.json', 'requirements.txt', 'LICENSE', 'NOTICE'];
for (const path of runtimeFiles) {
  await mkdir(dirname(resolve('../plugins/opl-image', path)), { recursive: true });
  await copyFile('../' + path, '../plugins/opl-image/' + path);
}
manifest.content_lock.paths = [...new Set(['mcp.json', 'plugin.json', 'skills/opl-image/SKILL.md', 'miniapp/server.mjs', 'miniapp/index.html', 'miniapp/DSH-LICENSE.txt', 'miniapp/THIRD_PARTY_NOTICES.txt', 'LOCAL_ACCESS.md', ...runtimeFiles])];
const digest = createHash('sha256');
for (const path of manifest.content_lock.paths) {
  const name = Buffer.from(path), bytes = await readFile('../plugins/opl-image/' + path);
  for (const value of [name, bytes]) { const size = Buffer.alloc(8); size.writeBigUInt64BE(BigInt(value.length)); digest.update(size); digest.update(value); }
}
manifest.content_lock.digest = 'sha256:' + digest.digest('hex');
await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
