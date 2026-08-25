import { ShieldCheck, Terminal } from "lucide-react";
import type { UiItem } from "../types";

export function ApprovalCard({ item, respond }: { item: Extract<UiItem, { type: "approval" }>; respond: (decision: string) => void }) {
  const label: Record<string, string> = { accept: "Allow once", acceptForSession: "Allow this session", decline: "Deny", cancel: "Cancel" };
  return <section className={`approval-card ${item.status}`}>
    <span className="approval-icon"><ShieldCheck /></span><div className="approval-content"><header><div><b>Approval required</b><span>Codex wants to {item.approvalKind === "command" ? "run a command" : "modify files"}</span></div></header>
    <code>{item.approvalKind === "command" && <Terminal />}{item.description}</code>
    {item.status === "pending" ? <div className="approval-actions">{item.decisions.map((decision) => <button key={decision} className={decision === "accept" ? "primary" : decision === "decline" ? "danger" : ""} onClick={() => respond(decision)}>{label[decision] || decision}</button>)}</div> : <small>{item.status === "approved" ? "Approved" : "Denied"}</small>}</div>
  </section>;
}
