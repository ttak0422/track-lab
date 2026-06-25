# Research Plugin

`research` is the reference plugin implementation for track-lab. Use it as the model when adding later plugins: keep the host-specific manifests, marketplace entries, and shared skill folder aligned.

## Layout

```text
plugins/research/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
└── skills/research/SKILL.md
```

The plugin name and primary skill name are both `research`. The skill body at `skills/research/SKILL.md` is the shared implementation. Host-specific files only describe how each agent discovers and installs it.

## Codex

```sh
codex plugin add research@track-lab
```

If the marketplace is not registered yet:

```sh
codex plugin marketplace add /path/to/track-lab
codex plugin add research@track-lab
```

## Claude Code

For local development, load the plugin directory directly:

```sh
claude --plugin-dir ./plugins/research
```

Inside Claude Code, invoke the namespaced skill with:

```text
/research:research
```

For marketplace-style installation, add the repository marketplace and install the plugin inside Claude Code:

```text
/plugin marketplace add /path/to/track-lab
/plugin install research@track-lab
/reload-plugins
```

Claude Code uses `.claude-plugin/marketplace.json` at the repository root and `plugins/research/.claude-plugin/plugin.json` inside the plugin.

## Standalone Skill

Agents that support the Agent Skills `SKILL.md` layout can use the shared skill directly:

```text
plugins/research/skills/research/SKILL.md
```

For Claude Code project-local standalone usage, copy or symlink `plugins/research/skills/research` to:

```text
.claude/skills/research
```

That exposes it as `/research` instead of the plugin-namespaced `/research:research`.

## Adding Later Plugins

1. Create `plugins/<plugin-name>/.codex-plugin/plugin.json` for Codex.
2. Create `plugins/<plugin-name>/.claude-plugin/plugin.json` for Claude Code.
3. Put shared skill instructions under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`.
4. Add the plugin to `.agents/plugins/marketplace.json` for Codex with `source.path` set to `./plugins/<plugin-name>`.
5. Add the plugin to `.claude-plugin/marketplace.json` for Claude Code with `source` set to `./plugins/<plugin-name>`.
6. Validate the plugin before installing it.
