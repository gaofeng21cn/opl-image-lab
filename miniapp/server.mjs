import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps/server';
import { z } from 'zod';
import { spawn } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';

export const uri = 'ui://opl-image/workbench.html';
// Installed payload is self-contained; runtime data stays outside its cache.
const payloadRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const codeRoot = existsSync(resolve(payloadRoot, 'scripts/image_tasks.py')) ? payloadRoot : resolve(payloadRoot, '..');
const root = resolve(process.env.OPL_IMAGE_WORKSPACE || (process.platform === 'darwin' ? resolve(homedir(), 'Library/Application Support/OPL Image Lab') : resolve(process.env.XDG_DATA_HOME || resolve(homedir(), '.local/share'), 'opl-image-lab')));
let settings = {};
try { if (existsSync(resolve(root, 'settings.json'))) settings = JSON.parse(readFileSync(resolve(root, 'settings.json'), 'utf8')); }
catch { throw Error('Runtime settings.json is invalid. Run scripts/setup.py to repair the configuration.'); }
const python = process.env.OPL_IMAGE_PYTHON || settings.python_executable || resolve(root, '.venv/bin/python');
export function invoke(operation, input = {}) {
  return new Promise((accept, reject) => {
    const child = spawn(python, [resolve(codeRoot, 'scripts/image_tasks.py')], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, OPL_IMAGE_WORKSPACE: root } });
    const chunks = []; let bytes = 0;
    const timeout = setTimeout(() => { child.kill(); reject(new Error('操作结果待核对，请查询原任务，避免重复生成。')); }, 55000);
    child.stdout.on('data', chunk => { bytes += chunk.length; if (bytes > 92 * 1024 * 1024) child.kill(); else chunks.push(chunk); });
    child.stderr.resume();
    child.on('error', () => { clearTimeout(timeout); reject(new Error('无法启动图片工作台，请检查本机环境。')); });
    child.on('close', () => {
      clearTimeout(timeout);
      try { const response = JSON.parse(Buffer.concat(chunks).toString()); if (!response.ok) throw Error(response.error); accept(response.result); }
      catch (error) { reject(new Error(error instanceof SyntaxError ? '操作结果待核对，请查询原任务。' : error.message)); }
    });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify({ ...input, operation }));
  });
}

function result(value) {
  const { data_uri, ...metadata } = value;
  return { content: [{ type: 'text', text: JSON.stringify(metadata) }], structuredContent: metadata, ...(data_uri ? { _meta: { data_uri } } : {}) };
}
const id = z.string().uuid();
export function createServer() {
  const server = new McpServer({ name: 'opl-image', version: '0.1.0' }, {
    instructions: '本机 Qwen 图片生成与编辑。open_image_workbench 打开标准图片 MiniApp。生成前查询服务状态；image_control start 只启动本机服务。使用 image_import 登记图片后将 asset_ref 交给 image_generate。每次新任务使用新 UUID；未知结果使用同一 task_id 查询，禁止自动重发。仅取消指定任务。释放内存/停止服务影响所有页面，忙时拒绝。照片与指令在本机处理。',
  });
  registerAppResource(server, 'image-workbench', uri, {}, async () => ({ contents: [{ uri, mimeType: RESOURCE_MIME_TYPE, text: await readFile(new URL('./index.html', import.meta.url), 'utf8'), _meta: { ui: { prefersBorder: true, csp: { connectDomains: [], resourceDomains: [] } } } }] }));
  registerAppTool(server, 'open_image_workbench', {
    title: 'OPL Image Lab · 图像工坊', description: '打开本机图像工坊，生成图片、自然语言改图、比较结果并继续编辑。打开和重开均不启动生成。',
    inputSchema: { task_id: id.optional(), image_ref: z.string().optional() },
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    _meta: { ui: { resourceUri: uri } },
  }, async input => { try { return result({ ...await invoke('status'), focus: input, ...(input.task_id ? { task: await invoke('get', { task_id: input.task_id }) } : {}) }); } catch (error) { return failure(error); } });
  const entries = {
    image_status: ['本机推理状态', '读取服务是否就绪和全局队列数量，不读取其他页面的图片或提示词。', 'status', {}, true],
    image_import: ['导入图片', '登记用户指定的本机绝对路径、公开 HTTP(S) 图片直链或 base64 图片，返回 asset_ref。只接受一个来源。', 'import', { path: z.string().optional(), url: z.string().max(8192).optional(), base64: z.string().max(34952540).optional() }, false],
    image_generate: ['生成或编辑图片', '使用本机 Qwen。image_ref 为空为文生图，否则编辑已登记图片。task_id 必须为新 UUID；重复相同 UUID 不重新生成。', 'submit', { task_id: id, prompt: z.string().min(1).max(8000), image_ref: z.string().optional(), width: z.number().int().min(256).max(1536).default(768), height: z.number().int().min(256).max(1536).default(768), steps: z.number().int().min(1).max(12).default(4), seed: z.number().int().min(0).max(Number.MAX_SAFE_INTEGER).default(42) }, false],
    image_get_task: ['读取图片任务', '按原 task_id 查询同一 ComfyUI 任务与产物；不重复执行。', 'get', { task_id: id }, true],
    image_list_tasks: ['图片任务历史', '只列出本 MiniApp 登记的最近任务，不枚举其他 ComfyUI 页面的历史。', 'list', {}, true],
    image_cancel_task: ['取消选中任务', '只取消 task_id 对应的排队或运行任务，不全局中断其他页面。', 'cancel', { task_id: id }, false],
    image_control: ['管理本机推理服务', 'start 启动服务；release 卸载模型释放内存；stop 停止所有页面共用服务。release/stop 在有任何运行或排队任务时拒绝。', 'control', { action: z.enum(['start', 'release', 'stop']) }, false],
    image_read_asset: ['预览或下载图片', '读取已登记图片预览或 PNG 下载。图片字节仅返回界面元数据，Agent 使用产物绝对路径查看图片。', 'asset', { asset_ref: z.string(), download: z.boolean().optional() }, true],
  };
  for (const [name, [title, description, operation, inputSchema, readOnlyHint]] of Object.entries(entries)) {
    server.registerTool(name, { title, description, inputSchema, annotations: { readOnlyHint, destructiveHint: name === 'image_control', idempotentHint: name !== 'image_control', openWorldHint: name === 'image_import' }, _meta: { ui: { resourceUri: uri, visibility: name === 'image_read_asset' ? ['app'] : ['app', 'model'] } } }, async input => {
      try { return result(await invoke(operation, input)); } catch (error) { return failure(error); }
    });
  }
  return server;
}
function failure(error) { return { isError: true, content: [{ type: 'text', text: error.message }], structuredContent: { error: error.message } }; }
if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) await createServer().connect(new StdioServerTransport());
