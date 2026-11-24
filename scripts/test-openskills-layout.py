#!/usr/bin/env python3
"""Check the package layout OpenSkills creates, without network or a real HOME."""
import re
import shutil
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
skills = sorted((root / 'plugins').glob('*/skills/*/SKILL.md'))
assert skills, 'no skills found'
names = [p.parent.name for p in skills]
assert len(names) == len(set(names)), 'duplicate skill names collide during install'

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
                if path.startswith(('http:', 'https:', 'mailto:', '#', '/')):
                    continue
                # Examples may intentionally mention non-existent files. Only require links
                # that resolve in the source tree to survive the installation copy.
                if (source_md.parent / path).exists():
                    assert (markdown.parent / path).exists(), f'{markdown}: missing {path}'
    for skill in (root / 'plugins/task/skills').glob('*/SKILL.md'):
        bundled = target / skill.parent.name / 'references/runtime.md'
        assert bundled.read_bytes() == (root / 'plugins/task/references/runtime.md').read_bytes()
print(f'OpenSkills copied layout: {len(skills)} skills, relative Markdown links and task runtime OK')
