from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


TYPE_TO_SECTION = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "docs": "Changed",
    "chore": "Changed",
    "ci": "Changed",
    "build": "Changed",
    "test": "Changed",
    "style": "Changed",
    "security": "Security",
}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def parse_commit_subject(subject: str) -> tuple[str, str]:
    pattern = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]+\))?(?:!)?:\s*(?P<body>.+)$")
    match = pattern.match(subject.strip())
    if match:
        ctype = match.group("type").lower()
        body = match.group("body").strip()
        section = TYPE_TO_SECTION.get(ctype, "Changed")
        return section, body
    return "Changed", subject.strip()


def commits_for_range(rev_range: str) -> list[str]:
    output = git("log", "--pretty=%s", "--no-merges", rev_range)
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def normalize_line(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    text = text[0].upper() + text[1:] if text else text
    return text if text.endswith(".") else f"{text}."


def render_section(commits: list[str], empty_message: str | None = None) -> str:
    grouped: dict[str, list[str]] = {}
    for subject in commits:
        section, message = parse_commit_subject(subject)
        grouped.setdefault(section, []).append(normalize_line(message))

    parts: list[str] = []
    for section_name in ("Added", "Changed", "Fixed", "Security"):
        entries = grouped.get(section_name, [])
        if not entries:
            continue
        parts.append(f"### {section_name}")
        for msg in entries:
            parts.append(f"- {msg}")
    if parts:
        return "\n".join(parts)
    if empty_message:
        return f"### Changed\n- {empty_message}"
    return "### Changed\n- Internal maintenance updates."


def collect_tags() -> list[str]:
    output = git("tag", "--list", "v*", "--sort=version:refname")
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def build_changelog() -> str:
    tags = collect_tags()
    latest_tag = tags[-1] if tags else None

    lines = [
        "# Changelog",
        "",
        "All notable changes to this project are documented in this file.",
        "The format follows Keep a Changelog and Semantic Versioning 2.0.0.",
        "",
        "## [Unreleased]",
    ]

    unreleased_commits = commits_for_range(f"{latest_tag}..HEAD") if latest_tag else commits_for_range("HEAD")
    lines.append(render_section(unreleased_commits, empty_message="No unreleased changes yet."))
    lines.append("")

    for idx in range(len(tags) - 1, -1, -1):
        tag = tags[idx]
        version = tag[1:]
        date = git("log", "-1", "--format=%cs", tag)
        prev_tag = tags[idx - 1] if idx > 0 else None
        rev_range = f"{prev_tag}..{tag}" if prev_tag else tag
        tag_commits = commits_for_range(rev_range)

        lines.append(f"## [{version}] - {date}")
        lines.append(render_section(tag_commits))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    content = build_changelog()
    CHANGELOG_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
