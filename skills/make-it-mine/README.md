# Make It Mine — Codex Skill

A personal Agent Skill for turning AI-assisted full-stack software development into engineering judgment you actually own.

## What it trains

The skill focuses on whether you can independently:

- understand a concept and its underlying problem
- place responsibilities in the correct system/UI layer
- choose technologies against realistic alternatives
- explain trade-offs and rejected options
- reason about failure and production operation
- choose UI/UX patterns based on user needs
- adapt architecture when constraints change
- notice where you still depend on AI for reasoning

## Package structure

```text
make-it-mine/
├── SKILL.md
├── README.md
├── references/
│   ├── CAPABILITY_FRAMEWORK.md
│   ├── TECH_SELECTION.md
│   ├── UI_UX_JUDGMENT.md
│   └── AUDIT_QUESTION_BANK.md
├── assets/
│   ├── CAPABILITY_MAP.md
│   ├── ENGINEERING_GROWTH_RECEIPT.md
│   └── LEARNING_LOG.md
└── scripts/
    ├── init_state.py
    └── make_it_mine.py
```

`SKILL.md` intentionally contains only the always-needed workflow. Detailed material lives in `references/` so the agent can load it only when relevant.

## Install/use with Codex

This package follows the Agent Skills format used by Codex: a skill directory with a required `SKILL.md` containing YAML frontmatter plus optional resources and scripts.

Depending on your Codex surface, install/import the skill using the Skills management UI or place the unzipped skill in a skills location recognized by your Codex setup.

The ZIP is also suitable for systems that accept Agent Skill zip bundles.

After installation, try prompts such as:

- `Use make-it-mine to audit what I actually learned from this architecture decision.`
- `I chose Redis here. Make this decision mine.`
- `Test whether I actually understand why this state belongs in the frontend.`
- `Audit my UI choice: why a drawer instead of a modal?`
- `What engineering capabilities am I still outsourcing to AI?`
- `Run a deep make-it-mine audit on this system design.`

## Optional persistent capability tracking

The skill does **not** silently modify your repository.

For one project's capability map and learning log, run from your project root:

```bash
python /path/to/make-it-mine/scripts/init_state.py --scope project
```

For a personal learning route shared across projects and machines, use user scope:

```bash
python /path/to/make-it-mine/scripts/init_state.py --scope user
```

User state is stored at `~/.make-it-mine`; project state is stored at
`./.make-it-mine`. Both contain human-readable Markdown and an append-only
`EVENTS.jsonl` ledger. Existing files are never overwritten.

It creates:

```text
.make-it-mine/
├── CAPABILITY_MAP.md
├── LEARNING_LOG.md
└── EVENTS.jsonl
```

Existing files are never overwritten.

If this is personal learning state, consider adding `.make-it-mine/` to `.gitignore`.

The dependency-free management script supports inspection, date statistics,
portable export, and conflict-aware import/merge:

```bash
python /path/to/make-it-mine/scripts/make_it_mine.py show list --scope user
python /path/to/make-it-mine/scripts/make_it_mine.py show stats --scope user
python /path/to/make-it-mine/scripts/make_it_mine.py export --scope user --output learning-bundle.zip
python /path/to/make-it-mine/scripts/make_it_mine.py merge --scope user --input other-learning-bundle.zip
python /path/to/make-it-mine/scripts/make_it_mine.py show conflicts --scope user
```

Merge uses stable event IDs: identical events are skipped, new events are
added, and differing events are preserved as conflicts instead of silently
overwriting either copy. Imported evidence is marked `imported`; it does not
automatically promote a capability in the local map. Re-audit it before
counting it as independently owned judgment.

In a Codex conversation, `/make-it-mine show list` can be treated as a
read-only shorthand for the user-scoped viewer. It is a conversational
convention, not a system-level slash-command registration.

## Philosophy

> Don't track what AI did for me. Track the engineering judgment I now own.
