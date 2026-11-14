import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const ENTRY = "/?template=QwenPhoto&source=qwen_rapid&mode=linear";
let message;
let importing = false;
function tell(text, error = false) {
  message.textContent = text;
  message.style.color = error ? "#ef9e92" : "var(--fg-color, #eee)";
}
async function post(path, body = {}) {
  const response = await api.fetchApi(`/qwen-workbench/${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error((await response.json()).error || "操作失败，请重试。");
  return response;
}
async function importImage(url) {
  const node = app.rootGraph.nodes.find((node) => node.type === "LoadImage" && node.title === "原始照片");
  if (!node) throw new Error("请先打开「照片编辑」应用，再导入图片。");
  if (importing) return;
  importing = true;
  try {
    tell("正在导入网络图片……");
    const response = await post("import-image", { url });
    const file = new File([await response.blob()], `network-${crypto.randomUUID()}.png`, { type: "image/png" });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    // Native ComfyUI owns upload, validation, preview and widget updates.
    const handled = await node.onDragDrop(new DragEvent("drop", { dataTransfer: transfer }));
    if (!handled) throw new Error("图片未被接收，请重试或使用本机上传。");
    tell("图片已导入，可以填写编辑要求并点击运行。");
  } finally { importing = false; }
}
function imageUrl(transfer) {
  const html = transfer.getData("text/html");
  if (html) {
    const src = new DOMParser().parseFromString(html, "text/html").querySelector("img")?.getAttribute("src");
    if (/^https?:\/\//i.test(src || "")) return src;
  }
  return (transfer.getData("text/uri-list") || transfer.getData("text/plain"))
    .split(/\r?\n/).find((line) => /^https?:\/\//i.test(line.trim()))?.trim();
}
app.registerExtension({
  name: "QwenPhoto.NativeWorkbench",
  async setup() {
    const toolbar = document.createElement("section");
    toolbar.id = "qwen-workbench-tools";
    toolbar.setAttribute("aria-label", "照片编辑工具");
    const style = document.createElement("style");
    style.textContent = `
      #qwen-workbench-tools {position:fixed;left:80px;bottom:18px;z-index:150;display:flex;flex-direction:column;gap:7px;max-width:min(600px,calc(100vw - 440px));padding:10px 12px;border:1px solid var(--border-color,#555);border-radius:10px;background:var(--comfy-menu-bg,#252525);box-shadow:0 3px 16px #0003;font:13px system-ui;}
      #qwen-workbench-tools .buttons {display:flex;gap:7px;flex-wrap:wrap;}
      #qwen-workbench-tools button {padding:7px 10px;border:1px solid var(--border-color,#666);border-radius:6px;background:var(--comfy-input-bg,#383838);color:var(--fg-color,#eee);cursor:pointer;}
      #qwen-workbench-tools button:hover {filter:brightness(1.2);}
      #qwen-workbench-tools [role=status] {max-width:550px;line-height:1.45;}
    `;
    document.head.append(style);
    const buttons = document.createElement("div");
    buttons.className = "buttons";
    message = document.createElement("div");
    message.setAttribute("role", "status");
    const button = (label, action) => {
      const b = document.createElement("button"); b.textContent = label;
      b.onclick = () => Promise.resolve().then(action).catch((e) => tell(e.message, true));
      buttons.append(b);
    };
    button("照片编辑", () => { location.href = ENTRY; });
    button("文生图", () => { location.href = "/?template=QwenTextToImage&source=qwen_rapid&mode=linear"; });
    button("导入图片链接", async () => {
      const url = await app.extensionManager.dialog.prompt({title: "导入网络图片", message: "粘贴图片的直接链接，也可以把网页上的图片直接拖进页面。", placeholder: "https://…/image.jpg"});
      if (url?.trim()) await importImage(url.trim());
    });
    button("释放模型内存", async () => tell((await (await post("release")).json()).message));
    button("停止服务", async () => tell((await (await post("stop")).json()).message));
    toolbar.append(buttons, message); document.body.append(toolbar);
    tell("支持拖入网页图片；不用时可释放模型内存，或停止服务。");
    document.addEventListener("dragover", (event) => {
      const t = event.dataTransfer;
      if (t && ![...t.items].some((item) => item.kind === "file") && (t.types.includes("text/uri-list") || t.types.includes("text/html"))) {
        event.preventDefault(); t.dropEffect = "copy";
      }
    }, true);
    document.addEventListener("drop", (event) => {
      const t = event.dataTransfer;
      if (!t || t.files.length) return;
      const url = imageUrl(t);
      if (!url) return;
      event.preventDefault(); event.stopImmediatePropagation();
      importImage(url).catch((e) => tell(e.message, true));
    }, true);
  },
});
