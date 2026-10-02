"""Project memory: lessons the agent saves for *future* runs.

Lessons are loaded into the system prompt when a run starts and never change
during it (the system prompt is part of the conversation the model's reasoning
is bound to). A lesson saved now takes effect on the next run.

Memory is also an attack surface — text that gets injected into every future
prompt — so lessons are short, capped, deduplicated, and live in a file a human
can read and review in version control.
"""

from __future__ import annotations

from pathlib import Path

LESSONS = Path(".harness/lessons.md")
MAX_LESSON_CHARS = 300
MAX_LESSONS = 30


def load(root: Path) -> list[str]:
    path = root / LESSONS
    if not path.is_file():
        return []
    return [line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("- ")]


def remember(root: Path, lesson: str) -> str:
    lesson = " ".join(lesson.split())[:MAX_LESSON_CHARS]
    if not lesson:
        return "Nothing to save."
    lessons = load(root)
    if lesson in lessons:
        return "Already known."
    if len(lessons) >= MAX_LESSONS:
        return f"Memory is full ({MAX_LESSONS} lessons); a human needs to review {LESSONS}."
    path = root / LESSONS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- {lesson}\n")
    return "Saved. It will be loaded at the start of the next run."
