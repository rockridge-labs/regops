"""
parser.py
Scan source files for compliance annotations.

Supported tags (in comments, language-agnostic):
  @req <ID>          — references a requirement
  @risk <ID>         — references a risk
  @class <A|B|C>     — IEC 62304 safety class
  @mitigation <ID>   — references a mitigation
  @test <ID>         — references a test case
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Matches any comment style: // ... or # ...
COMMENT_RE = re.compile(r'(?://|#)\s*(.*)')

# Matches individual annotation tags within a comment
TAG_RE = re.compile(
    r'@(req|risk|class|mitigation|test)\s+([\w-]+)',
    re.IGNORECASE,
)

# File extensions to scan, grouped by language
SUPPORTED_EXTENSIONS = {
    '.cpp', '.cc', '.cxx', '.c',    # C / C++
    '.h', '.hpp', '.hxx',           # C / C++ headers
    '.py',                           # Python
    '.pyx', '.pxd', '.pxi',         # Cython
    '.go',                           # Go
    '.dart',                         # Flutter / Dart
    '.cl',                           # OpenCL
    '.tf', '.tfvars',               # Terraform
}

# Directories to always skip
SKIP_DIRS = {
    'build', '.git', '__pycache__', 'node_modules',
    '.tox', 'dist', '*.egg-info', 'venv', '.venv',
    'bazel-bin', 'bazel-out', 'bazel-testlogs',
}


@dataclass
class TraceLink:
    """A single compliance annotation found in source code."""
    file: str               # relative path from repo root
    line: int               # 1-based line number
    reqs: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    safety_class: Optional[str] = None
    mitigations: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)

    def has_annotations(self) -> bool:
        return bool(self.reqs or self.risks or self.safety_class
                    or self.mitigations or self.tests)


def parse_repo(root: Path) -> list[TraceLink]:
    """
    Walk all source files in root and extract TraceLinks.
    Returns a flat list — one TraceLink per annotated block.
    """
    links: list[TraceLink] = []

    for path in sorted(root.rglob('*')):
        # Skip non-files and unsupported extensions
        if not path.is_file():
            continue
        if path.suffix not in SUPPORTED_EXTENSIONS:
            continue
        # Skip unwanted directories
        parts = set(path.parts)
        if parts & SKIP_DIRS:
            continue
        # Skip the compliance/ and .regops/ directories themselves
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in ('compliance', '.regops', 'fixtures'):
            continue

        links.extend(_parse_file(path, root))

    return links


def _parse_file(path: Path, root: Path) -> list[TraceLink]:
    """Extract all TraceLinks from a single file."""
    links: list[TraceLink] = []
    current: Optional[TraceLink] = None

    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []

    rel_path = str(path.relative_to(root))

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        comment_match = COMMENT_RE.search(raw_line)

        if not comment_match:
            # Non-comment line: flush accumulated link if any
            if current and current.has_annotations():
                links.append(current)
            current = None
            continue

        comment_text = comment_match.group(1)
        tags = TAG_RE.findall(comment_text)

        if not tags:
            # Comment with no annotation tags — flush if switching block
            if current and current.has_annotations():
                links.append(current)
                current = None
            continue

        # Start a new link or continue accumulating
        if current is None:
            current = TraceLink(file=rel_path, line=lineno)

        for tag_name, tag_value in tags:
            tag_name = tag_name.lower()
            if tag_name == 'req':
                current.reqs.append(tag_value.upper())
            elif tag_name == 'risk':
                current.risks.append(tag_value.upper())
            elif tag_name == 'class':
                current.safety_class = tag_value.upper()
            elif tag_name == 'mitigation':
                current.mitigations.append(tag_value.upper())
            elif tag_name == 'test':
                current.tests.append(tag_value.upper())

    # Flush last link
    if current and current.has_annotations():
        links.append(current)

    return links
