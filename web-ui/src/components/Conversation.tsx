import { Activity, FileImage, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ApprovalDecision, UiItem } from "../types";
import { ApprovalCard } from "./ApprovalCard";
import { CodexLogo } from "./CodexLogo";
import { ToolCard } from "./ToolCard";

type ToolItem = Exclude<UiItem, { type: "user_message" | "assistant_message" | "approval" | "error" }>;
type Segment = { type: "item"; item: UiItem } | { type: "activity"; id: string; items: ToolItem[] };

function groupItems(items: UiItem[]): Segment[] {
  const result: Segment[] = [];
  for (const item of items) {
    const isTool = !["user_message", "assistant_message", "approval", "error"].includes(item.type);
    const last = result.at(-1);
    if (isTool && last?.type === "activity") last.items.push(item as ToolItem);
    else if (isTool) result.push({ type: "activity", id: `activity-${item.id}`, items: [item as ToolItem] });
    else result.push({ type: "item", item });
  }
  return result;
}

function ActivityGroup({ items }: { items: ToolItem[] }) {
  const active = items.some((item) => (item.type === "thinking" || item.type === "command") && item.status === "running");
  return <section className={`activity-group ${active ? "running" : ""}`}>
    <header><span className="activity-icon">{active ? <LoaderCircle /> : <Activity />}</span><div><b>{active ? "Working" : "Activity"}</b><small>{active ? "Codex is reasoning and using tools" : `${items.length} ${items.length === 1 ? "step" : "steps"}`}</small></div></header>
    <div className="activity-list">{items.map((item) => <ToolCard item={item} key={item.id} />)}</div>
  </section>;
}

const cleanCitations = (text: string) => text.replace(/cite[^]+/g, "");
const normalizeFilePath = (value: string) => { try { return decodeURIComponent(value).replace(/^file:\/\//, "").replaceAll("\\", "/").split(/[?#]/, 1)[0].replace(/:\d+(?::\d+)?$/, ""); } catch { return value.replaceAll("\\", "/").split(/[?#]/, 1)[0].replace(/:\d+(?::\d+)?$/, ""); } };
function workspaceFile(href: string, workspace: string) {
  if (!href || href.startsWith("#") || /^(https?|mailto|tel):/i.test(href)) return null;
  let candidate = normalizeFilePath(href); const root = workspace.replaceAll("\\", "/").replace(/\/$/, "");
  const absolute = candidate.startsWith("/") || /^[a-z]:\//i.test(candidate);
  if (absolute) {
    const compareCandidate = /^[a-z]:/i.test(candidate) ? candidate.toLowerCase() : candidate; const compareRoot = /^[a-z]:/i.test(root) ? root.toLowerCase() : root;
    if (!compareRoot || !compareCandidate.startsWith(`${compareRoot}/`)) return { unavailable: true as const, path: "" };
    candidate = candidate.slice(root.length + 1);
  } else {
    candidate = candidate.replace(/^\.\//, ""); const rootName = root.split("/").pop();
    if (rootName && candidate.startsWith(`${rootName}/`)) candidate = candidate.slice(rootName.length + 1);
  }
  const parts = candidate.split("/").filter((part) => part && part !== ".");
  if (!parts.length || parts.some((part) => part === "..")) return { unavailable: true as const, path: "" };
  return { unavailable: false as const, path: parts.join("/") };
}

export function Conversation({ items, running, workspace, basePath, openFile, respond }: { items: UiItem[]; running: boolean; workspace: string; basePath: string; openFile: (path: string) => void; respond: (item: Extract<UiItem, { type: "approval" }>, decision: ApprovalDecision) => void }) {
  const scroll = useRef<HTMLDivElement>(null); const [following, setFollowing] = useState(true);
  const segments = useMemo(() => groupItems(items), [items]);
  useEffect(() => { if (following) scroll.current?.scrollTo({ top: scroll.current.scrollHeight, behavior: "smooth" }); }, [items, following]);
  return <div className="conversation" ref={scroll} onScroll={() => { const element = scroll.current; if (element) setFollowing(element.scrollHeight - element.scrollTop - element.clientHeight < 100); }}>
    <div className="conversation-inner">{items.length === 0 && <div className="empty-chat"><span className="empty-logo"><CodexLogo /></span><h1>What are we coding next?</h1><p>Describe a task, ask a question, or explore this workspace with Codex.</p></div>}
    {segments.map((segment) => segment.type === "activity" ? <ActivityGroup items={segment.items} key={segment.id} /> : segment.item.type === "user_message" ? <article className="message user" key={segment.item.id}><div className="user-bubble">{segment.item.attachments?.length ? <div className="user-attachments">{segment.item.attachments.map((attachment, index) => attachment.kind === "image" && attachment.data ? <img className="user-attachment-image" src={attachment.data} alt={attachment.name} key={`${attachment.name}-${index}`} /> : <div className="user-attachment-file" key={`${attachment.name}-${index}`}><FileImage /><span>{attachment.name}</span></div>)}</div> : null}{segment.item.text && <p>{segment.item.text}</p>}</div></article>
      : segment.item.type === "assistant_message" ? <article className={`message assistant ${segment.item.streaming ? "is-streaming" : ""}`} key={segment.item.id}><div className="avatar codex-avatar"><CodexLogo /></div><div className="assistant-body"><ReactMarkdown components={{ a: ({ href = "", children, ...props }) => { const local = workspaceFile(href, workspace); if (!local) return <a href={href} {...props}>{children}</a>; if (local.unavailable) return <span className="unavailable-file-link" title="This file is outside the selected workspace">{children}</span>; const prefix = basePath === "/" ? "" : basePath; return <a className="workspace-file-link" href={`${prefix}/?file=${encodeURIComponent(local.path)}`} onClick={(event) => { event.preventDefault(); openFile(local.path); }}>{children}</a>; } }}>{cleanCitations(segment.item.text)}</ReactMarkdown>{segment.item.streaming && <span className="stream-cursor" />}</div></article>
      : segment.item.type === "approval" ? <ApprovalCard key={segment.item.id} item={segment.item} respond={(decision) => respond(segment.item as Extract<UiItem, { type: "approval" }>, decision)} />
      : segment.item.type === "error" ? <div className="error-card" key={segment.item.id}>{segment.item.message}</div> : null)}
    {running && !items.some((item) => (item.type === "thinking" && item.status === "running") || (item.type === "assistant_message" && item.streaming)) && <div className="thinking-live"><LoaderCircle /><div><b>Starting</b><span>Codex is preparing the turn</span></div></div>}
    </div>
  </div>;
}
