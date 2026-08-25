import type { WebSocketServer, WebSocket } from "ws";
import nodeFs from "node:fs/promises";
import v8 from "node:v8";
import { adapt, approval } from "./codex/event-adapter.js";
import type { CodexClient } from "./codex/client.js";
import type { WorkspaceFs } from "./filesystem.js";

const send = (socket: WebSocket, data: any) => socket.readyState === socket.OPEN && socket.send(JSON.stringify(data));
const sourceKinds = ["cli", "vscode", "exec", "appServer", "subAgent", "subAgentReview", "subAgentCompact", "subAgentThreadSpawn", "subAgentOther", "unknown"];
const userMessage = (content: any[]) => ({
  text: content.filter((item: any) => item.type === "text").map((item: any) => item.text).join("\n"),
  attachments: content.filter((item: any) => ["image", "localImage", "audio", "localAudio"].includes(item.type)).map((item: any, index: number) => ({ name: item.path?.split("/").pop() || `${item.type.startsWith("audio") || item.type === "localAudio" ? "Audio" : "Image"} ${index + 1}`, kind: item.type.startsWith("audio") || item.type === "localAudio" ? "audio" : "image", data: item.url?.startsWith("data:") ? item.url : undefined })),
});
const compactionFor = (thread: any) => {
  const turn = [...(thread.turns || [])].reverse().find((entry: any) => (entry.items || []).some((item: any) => item.type === "contextCompaction"));
  return turn ? { status: "completed", at: turn.completedAt ? turn.completedAt * 1000 : undefined } : null;
};
async function processRss(pid?: number) {
  if (!pid || process.platform !== "linux") return null;
  try { const status = await nodeFs.readFile(`/proc/${pid}/status`, "utf8"); const value = status.match(/^VmRSS:\s+(\d+)\s+kB$/m); return value ? Number(value[1]) * 1024 : null; } catch { return null; }
}
async function allThreads(codex: CodexClient, archived: boolean) {
  const threads: any[] = []; let cursor: string | null | undefined; let pages = 0;
  do {
    const result = await codex.request("thread/list", { limit: 100, cursor: cursor || null, sortKey: "updated_at", sortDirection: "desc", archived, sourceKinds });
    threads.push(...(result.data || [])); cursor = result.nextCursor; pages++;
  } while (cursor && pages < 100);
  return threads;
}
const threadItems = (thread: any) => (thread.turns || []).flatMap((turn: any) => (turn.items || []).flatMap((item: any) => {
  if (item.type === "userMessage") return [{ type: "user_message", id: item.id, ...userMessage(item.content || []) }];
  const mapped = adapt({ method: "item/completed", params: { threadId: thread.id, item } }); return mapped?.items || [];
}));

export function wireSockets(wss: WebSocketServer, codex: CodexClient, fs: WorkspaceFs, meta: any) {
  const clients = new Set<WebSocket>();
  const broadcast = (data: any) => clients.forEach((socket) => send(socket, data));
  codex.on("status", (status) => broadcast({ type: "status", ...meta(), codexStatus: status }));
  codex.on("message", (message) => {
    const request = approval(message);
    if (request) return broadcast({ type: "items", threadId: message.params?.threadId, items: [request] });
    const event = adapt(message); if (event) broadcast({ type: "event", ...event });
  });

  wss.on("connection", (socket) => {
    clients.add(socket); send(socket, { type: "status", ...meta(), codexStatus: codex.status });
    socket.on("close", () => clients.delete(socket));
    socket.on("message", async (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        if (msg.type === "thread.list") {
          send(socket, { type: "threads", archived: Boolean(msg.archived), threads: await allThreads(codex, Boolean(msg.archived)) });
        } else if (msg.type === "model.list") {
          const result = await codex.request("model/list", { limit: 50, includeHidden: false });
          send(socket, { type: "models", models: result.data || [] });
        } else if (msg.type === "thread.create") {
          if (!fs.isSelected) throw new Error("Choose a workspace before starting a thread");
          const result = await codex.request("thread/start", { cwd: fs.path, model: msg.model || null, approvalPolicy: "on-request", experimentalRawEvents: false });
          send(socket, { type: "thread.active", thread: result.thread, items: [], model: result.model, effort: result.reasoningEffort }); broadcast({ type: "thread.changed", thread: result.thread });
        } else if (msg.type === "thread.resume") {
          const result = await codex.request("thread/resume", { threadId: msg.threadId });
          if (result.thread?.cwd) {
            try { await fs.selectAbsolute(result.thread.cwd); broadcast({ type: "status", ...meta(), codexStatus: codex.status }); } catch { /* The session can still be viewed outside the file-browser root. */ }
          }
          send(socket, { type: "thread.active", thread: result.thread, items: threadItems(result.thread), compaction: compactionFor(result.thread), model: result.model, effort: result.reasoningEffort });
        } else if (msg.type === "thread.archive") {
          await codex.request("thread/archive", { threadId: msg.threadId });
          broadcast({ type: "thread.mutated", action: "archive", threadId: msg.threadId });
        } else if (msg.type === "thread.unarchive") {
          const result = await codex.request("thread/unarchive", { threadId: msg.threadId });
          broadcast({ type: "thread.mutated", action: "unarchive", threadId: msg.threadId, thread: result.thread });
        } else if (msg.type === "thread.delete") {
          await codex.request("thread/delete", { threadId: msg.threadId });
          broadcast({ type: "thread.mutated", action: "delete", threadId: msg.threadId });
        } else if (msg.type === "turn.send") {
          const text = String(msg.text || "").trim(); const attachments = Array.isArray(msg.attachments) ? msg.attachments.slice(0, 4) : []; if (!text && !attachments.length) return;
          const input: any[] = text ? [{ type: "text", text, text_elements: [] }] : [];
          for (const attachment of attachments) {
            if (attachment.kind === "image" && typeof attachment.data === "string" && attachment.data.startsWith("data:image/") && attachment.data.length <= 14 * 1024 * 1024) input.push({ type: "image", url: attachment.data });
            else if (attachment.kind === "text" && typeof attachment.data === "string" && Buffer.byteLength(attachment.data, "utf8") <= 1024 * 1024) input.push({ type: "text", text: `Attached file \"${String(attachment.name || "attachment").slice(0, 200)}\":\n\n${attachment.data}`, text_elements: [] });
          }
          const result = await codex.request("turn/start", { threadId: msg.threadId, input, model: msg.model || null, effort: msg.effort || null, summary: "auto" });
          send(socket, { type: "turn.accepted", turnId: result.turn.id });
        } else if (msg.type === "turn.interrupt") await codex.request("turn/interrupt", { threadId: msg.threadId, turnId: msg.turnId });
        else if (msg.type === "approval.respond") codex.respond(msg.requestId, { decision: msg.decision });
        else if (msg.type === "fs.list") send(socket, { type: "fs.entries", path: msg.path || "", entries: await fs.list(msg.path || "") });
        else if (msg.type === "fs.read") send(socket, { type: "fs.file", file: await fs.read(msg.path) });
        else if (msg.type === "fs.write") send(socket, { type: "fs.saved", file: await fs.write(msg.path, String(msg.content ?? "")) });
        else if (msg.type === "workspace.list") send(socket, { type: "workspace.entries", path: msg.path || "", entries: await fs.listWorkspaces(msg.path || ""), base: fs.basePath, current: fs.path });
        else if (msg.type === "system.usage") {
          const memory = process.memoryUsage(); const codexRss = await processRss(codex.pid);
          send(socket, { type: "system.usage", usage: { rss: memory.rss, heapUsed: memory.heapUsed, heapTotal: memory.heapTotal, heapLimit: v8.getHeapStatistics().heap_size_limit, external: memory.external, codexRss, totalRss: memory.rss + (codexRss || 0), uptime: process.uptime(), clients: clients.size } });
        } else if (msg.type === "account.usage") {
          const [usage, limits] = await Promise.allSettled([codex.request("account/usage/read"), codex.request("account/rateLimits/read")]);
          send(socket, { type: "account.usage", usage: usage.status === "fulfilled" ? usage.value : null, rateLimits: limits.status === "fulfilled" ? limits.value : null, unavailable: usage.status === "rejected" && limits.status === "rejected" });
        }
        else if (msg.type === "workspace.select") {
          const selected = await fs.select(msg.path || "");
          send(socket, { type: "workspace.selected", ...selected, ...meta() });
          broadcast({ type: "status", ...meta(), codexStatus: codex.status });
        }
      } catch (error) { send(socket, { type: "error", message: error instanceof Error ? error.message : String(error) }); }
    });
  });
}
