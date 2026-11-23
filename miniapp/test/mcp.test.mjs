import test from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdtemp, rm, realpath, cp, readFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

test('installed payload exposes standard UI and the same local owner to a no-UI client', async () => {
  const marketplace = JSON.parse(await readFile(resolve(repoRoot, '.agents/plugins/marketplace.json'), 'utf8'));
  assert.equal(marketplace.plugins[0].source.path, '.');
  const mcp = JSON.parse(await readFile(resolve(repoRoot, 'mcp.json'), 'utf8'));
  const entryArg = mcp.mcpServers['opl-image'].args[0];
  assert.equal(entryArg, '${PLUGIN_ROOT}/miniapp/dist/server.mjs');
  const manifest = JSON.parse(await readFile(resolve(repoRoot, 'opl-package.json'), 'utf8'));
  const digest = createHash('sha256');
  for (const path of manifest.content_lock.paths) {
    const name = Buffer.from(path), bytes = await readFile(resolve(repoRoot, path));
    for (const value of [name, bytes]) { const size = Buffer.alloc(8); size.writeBigUInt64BE(BigInt(value.length)); digest.update(size); digest.update(value); }
  }
  assert.equal('sha256:' + digest.digest('hex'), manifest.content_lock.digest);

  const client = new Client({ name: 'image-contract-test', version: '1' }, { capabilities: {} });
  const temporary = await mkdtemp(resolve(tmpdir(), 'opl-image-test-'));
  const workspace = resolve(temporary, 'personal data');
  const payload = resolve(temporary, 'installed plugin');
  await cp(resolve(repoRoot, 'opl-package.json'), resolve(payload, 'opl-package.json'));
  for (const path of manifest.content_lock.paths) {
    await mkdir(dirname(resolve(payload, path)), { recursive: true });
    await cp(resolve(repoRoot, path), resolve(payload, path));
  }
  await cp(resolve(repoRoot, 'miniapp/dist'), resolve(payload, 'miniapp/dist'), { recursive: true });
  const serverEntry = resolve(payload, entryArg.replace('${PLUGIN_ROOT}/', ''));
  await client.connect(new StdioClientTransport({ command: 'node', args: [serverEntry], cwd: temporary, env: { ...process.env, OPL_IMAGE_WORKSPACE: workspace, OPL_IMAGE_PYTHON: process.env.OPL_IMAGE_PYTHON || 'python3' } }));
  try {
    const { tools } = await client.listTools();
    assert.equal(tools.find(t => t.name === 'open_image_workbench')._meta.ui.resourceUri, 'ui://opl-image/workbench.html');
    assert.equal(tools.find(t => t.name === 'open_image_workbench').annotations.readOnlyHint, true);
    assert.deepEqual(tools.find(t => t.name === 'image_read_asset')._meta.ui.visibility, ['app']);
    const resource = await client.readResource({ uri: 'ui://opl-image/workbench.html' });
    assert.equal(resource.contents[0].mimeType, 'text/html;profile=mcp-app');
    assert.ok(resource.contents[0].text.includes('data-opl-family="opl-apps"'));
    const result = await client.callTool({ name: 'open_image_workbench', arguments: {} });
    assert.ok(!result.isError); assert.equal(typeof result.structuredContent.service.ready, 'boolean');
    assert.equal(result.structuredContent.workspace, await realpath(workspace));
    const invalid = await client.callTool({ name: 'image_get_task', arguments: { task_id: crypto.randomUUID() } });
    assert.equal(invalid.isError, true);
  } finally { await client.close(); await rm(temporary, { recursive: true, force: true }); }
});
