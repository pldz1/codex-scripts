import { ArrowLeft, Check, ChevronDown, ChevronRight, FileCode2, Folder, FolderOpen, PanelRight, Pencil, Save, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { FileEntry } from "../types";

function Tree({ path, load, openFile }: { path: string; load: (path: string) => Promise<FileEntry[]>; openFile: (path: string) => void }) {
  const [entries, setEntries] = useState<FileEntry[]>([]); const [open, setOpen] = useState(path === "");
  useEffect(() => { if (open) load(path).then(setEntries); }, [open, path, load]);
  if (path && !open) return <button className="tree-row folder" onClick={() => setOpen(true)}><ChevronRight /><Folder /> <span>{path.split("/").pop()}</span></button>;
  return <div className={path ? "tree-branch" : ""}>{path && <button className="tree-row folder" onClick={() => setOpen(false)}><ChevronDown /><FolderOpen /> <span>{path.split("/").pop()}</span></button>}{entries.map((entry) => entry.type === "directory" ? <Tree key={entry.path} path={entry.path} load={load} openFile={openFile} /> : <button className="tree-row file" key={entry.path} onClick={() => openFile(entry.path)}><span className="tree-indent" /><FileCode2 /> <span>{entry.name}</span></button>)}</div>;
}

export function FileDrawer({ close, load, read, write, onSaved }: { close: () => void; load: (path: string) => Promise<FileEntry[]>; read: (path: string) => Promise<{ path: string; content: string }>; write: (path: string, content: string) => Promise<{ path: string; content: string }>; onSaved?: (path: string, before: string, after: string) => void }) {
  const [file, setFile] = useState<{ path: string; content: string } | null>(null); const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(false); const [draft, setDraft] = useState(""); const [saving, setSaving] = useState(false); const [saved, setSaved] = useState(false);
  const openFile = (path: string) => read(path).then((next) => { setFile(next); setDraft(next.content); setEditing(false); setSaved(false); });
  const save = async () => { if (!file) return; setSaving(true); try { const before = file.content; const next = await write(file.path, draft); setFile(next); setEditing(false); setSaved(true); onSaved?.(file.path, before, next.content); window.setTimeout(() => setSaved(false), 1400); } finally { setSaving(false); } };
  return <div className="drawer-layer" onMouseDown={(event) => event.target === event.currentTarget && close()}><section className={`file-drawer ${file ? "previewing" : ""}`}>
    <header><button className="mobile-back icon-button" aria-label="Back" onClick={() => file ? setFile(null) : close()}><ArrowLeft /></button><div><span>Workspace</span><b>{file ? file.path.split("/").pop() : "Files"}</b></div><button className="icon-button" aria-label="Close files" onClick={close}><X /></button></header>
    <div className="files-body"><div className="tree-pane"><label className="search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search files" /></label><div className="workspace-name"><FolderOpen /><span>workspace</span></div><Tree path="" load={load} openFile={openFile} /></div>
    <div className="preview-pane">{file ? <><div className="preview-head"><span><FileCode2 />{file.path}</span><div className="preview-actions">{editing ? <><button onClick={() => { setEditing(false); setDraft(file.content); }}>Cancel</button><button className="primary" disabled={saving || draft === file.content} onClick={save}><Save />{saving ? "Saving…" : "Save"}</button></> : <button onClick={() => setEditing(true)}>{saved ? <Check /> : <Pencil />}{saved ? "Saved" : "Edit"}</button>}</div></div>{editing ? <textarea className="file-editor" value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} /> : <pre>{file.content.split("\n").map((line, index) => <span key={index}><i>{index + 1}</i>{line}{"\n"}</span>)}</pre>}</> : <div className="preview-empty"><PanelRight /><b>Preview a file</b><p>Select a text file from the workspace.</p></div>}</div></div>
  </section></div>;
}
