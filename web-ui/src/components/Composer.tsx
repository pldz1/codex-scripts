import { useEffect, useRef, useState } from "react";
import { ArrowUp, FileText, Paperclip, Square, X } from "lucide-react";
import type { ModelOption } from "../types";
import type { CompactionStatus, ThreadUsage } from "./SettingsDrawer";
import { ModelPicker } from "./ModelPicker";

export type ComposerAttachment = { id: string; name: string; mime: string; kind: "image" | "text"; data: string; size: number };
const textTypes = new Set(["text/plain", "text/markdown", "application/json", "application/xml", "application/javascript", "application/typescript"]);
const asDataUrl = (file: File) => new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(reader.error); reader.readAsDataURL(file); });

const compactNumber = (value: number) => new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value);

export function Composer({ running, disabled, send, stop, models, model, effort, threadUsage, compaction, onModel, onEffort }: { running: boolean; disabled: boolean; send: (text: string, attachments: ComposerAttachment[]) => boolean; stop: () => void; models: ModelOption[]; model: string; effort: string; threadUsage: ThreadUsage | null; compaction: CompactionStatus; onModel: (model: string) => void; onEffort: (effort: string) => void }) {
  const [text, setText] = useState(""); const [attachments, setAttachments] = useState<ComposerAttachment[]>([]); const [attachmentError, setAttachmentError] = useState(""); const [preview, setPreview] = useState<ComposerAttachment | null>(null);
  const area = useRef<HTMLTextAreaElement>(null); const input = useRef<HTMLInputElement>(null);
  useEffect(() => { if (area.current) { area.current.style.height = "0"; area.current.style.height = `${Math.min(area.current.scrollHeight, 160)}px`; } }, [text]);
  useEffect(() => { if (!preview) return; const close = (event: KeyboardEvent) => event.key === "Escape" && setPreview(null); addEventListener("keydown", close); return () => removeEventListener("keydown", close); }, [preview]);
  const submit = () => { if ((!text.trim() && !attachments.length) || running) return; if (send(text.trim(), attachments)) { setText(""); setAttachments([]); setAttachmentError(""); } };
  const addFiles = async (files: FileList | File[] | null) => {
    if (!files) return; setAttachmentError("");
    const next: ComposerAttachment[] = [];
    for (const file of Array.from(files).slice(0, Math.max(0, 4 - attachments.length))) {
      const image = file.type.startsWith("image/"); const textFile = textTypes.has(file.type) || /\.(txt|md|json|ya?ml|xml|csv|tsx?|jsx?|py|rs|go|java|c|cc|cpp|h|hpp|css|html|sh|toml)$/i.test(file.name);
      if (!image && !textFile) { setAttachmentError(`Unsupported attachment: ${file.name}`); continue; }
      if (file.size > (image ? 10 : 1) * 1024 * 1024) { setAttachmentError(`${file.name} is too large`); continue; }
      next.push({ id: `${Date.now()}-${file.name}-${next.length}`, name: file.name, mime: file.type || "text/plain", kind: image ? "image" : "text", data: image ? await asDataUrl(file) : await file.text(), size: file.size });
    }
    setAttachments((old) => [...old, ...next].slice(0, 4)); if (input.current) input.current.value = "";
  };
  const paste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(event.clipboardData.items).filter((item) => item.kind === "file").map((item) => item.getAsFile()).filter((file): file is File => Boolean(file));
    if (!files.length) return;
    event.preventDefault(); void addFiles(files);
  };
  const contextPercent = threadUsage?.modelContextWindow ? Math.max(0, Math.min(100, threadUsage.last.inputTokens / threadUsage.modelContextWindow * 100)) : null;
  return <><div className="composer-wrap"><div className="composer">
    {attachments.length > 0 && <div className="attachment-list">{attachments.map((attachment) => <div className="attachment-chip" key={attachment.id}>{attachment.kind === "image" ? <button type="button" className="attachment-preview-button" aria-label={`View ${attachment.name}`} onClick={() => setPreview(attachment)}><img src={attachment.data} alt="" /></button> : <span><FileText /></span>}<div><b>{attachment.name}</b><small>{attachment.kind === "image" ? "Image" : "Text file"} · {Math.max(1, Math.round(attachment.size / 1024))} KB</small></div><button type="button" className="attachment-remove" aria-label={`Remove ${attachment.name}`} onClick={() => setAttachments((old) => old.filter((item) => item.id !== attachment.id))}><X /></button></div>)}</div>}
    {attachmentError && <div className="attachment-error">{attachmentError}</div>}
    <textarea ref={area} value={text} disabled={disabled} rows={1} placeholder={disabled ? "Connect to Codex to start…" : "Ask Codex to work on your code"} onPaste={paste} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && matchMedia("(min-width: 701px)").matches) { event.preventDefault(); submit(); } }} />
    <div className="composer-toolbar"><div className="composer-tools"><input ref={input} className="attachment-input" type="file" multiple accept="image/*,.txt,.md,.json,.yaml,.yml,.xml,.csv,.ts,.tsx,.js,.jsx,.py,.rs,.go,.java,.c,.cc,.cpp,.h,.hpp,.css,.html,.sh,.toml" onChange={(event) => addFiles(event.target.files)} /><button className="attach-button" type="button" aria-label="Add attachment" onClick={() => input.current?.click()}><Paperclip /></button><ModelPicker models={models} model={model} effort={effort} onModel={onModel} onEffort={onEffort} />{effort && <span className="effort-chip">{effort}</span>}</div>
      <div className="composer-actions">{(contextPercent != null || compaction) && <div className={`context-indicator ${compaction?.status || ""}`} tabIndex={0} aria-label="Context window usage"><span style={{ "--context-used": `${contextPercent || 0}%` } as React.CSSProperties}><i /></span><div className="context-tooltip"><b>{compaction?.status === "running" ? "Compacting context…" : "Context window"}</b>{contextPercent != null && threadUsage?.modelContextWindow ? <><strong>{contextPercent.toFixed(0)}% used ({(100 - contextPercent).toFixed(0)}% left)</strong><em>{compactNumber(threadUsage.last.inputTokens)} / {compactNumber(threadUsage.modelContextWindow)} tokens used</em></> : <em>Usage appears after the next response</em>}{compaction?.status === "completed" && <small>Context compacted{compaction.at ? ` · ${new Date(compaction.at).toLocaleTimeString()}` : ""}</small>}</div></div>}<button className={`send ${running ? "stop" : ""}`} aria-label={running ? "Stop" : "Send"} onClick={running ? stop : submit}>{running ? <Square /> : <ArrowUp />}</button></div>
    </div>
  </div><div className="composer-hint">Codex can make mistakes. Review changes before committing.</div></div>{preview && <div className="image-lightbox" role="dialog" aria-label={preview.name} onMouseDown={(event) => event.target === event.currentTarget && setPreview(null)}><button type="button" aria-label="Close image preview" onClick={() => setPreview(null)}><X /></button><img src={preview.data} alt={preview.name} /></div>}</>;
}
