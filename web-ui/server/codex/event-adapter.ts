import type { JsonRpcMessage, UiItem } from "./protocol.js";

const diffFor = (changes: any[]) => changes?.map((c) => c.diff || c.patch || c.content || "").filter(Boolean).join("\n") || "";
const pathFor = (change: any) => change?.path || change?.file_path || change?.move_path || "Changed files";

export function adapt(message: JsonRpcMessage): { threadId?: string; items?: UiItem[]; running?: boolean; turnId?: string; diff?: string; tokenUsage?: any; compaction?: { status: "running" | "completed"; at?: number } } | null {
  const p = message.params || {}; const item = p.item || {};
  if (message.method === "turn/diff/updated") return { threadId: p.threadId, turnId: p.turnId, diff: p.diff || "" };
  if (message.method === "thread/tokenUsage/updated") return { threadId: p.threadId, turnId: p.turnId, tokenUsage: p.tokenUsage };
  if (message.method === "thread/compacted") return { threadId: p.threadId, turnId: p.turnId, compaction: { status: "completed", at: Date.now() } };
  if (message.method === "item/agentMessage/delta") return { threadId: p.threadId, items: [{ type: "assistant_message", id: p.itemId, text: p.delta || "", streaming: true }] };
  if (message.method === "item/reasoning/summaryTextDelta" || message.method === "item/reasoning/textDelta") return { threadId: p.threadId, items: [{ type: "thinking", id: p.itemId, text: p.delta || "", status: "running" }] };
  if (message.method === "item/commandExecution/outputDelta") return { threadId: p.threadId, items: [{ type: "command", id: p.itemId, command: "", output: p.delta || "", status: "running" }] };
  if (message.method === "item/fileChange/patchUpdated") return { threadId: p.threadId, items: (p.changes || []).map((c: any, i: number) => ({ type: "file_change", id: `${p.itemId}-${i}`, path: pathFor(c), diff: diffFor([c]), status: "running" })) };
  if (message.method === "turn/started") return { threadId: p.threadId, running: true, turnId: p.turn?.id };
  if (message.method === "turn/completed") return { threadId: p.threadId, running: false, turnId: p.turn?.id };
  if (message.method === "error") return { threadId: p.threadId, running: false, items: [{ type: "error", id: `error-${Date.now()}`, message: p.error?.message || p.message || "Codex error" }] };
  if (message.method === "item/started" || message.method === "item/completed") {
    const done = message.method === "item/completed";
    if (item.type === "contextCompaction") return { threadId: p.threadId, turnId: p.turnId, compaction: { status: done ? "completed" : "running", at: done ? Date.now() : undefined } };
    if (item.type === "agentMessage") return { threadId: p.threadId, items: [{ type: "assistant_message", id: item.id, text: item.text || "", streaming: !done }] };
    if (item.type === "reasoning") return { threadId: p.threadId, items: [{ type: "thinking", id: item.id, text: [...(item.summary || []), ...(item.content || [])].join("\n"), status: done ? "done" : "running" }] };
    if (item.type === "commandExecution") return { threadId: p.threadId, items: [{ type: "command", id: item.id, command: item.command || "Command", output: item.aggregatedOutput || "", status: done ? (item.status === "failed" ? "error" : "done") : "running" }] };
    if (item.type === "fileChange") return { threadId: p.threadId, items: (item.changes || []).map((c: any, i: number) => ({ type: "file_change", id: `${item.id}-${i}`, path: pathFor(c), diff: diffFor([c]), status: item.status })) };
    if (item.type === "mcpToolCall" || item.type === "dynamicToolCall") return { threadId: p.threadId, items: [{ type: "command", id: item.id, command: `${item.server || item.namespace || "tool"} · ${item.tool}`, output: item.result ? JSON.stringify(item.result, null, 2) : "", status: done ? (item.error ? "error" : "done") : "running" }] };
  }
  return null;
}

export function approval(message: JsonRpcMessage): UiItem | null {
  const p = message.params || {};
  if (message.id === undefined) return null;
  if (message.method === "item/commandExecution/requestApproval") return { type: "approval", id: `approval-${message.id}`, requestId: message.id, description: p.command || p.reason || "Run command", status: "pending", decisions: p.availableDecisions || ["accept", "acceptForSession", "decline"], approvalKind: "command" };
  if (message.method === "item/fileChange/requestApproval") return { type: "approval", id: `approval-${message.id}`, requestId: message.id, description: p.reason || `Modify files${p.grantRoot ? ` under ${p.grantRoot}` : ""}`, status: "pending", decisions: ["accept", "acceptForSession", "decline"], approvalKind: "file" };
  return null;
}
