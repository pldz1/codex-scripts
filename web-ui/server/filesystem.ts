import fs from "node:fs/promises";
import path from "node:path";

const hidden = new Set([".git", "node_modules", "dist", "build", ".next", "coverage"]);
const MAX_FILE_SIZE = 1024 * 1024;

export class WorkspaceFs {
  private root = "";
  private base = "";
  private selected = false;
  constructor(private requestedRoot: string, private requestedBase = requestedRoot, selected = false) { this.selected = selected; }

  async init() {
    this.root = await fs.realpath(this.requestedRoot);
    this.base = await fs.realpath(this.requestedBase);
    if (!this.inside(this.base, this.root)) this.base = path.dirname(this.root);
  }
  get path() { return this.root; }
  get basePath() { return this.base; }
  get isSelected() { return this.selected; }

  private inside(parent: string, candidate: string) {
    const relative = path.relative(parent, candidate);
    return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
  }

  private async safeFrom(parent: string, relative = "", existing = true) {
    if (path.isAbsolute(relative)) throw new Error("Absolute paths are not allowed");
    const candidate = path.resolve(parent, relative);
    const resolved = existing ? await fs.realpath(candidate) : candidate;
    if (!this.inside(parent, resolved)) throw new Error("Path escapes allowed workspace root");
    return resolved;
  }

  private async safe(relative = "", existing = true) {
    return this.safeFrom(this.root, relative, existing);
  }

  async listWorkspaces(relative = "") {
    const dir = await this.safeFrom(this.base, relative);
    const entries = await fs.readdir(dir, { withFileTypes: true });
    return entries
      .filter((entry) => entry.isDirectory() && !hidden.has(entry.name) && !entry.name.startsWith("."))
      .map((entry) => ({ name: entry.name, path: path.posix.join(relative.replaceAll("\\", "/"), entry.name), type: "directory" as const }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  async select(relative = "") {
    const selected = await this.safeFrom(this.base, relative);
    const stat = await fs.stat(selected);
    if (!stat.isDirectory()) throw new Error("Workspace must be a directory");
    this.root = selected;
    this.selected = true;
    return { path: this.root, relative: path.relative(this.base, this.root).replaceAll("\\", "/") };
  }

  async selectAbsolute(candidate: string) {
    const resolved = await fs.realpath(candidate);
    if (!this.inside(this.base, resolved)) throw new Error("Session workspace is outside the browsable root");
    const stat = await fs.stat(resolved);
    if (!stat.isDirectory()) throw new Error("Workspace must be a directory");
    this.root = resolved;
    this.selected = true;
    return { path: this.root, relative: path.relative(this.base, this.root).replaceAll("\\", "/") };
  }

  async list(relative = "") {
    const dir = await this.safe(relative);
    const entries = await fs.readdir(dir, { withFileTypes: true });
    return entries
      .filter((entry) => !hidden.has(entry.name))
      .map((entry) => ({ name: entry.name, path: path.posix.join(relative.replaceAll("\\", "/"), entry.name), type: entry.isDirectory() ? "directory" : entry.isFile() ? "file" : "other" }))
      .filter((entry) => entry.type !== "other")
      .sort((a, b) => a.type === b.type ? a.name.localeCompare(b.name) : a.type === "directory" ? -1 : 1);
  }

  async read(relative: string) {
    const file = await this.safe(relative);
    const stat = await fs.stat(file);
    if (!stat.isFile()) throw new Error("Not a file");
    if (stat.size > MAX_FILE_SIZE) throw new Error("File exceeds 1 MB preview limit");
    const buffer = await fs.readFile(file);
    if (buffer.subarray(0, 8000).includes(0)) throw new Error("Binary files cannot be previewed");
    return { path: relative, content: buffer.toString("utf8"), size: stat.size };
  }

  async write(relative: string, content: string) {
    if (Buffer.byteLength(content, "utf8") > MAX_FILE_SIZE) throw new Error("File exceeds 1 MB edit limit");
    const file = await this.safe(relative);
    const stat = await fs.stat(file);
    if (!stat.isFile()) throw new Error("Not a file");
    await fs.writeFile(file, content, "utf8");
    return this.read(relative);
  }
}
