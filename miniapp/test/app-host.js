import { AppBridge, PostMessageTransport } from '@modelcontextprotocol/ext-apps/app-bridge';
const frame = document.querySelector('iframe');
const focus = Object.fromEntries(new URLSearchParams(location.search));
const bridge = new AppBridge(null, { name: 'OPL image SDK qualification host', version: '1.0.0' }, { serverTools: {}, updateModelContext: {}, openLinks: {} });
bridge.oncalltool = async request => {
  const response = await fetch('/tool', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) });
  return response.json();
};
bridge.onupdatemodelcontext = async value => { window.imageContext = value; return {}; };
bridge.onopenlink = async () => ({ isError: false });
bridge.oninitialized = async () => {
  await bridge.sendToolInput({ arguments: focus });
  await bridge.sendToolResult(await bridge.oncalltool({ name: 'open_image_workbench', arguments: focus }));
  document.body.dataset.initialized = 'true';
};
await bridge.connect(new PostMessageTransport(frame.contentWindow, frame.contentWindow));
frame.src = '/view';
