// Local qualification fixture only; never an installed product entry.
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { build } from 'esbuild';
import { createServer } from 'node:http';
import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
// A strict qualification fixture. Native Host acceptance is recorded separately.
const sandboxDocument = resource => `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; media-src data: blob:; font-src data:; connect-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'; object-src 'none'">${resource.text}`;
const client = new Client({ name: 'image-sdk-host', version: '1.0.0' }, { capabilities: { extensions: { 'io.modelcontextprotocol/ui': { mimeTypes: ['text/html;profile=mcp-app'] } } } });
await client.connect(new StdioClientTransport({ command: 'node', args: [resolve('../plugins/opl-image/miniapp/server.mjs')], env: process.env }));
const resource = (await client.readResource({ uri: 'ui://opl-image/workbench.html' })).contents[0];
const view = sandboxDocument({ ...resource, text: resource.text });
const script = (await build({ entryPoints: ['test/app-host.js'], bundle: true, write: false, format: 'esm', platform: 'browser' })).outputFiles[0].text;
const allowed = new Set((await client.listTools()).tools.map(t => t.name));
const server = createServer(async (request, response) => {
  const origin = 'http://127.0.0.1:' + server.address().port;
  if (request.headers.origin && request.headers.origin !== origin) { response.writeHead(403).end(); return; }
  const route = request.url.split('?')[0];
  if (route === '/view') { response.setHeader('Content-Type', 'text/html; charset=utf-8'); response.end(view); return; }
  if (route === '/host.js') { response.setHeader('Content-Type', 'text/javascript'); response.end(script); return; }
  if (route === '/tool' && request.method === 'POST') {
    try {
      const chunks = []; let size = 0;
      for await (const chunk of request) { size += chunk.length; if (size > 36 * 1024 * 1024) throw Error('Request too large'); chunks.push(chunk); }
      const input = JSON.parse(Buffer.concat(chunks));
      if (!allowed.has(input.name)) throw Error('Unknown tool');
      response.setHeader('Content-Type', 'application/json'); response.end(JSON.stringify(await client.callTool(input)));
    } catch (error) { response.writeHead(400).end(JSON.stringify({ error: error.message })); }
    return;
  }
  response.setHeader('Content-Type', 'text/html; charset=utf-8');
  response.end('<!doctype html><html><head><title>OPL Image · SDK qualification</title><style>body{margin:0}iframe{border:0;width:100%;height:100vh;display:block}</style></head><body><iframe title="OPL 图片工作台" sandbox="allow-scripts allow-downloads"></iframe><script type="module" src="/host.js"></script></body></html>');
});
server.listen(0, '127.0.0.1', async () => {
  const url = 'http://127.0.0.1:' + server.address().port;
  await writeFile('/tmp/qwen-image-host-url.txt', url); console.log(url);
});
process.on('SIGTERM', async () => { await client.close(); server.close(); process.exit(0); });
