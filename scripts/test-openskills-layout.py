#!/usr/bin/env python3
"""Check the package layout OpenSkills creates, without network or a real HOME."""
import json
import re
import shutil
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
skills = sorted((root / 'plugins').glob('*/skills/*/SKILL.md'))
assert skills, 'no skills found'
names = [p.parent.name for p in skills]
assert len(names) == len(set(names)), 'duplicate skill names collide during install'

# These literals demonstrate syntax, not links to bundled resources.
example_links = {
    "note/skills/track-report/SKILL.md": {"URL", "<url>"},
    "note/skills/track-tool/SKILL.md": {"assets/<tool>.html"},
    "note/skills/track-markdown/SKILL.md": {"assets/file.png", "assets/file.mp3", "url"},
    "note/skills/track-markdown/references/ARCHITECTURE.md": {"assets/orders.c4"},
    "note/skills/track-markdown/references/DRAWING.md": {"url"},
    "note/skills/track-markdown/references/EMBEDS.md": {
        "src", "assets/logo.png", "assets/demo.html", "assets/map.html",
    },
}

claude_task = json.loads((root / 'plugins/task/.claude-plugin/plugin.json').read_text())
codex_task = json.loads((root / 'plugins/task/.codex-plugin/plugin.json').read_text())
claude_marketplace = json.loads((root / '.claude-plugin/marketplace.json').read_text())
codex_marketplace = json.loads((root / '.agents/plugins/marketplace.json').read_text())
claude_entry = next(plugin for plugin in claude_marketplace['plugins'] if plugin['name'] == 'task')
codex_entry = next(plugin for plugin in codex_marketplace['plugins'] if plugin['name'] == 'task')
assert claude_entry['source'] == codex_entry['source']['path'] == './plugins/task'
assert claude_entry['version'] == claude_task['version'] == codex_task['version']
assert claude_entry['skills'] == claude_task['skills'] == codex_task['skills'] == './skills/'
assert len(codex_task['interface']['defaultPrompt']) <= 3

with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / '.agent' / 'skills'
    target.mkdir(parents=True)
    for skill in skills:
        # OpenSkills 1.5.0 copies each skill root recursively with dereference=true.
        shutil.copytree(skill.parent, target / skill.parent.name, symlinks=False)
    for skill in skills:
        installed = target / skill.parent.name / 'SKILL.md'
        assert installed.read_bytes() == skill.read_bytes(), skill
        for markdown in installed.parent.rglob('*.md'):
            source_md = skill.parent / markdown.relative_to(installed.parent)
            for path in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', markdown.read_text()):
                if path.startswith(('http:', 'https:', 'mailto:', '#')):
                    continue
                relative_source = source_md.relative_to(root / 'plugins').as_posix()
                assert not path.startswith(('file:', '/')), f'{relative_source}: nonportable local link {path}'
                if path in example_links.get(relative_source, ()):
                    continue
                assert (source_md.parent / path).exists(), f'{relative_source}: missing source link {path}'
                resolved = (markdown.parent / path).resolve()
                assert resolved.is_relative_to(target.resolve()), f'{relative_source}: escapes installed skills: {path}'
                assert resolved.exists(), f'{relative_source}: missing installed link {path}'
    for name in ('track-timeline', 'track-timeline-interval-reports'):
        metadata = target / name / 'agents/openai.yaml'
        assert metadata.is_file() and f'${name}' in metadata.read_text(), f'{name}: missing client prompt'
    for skill in (root / 'plugins/task/skills').glob('*/SKILL.md'):
        bundled = target / skill.parent.name / 'references/runtime.md'
        assert bundled.read_bytes() == (root / 'plugins/task/references/runtime.md').read_bytes()
print(f'OpenSkills copied layout: {len(skills)} skills, relative Markdown links and task runtime OK')
