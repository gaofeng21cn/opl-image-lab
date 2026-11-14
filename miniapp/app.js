import { App, applyDocumentTheme, applyHostStyleVariables } from '@modelcontextprotocol/ext-apps';

const $ = id => document.getElementById(id);
const app = new App({ name: 'OPL Image Lab', version: '0.1.0' }, { availableDisplayModes: ['inline', 'fullscreen'] });
const labels = { submitting: '正在提交', queued: '排队中', running: '正在生成', completed: '生成完成', failed: '生成失败', cancelled: '已取消', cancel_requested: '正在取消', unknown: '结果待核对' };
const active = new Set(['submitting', 'queued', 'running', 'cancel_requested', 'unknown']);
const state = { ready: false, input: null, task: null, view: 'result', busy: false, selection: 0, original: null, output: null, advancedUrl: null };
let polling = false;

function theme(context = {}) {
  applyDocumentTheme(context.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  document.body.toggleAttribute('data-ds-dark-theme', document.documentElement.dataset.theme === 'dark');
  if (context.styles?.variables) applyHostStyleVariables(context.styles.variables);
}
app.onhostcontextchanged = theme;
function notice(message) { $('notice').textContent = message; $('notice').hidden = false; }
async function call(name, args = {}) {
  const response = await app.callServerTool({ name, arguments: args });
  if (response.isError) throw Error(response.structuredContent?.error || response.content?.find(c => c.type === 'text')?.text || '操作未完成。');
  return { ...response.structuredContent, ...response._meta };
}
async function run(fn) {
  if (state.busy) return;
  state.busy = true; $('notice').hidden = true; render();
  try { await fn(); } catch (error) { notice(error.message); }
  finally { state.busy = false; render(); }
}
function bind(id, fn) { $(id).onclick = event => { event.preventDefault(); run(fn); }; }
function render() {
  $('generate').disabled = state.busy || !state.ready;
  $('generate').textContent = state.input ? '按描述编辑图片' : '生成图片';
  $('prompt-label').textContent = state.input ? '想怎样修改这张图？' : '想生成什么画面？';
  $('prompt').placeholder = state.input ? '例如：把背景换成海边，保留主体。' : '例如：白色背景上的黄色陶瓷杯，柔和自然光。';
  $('cancel').disabled = state.busy || !state.task || !active.has(state.task.status) || !state.ready;
  $('reuse').disabled = state.busy || !state.output;
  $('download').disabled = state.busy || !state.output;
  $('clear-input').disabled = state.busy || !state.input;
  $('start').disabled = state.busy || state.ready;
  $('start').hidden = state.ready;
  $('release').disabled = state.busy || !state.ready;
  $('stop').disabled = state.busy || !state.ready;
  $('input-label').textContent = state.input ? `${state.input.width} × ${state.input.height} · 待编辑图片` : '点击、拖入或粘贴图片';
  $('input-thumbnail').hidden = !state.input?.data_uri;
  if (state.input?.data_uri) $('input-thumbnail').src = state.input.data_uri;
  const originalVisible = Boolean(state.original && (state.view !== 'result' || !state.output));
  $('original-figure').hidden = !originalVisible;
  $('result-figure').hidden = !state.output || state.view === 'original';
  if (state.original) $('original').src = state.original.data_uri;
  if (state.output) $('result').src = state.output.data_uri;
  $('empty-preview').hidden = Boolean(state.original || state.output);
  for (const view of ['result', 'original', 'compare']) $('show-' + view).setAttribute('aria-pressed', String(view === state.view));
  $('show-original').disabled = !state.original;
  $('show-compare').disabled = !state.original || !state.output;
  const task = state.task;
  $('task-status').textContent = task ? `${labels[task.status] || task.status}${task.backend_offline ? ' · 后台离线，记录已保留' : ''}${task.message ? ' · ' + task.message : ''}${task.output ? ` · ${task.output.width} × ${task.output.height}` : ''}` : '图片与指令在本机处理。';
}
async function context() {
  try { await app.updateModelContext({ structuredContent: { navigation: { task_id: state.task?.task_id, image_ref: state.input?.asset_ref }, selection: { task_id: state.task?.task_id, status: state.task?.status, input_ref: state.input?.asset_ref, output_ref: state.task?.output?.asset_ref } } }); } catch { /* Reopening still reads the domain owner. */ }
}
async function status() {
  const data = await call('image_status');
  state.ready = data.service.ready;
  state.advancedUrl = data.advanced_url;
  $('model-info').textContent = `${data.model} · 本机推理`;
  $('service').textContent = state.ready ? (data.service.running || data.service.pending ? `运行 ${data.service.running} · 排队 ${data.service.pending}` : '本机服务已就绪') : '本机服务未启动';
  render();
}
async function image(reference) { return call('image_read_asset', { asset_ref: reference }); }
async function setInput(asset) {
  const epoch = ++state.selection;
  const preview = asset.data_uri ? asset : await image(asset.asset_ref);
  if (epoch !== state.selection) return;
  state.input = preview; state.original = preview; state.output = null; state.task = null; state.view = 'original';
  const ratio = preview.width / preview.height;
  $('width').value = ratio >= 1 ? 768 : Math.max(256, Math.round(768 * ratio / 16) * 16);
  $('height').value = ratio >= 1 ? Math.max(256, Math.round(768 / ratio / 16) * 16) : 768;
  render(); await context();
}
async function importFile(file) {
  if (!file || file.size > 25 * 1024 * 1024) throw Error('请选择不超过 25 MB 的图片。');
  const encoded = await new Promise((accept, reject) => { const reader = new FileReader(); reader.onerror = () => reject(Error('图片读取失败。')); reader.onload = () => accept(reader.result.split(',')[1]); reader.readAsDataURL(file); });
  await setInput(await call('image_import', { base64: encoded }));
}
async function importUrl(url) {
  if (!/^https?:\/\//i.test(url)) throw Error('请输入公开图片的 HTTP 或 HTTPS 直链。');
  await setInput(await call('image_import', { url }));
  $('url-row').hidden = true;
}
async function selectTask(task) {
  const epoch = ++state.selection;
  const data = await call('image_get_task', { task_id: task.task_id });
  if (epoch !== state.selection) return;
  state.task = data; state.input = null; state.original = null; state.output = null; state.view = 'result';
  for (const key of ['prompt', 'width', 'height', 'steps', 'seed']) $(key).value = data.request[key];
  const [original, output] = await Promise.all([data.request.image_ref ? image(data.request.image_ref) : null, data.output ? image(data.output.asset_ref) : null]);
  if (epoch !== state.selection) return;
  state.input = original; state.original = original; state.output = output;
  render(); await context();
}
async function history() {
  const data = await call('image_list_tasks');
  $('history-list').replaceChildren();
  for (const task of data.tasks) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'history-item';
    const title = document.createElement('span'); title.textContent = task.request.prompt;
    const description = document.createElement('span'); description.textContent = labels[task.status] || task.status;
    button.append(title, description); button.setAttribute('aria-current', String(task.task_id === state.task?.task_id));
    button.onclick = () => run(() => selectTask(task)); $('history-list').append(button);
  }
  if (!data.tasks.length) $('history-list').textContent = '还没有生成任务。';
}

bind('start', async () => { await call('image_control', { action: 'start' }); $('service').textContent = '推理服务正在启动…'; });
bind('release', async () => { const result = await call('image_control', { action: 'release' }); notice(result.message || '模型未加载。'); await status(); });
bind('stop', async () => {
  if ($('stop').dataset.confirm !== 'true') { $('stop').dataset.confirm = 'true'; $('stop').textContent = '确认停止所有页面'; return; }
  await call('image_control', { action: 'stop' }); delete $('stop').dataset.confirm; $('stop').textContent = '停止推理服务'; state.ready = false; $('service').textContent = '推理服务正在停止…';
});
bind('advanced', () => state.advancedUrl && app.openLink({ url: state.advancedUrl }));
bind('cancel', async () => { const ident = state.task.task_id; const task = await call('image_cancel_task', { task_id: ident }); if (state.task?.task_id === ident) state.task = task; await context(); });
bind('reuse', async () => { await setInput(state.output); $('prompt').value = ''; $('prompt').focus(); });
bind('download', async () => {
  const data = await call('image_read_asset', { asset_ref: state.output.asset_ref, download: true });
  const bytes = Uint8Array.from(atob(data.data_uri.split(',')[1]), c => c.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: 'image/png' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'qwen-' + state.task.task_id + '.png'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
bind('history-toggle', async () => { $('history').hidden = !$('history').hidden; if (!$('history').hidden) await history(); });
bind('refresh-history', history);
bind('url-toggle', () => { $('url-row').hidden = !$('url-row').hidden; if (!$('url-row').hidden) $('image-url').focus(); });
bind('import-url', () => importUrl($('image-url').value.trim()));
bind('clear-input', async () => { ++state.selection; state.input = null; state.task = null; state.original = null; state.output = null; state.view = 'result'; await context(); });
for (const view of ['result', 'original', 'compare']) bind('show-' + view, () => { state.view = view; });
$('pick-preview').onclick = () => $('file').click();
$('file').onchange = event => { run(() => importFile(event.target.files[0])); event.target.value = ''; };
$('dropzone').onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); $('file').click(); } };
$('dropzone').ondragover = event => { event.preventDefault(); $('dropzone').classList.add('dragging'); };
$('dropzone').ondragleave = () => $('dropzone').classList.remove('dragging');
$('dropzone').ondrop = event => {
  event.preventDefault(); $('dropzone').classList.remove('dragging');
  const transfer = event.dataTransfer;
  const file = [...transfer.files].find(f => f.type.startsWith('image/'));
  const html = transfer.getData('text/html');
  const source = html ? new DOMParser().parseFromString(html, 'text/html').querySelector('img')?.src : null;
  const url = source || transfer.getData('text/uri-list').split('\n').find(line => /^https?:\/\//i.test(line.trim())) || transfer.getData('text/plain').trim();
  run(() => file ? importFile(file) : importUrl(url));
};
document.addEventListener('paste', event => {
  const file = [...(event.clipboardData?.items || [])].find(item => item.type.startsWith('image/'))?.getAsFile();
  if (file) { event.preventDefault(); run(() => importFile(file)); }
});
$('generate-form').onsubmit = event => event.preventDefault();
$('generate').onclick = event => {
  event.preventDefault();
  if (!$('generate-form').reportValidity()) return;
  run(async () => {
    const ident = crypto.randomUUID();
    const request = { task_id: ident, prompt: $('prompt').value, ...(state.input ? { image_ref: state.input.asset_ref } : {}) };
    for (const key of ['width', 'height', 'steps', 'seed']) request[key] = Number($(key).value);
    const epoch = ++state.selection;
    state.task = { task_id: ident, status: 'submitting' }; state.original = state.input; state.output = null; state.view = 'result'; render();
    try { const task = await call('image_generate', request); if (epoch === state.selection) state.task = task; }
    catch (error) { if (epoch === state.selection) state.task = { task_id: ident, status: 'unknown', message: error.message }; throw error; }
    await context(); if (!$('history').hidden) await history();
  });
};
app.ontoolresult = result => {
  const focus = result.structuredContent?.focus;
  if (focus?.task_id) run(() => selectTask({ task_id: focus.task_id }));
  else if (focus?.image_ref) run(async () => setInput(await image(focus.image_ref)));
};
await app.connect(); theme(app.getHostContext()); await status();
setInterval(async () => {
  if (polling || state.busy) return;
  polling = true;
  try {
    await status();
    if (state.task && active.has(state.task.status)) {
      const ident = state.task.task_id, epoch = state.selection;
      const task = await call('image_get_task', { task_id: ident });
      if (epoch === state.selection && state.task?.task_id === ident) {
        const changed = state.task.status !== task.status; state.task = task;
        if (task.output && !state.output) { const output = await image(task.output.asset_ref); if (epoch === state.selection) state.output = output; }
        if (changed) { await context(); if (!$('history').hidden) await history(); }
      }
    }
    render();
  } catch (error) { $('service').textContent = '连接中断，任务记录仍保留'; }
  finally { polling = false; }
}, 2500);
