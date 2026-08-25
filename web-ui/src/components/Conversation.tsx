import { Activity, FileImage, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { UiItem } from "../types";
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

export function Conversation({ items, running, respond }: { items: UiItem[]; running: boolean; respond: (item: Extract<UiItem, { type: "approval" }>, decision: string) => void }) {
  const scroll = useRef<HTMLDivElement>(null); const [following, setFollowing] = useState(true);
  const segments = useMemo(() => groupItems(items), [items]);
  useEffect(() => { if (following) scroll.current?.scrollTo({ top: scroll.current.scrollHeight, behavior: "smooth" }); }, [items, following]);
  return <div className="conversation" ref={scroll} onScroll={() => { const element = scroll.current; if (element) setFollowing(element.scrollHeight - element.scrollTop - element.clientHeight < 100); }}>
    <div className="conversation-inner">{items.length === 0 && <div className="empty-chat"><span className="empty-logo"><CodexLogo /></span><h1>What are we coding next?</h1><p>Describe a task, ask a question, or explore this workspace with Codex.</p></div>}
    {segments.map((segment) => segment.type === "activity" ? <ActivityGroup items={segment.items} key={segment.id} /> : segment.item.type === "user_message" ? <article className="message user" key={segment.item.id}><div className="user-bubble">{segment.item.attachments?.length ? <div className="user-attachments">{segment.item.attachments.map((attachment, index) => attachment.kind === "image" && attachment.data ? <img className="user-attachment-image" src={attachment.data} alt={attachment.name} key={`${attachment.name}-${index}`} /> : <div className="user-attachment-file" key={`${attachment.name}-${index}`}><FileImage /><span>{attachment.name}</span></div>)}</div> : null}{segment.item.text && <p>{segment.item.text}</p>}</div></article>
      : segment.item.type === "assistant_message" ? <article className={`message assistant ${segment.item.streaming ? "is-streaming" : ""}`} key={segment.item.id}><div className="avatar codex-avatar"><CodexLogo /></div><div className="assistant-body"><ReactMarkdown>{cleanCitations(segment.item.text)}</ReactMarkdown>{segment.item.streaming && <span className="stream-cursor" />}</div></article>
      : segment.item.type === "approval" ? <ApprovalCard key={segment.item.id} item={segment.item} respond={(decision) => respond(segment.item as Extract<UiItem, { type: "approval" }>, decision)} />
      : segment.item.type === "error" ? <div className="error-card" key={segment.item.id}>{segment.item.message}</div> : null)}
    {running && !items.some((item) => (item.type === "thinking" && item.status === "running") || (item.type === "assistant_message" && item.streaming)) && <div className="thinking-live"><LoaderCircle /><div><b>Starting</b><span>Codex is preparing the turn</span></div></div>}
    </div>
  </div>;
}
