# Course Study Skills

[中文](README.md) | [English](README_EN.md)

Turn course materials into a textbook you can learn from, then use the same textbook to complete assignments. The two skills remain independent and share directory conventions and a source index.

| Skill | Purpose | Default output |
| --- | --- | --- |
| [learning-notes](skills/learning-notes/SKILL.md) | Verify course materials and create a complete HTML textbook for beginners | `textbook/index.html` and `textbook/textbook-index.json` |
| [kill-your-quizs](skills/kill-your-quizs/SKILL.md) | Complete assignments using the required format and classroom methods, with concise but complete answers | Required files in `submit/` |

## Use them together

First, create the textbook:

```text
Use $learning-notes to turn all relevant materials in /courses/lecture5 into a complete textbook.
Write the explanations in English and preserve the original technical titles.
```

Later, complete an assignment covering the same material:

```text
Use $kill-your-quizs to complete homework.pdf within /courses/lecture5,
following the assignment's required submission format.
```

The assignment skill first reads the current assignment and necessary inputs, then consults the textbook index and retrieves only relevant knowledge blocks. It checks the corresponding original materials when sources or textbook pages have changed, coverage is incomplete, or the assignment requires original code. Assignments can also be completed without a textbook; generating an entire textbook first is not required.

This reduces repeated extraction and the amount of unrelated text entering the context. Actual savings depend on the size of the materials, the assignment's scope, and source changes; no fixed reduction in time or tokens is promised.

The default teaching language for `learning-notes` is Simplified Chinese, with the original English titles preserved. The examples here explicitly request English explanations; specify English or another language when you want to override the default. Assignment answers follow the language required by the assignment or requested by the user.

## Complete example: a textbook and assignment for one lecture

The following hypothetical scenario shows the full workflow. Its paths and filenames are examples; this repository does not include these course materials. Assume lecture 5 covers conditional probability and the assignment accepts answers in English Markdown. Substitute your actual directory, assignment, and submission requirements.

### 1. Prepare the materials and create the textbook

Keep this lecture's materials together, preserving the original files:

```text
/courses/probability/lecture5/
├── lecture.pdf        # Slides: definitions, formulas, and classroom examples
├── transcript.txt     # Class transcript, possibly containing transcription errors
├── demo.py            # Classroom demonstration code
└── homework.pdf       # Assignment and submission requirements for this lecture
```

Send this request in Codex:

```text
Use $learning-notes with /courses/probability/lecture5 as the scope of this task.
Read all relevant materials there and create a complete HTML textbook that teaches beginners.
Write the explanations in English. Check the transcript against the course materials,
preserve the slides' original English titles, notation, and methods, and retain source locations.
You may consult homework.pdf to identify the skills students need; this task is only to create the textbook.
Save the textbook and source index in textbook/ within that directory.
Keep all drafts within lecture5 as well.
```

The expected outputs are `textbook/index.html` and `textbook/textbook-index.json`. The HTML is for reading; the index records knowledge block locations, related sources, and file fingerprints. Add `chapters/` and `assets/` only when separate chapters or external images are needed. Unverifiable content should be recorded as a gap, rather than filled with invented conclusions to claim completeness.

Open the HTML and check that the textbook covers the lecture. You can continue in the same chat or a new one: reuse depends on the saved textbook and index, not on memory of the previous conversation.

### 2. Use the existing textbook to complete the assignment

Send a second request:

```text
Use $kill-your-quizs to complete homework.pdf within /courses/probability/lecture5.
Consult the existing textbook in textbook/ first, and use the course's notation and methods for each question.
First check the current assignment, grading requirements, and necessary inputs.
Read demo.py when classroom code is needed.
The assignment in this example accepts English Markdown; write only the required answers to submit/answer.md.
Keep all outputs within lecture5.
```

The assignment skill reads the questions first, then uses the textbook index to locate a topic such as `Conditional probability`, reads the relevant passages and necessary prerequisite explanations, and checks fingerprints for the corresponding textbook pages and original materials. If a question gives `P(A ∩ B) = 0.12` and `P(B) = 0.4` and asks for the formula and result, the answer can be `P(A | B) = P(A ∩ B) / P(B) = 0.3`, without attaching the entire chapter's teaching content. Proofs, explanations, and lab assignments still need the steps and evidence required by the questions.

When the textbook provides sufficient, applicable support, the skill does not need to extract all slides again. The assignment, original data, specified code, and actual execution results still need to be checked as required; the textbook does not replace these inputs.

### 3. Handle source changes and gaps

Suppose the instructor replaces `lecture.pdf` to correct a condition in an example. When working on the assignment again, you can state this explicitly:

```text
Use $kill-your-quizs to continue checking homework.pdf within /courses/probability/lecture5.
lecture.pdf has been replaced with the instructor's corrected version.
Check the affected questions, consult the updated slides as needed, and update submit/answer.md.
Do not update the textbook in this task.
```

A changed fingerprint for a relevant source signals that it needs to be checked again. The skill should verify the affected passages and use supported corrections to complete the assignment; other applicable content can still be reused. If the textbook does not cover a question or has no index, the skill can consult the corresponding original materials directly without rebuilding the entire textbook first. Explicitly mention newly added errata files in your request, because the old index can check fingerprints only for files it already records.

To make the updated textbook available for future assignments, send a separate request:

```text
Use $learning-notes to update the textbook in /courses/probability/lecture5/textbook/.
Inventory the materials in lecture5 again, then check and revise the affected chapters against the new lecture.pdf.
Keep the explanations in English and preserve the original technical titles.
Reuse explanations that still apply, retain source references and unresolved gaps, and regenerate the index.
The scope remains lecture5. Preserve the original materials and existing assignment answers.
```

An update requires checking the content itself. Recalculating fingerprints alone does not establish that the old text agrees with the revised slides.

### 4. Check the final files

The minimal result for a single-page textbook looks like this. Add chapters, assets, and assignment attachments only when needed:

```text
/courses/probability/lecture5/
├── lecture.pdf
├── transcript.txt
├── demo.py
├── homework.pdf
├── textbook/
│   ├── index.html
│   └── textbook-index.json
├── .study-work/              # Drafts and extracted files created during the work
└── submit/
    └── answer.md            # The only submission file in this example
```

Open `textbook/index.html` to read the textbook; submit only the files in `submit/` that the assignment requires. The textbook, index, drafts, and answers all stay within `lecture5/`; they are not automatically written to `/courses/probability/`. To work on the entire course, explicitly select the course directory as the new scope.

## Directory boundaries

```text
lecture5/
├── lecture.pdf
├── homework.pdf
├── textbook/
│   ├── index.html
│   ├── textbook-index.json
│   ├── chapters/             # When separate chapters are needed
│   └── assets/               # When external assets are needed
├── .study-work/              # Drafts, extracted text, and build manifests
└── submit/                   # Required answers and attachments
```

Selecting `lecture5/` keeps the work inside it. The skills must not automatically create textbook, cache, or answer directories in its parent. Scripts check actual paths after resolving `..` and symbolic links. When the user explicitly specifies other input or output locations, those locations are handled under their respective authorization without broadening the scope for other files.

A complete textbook covers the full teaching content of the authorized scope. A course-wide textbook must use the course directory explicitly selected by the user as its root. Reading a shared textbook elsewhere requires an explicitly specified location; assignment outputs still stay in the current task directory.

## Installation

```bash
git clone https://github.com/yqia03/course-study-skills.git
cd course-study-skills
```

Each `skills/<skill-name>/` is a complete, independently installable directory containing its required scripts, references, and license. Neither skill depends on the other's installation location. Copy the entire directory for each skill you need into your skills directory; Codex defaults to `~/.codex/skills/`. If a skill with the same name is already installed, back up or compare your changes before updating it.

For example, run the following from the repository root. It stops if either installation already exists and does not overwrite it:

```bash
python3 - <<'PY'
import os
import shutil
from pathlib import Path

target = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
names = ('learning-notes', 'kill-your-quizs')
existing = [str(target / name) for name in names if (target / name).exists()]
if existing:
    raise SystemExit('Back up or compare existing installations first: ' + ', '.join(existing))
target.mkdir(parents=True, exist_ok=True)
for name in names:
    shutil.copytree(Path('skills') / name, target / name)
PY
```

Open a new chat and use the existing names, `$learning-notes` and `$kill-your-quizs`.

## Scripts and compatibility

The scripts require Python 3.10+ and use only the standard library. Reading PDFs, Office files, and media, and performing visual checks in a browser, depend on tools available in the environment. The builder preserves the existing offline search, collapsible table of contents, and formula and image rules.

- [Building and source mapping](skills/learning-notes/references/textbook-handoff.md): pass `--scope-root` and `--catalog` when building to generate a lightweight index.
- [On-demand lookup](skills/kill-your-quizs/references/textbook-reuse.md): find a topic by title or alias, read an individual knowledge block, and check the relevant page and source fingerprints.
- Legacy HTML without an index can still be consulted selectively, but the corresponding sources must be checked. Existing files are not automatically deleted or moved.
- `coverage` records completion within the scope. File fingerprints indicate whether versions have changed; they do not establish that teaching conclusions are correct.
- Build commands from before this update need `--scope-root`. The default output has changed from `<directory-name>-学习教材.html` in the scope root to `textbook/index.html`.

Run validation from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
```

The repository contains only skills and synthetic test fixtures, with no course materials, real assignments, or personal student IDs. Identity fields use values explicitly supplied by the user only when required by the assignment.

## Sources and license

`kill-your-quizs` is based on a locally revised version of [vect-G/lecture-to-hw](https://github.com/vect-G/lecture-to-hw) and retains its original MIT copyright notice. This repository uses the [MIT License](LICENSE); each independently installable skill also includes a license copy.
