import test from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { resolve } from 'node:path';
import { mkdtemp, rm, realpath, cp } from 'node:fs/promises';
import { tmpdir } from 'node:os';

test('installed payload exposes standard UI and the same local owner to a no-UI client', async () => {
  const client = new Client({ name: 'image-contract-test', version: '1' }, { capabilities: {} });
  const temporary = await mkdtemp(resolve(tmpdir(), 'opl-image-test-'));
  const workspace = resolve(temporary, 'personal data');
  const payload = resolve(temporary, 'installed plugin');
  await cp(resolve('../plugins/opl-image'), payload, { recursive: true });
  await client.connect(new StdioClientTransport({ command: 'node', args: [resolve(payload, 'miniapp/server.mjs')], cwd: temporary, env: { ...process.env, OPL_IMAGE_WORKSPACE: workspace, OPL_IMAGE_PYTHON: process.env.OPL_IMAGE_PYTHON || 'python3' } }));
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
