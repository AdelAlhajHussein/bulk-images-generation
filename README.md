# Bulk Images Generation

A reusable Codex skill for teachers and course creators. Turn a sectioned lesson into one educational slide image per section, with a consistent style, numbered files, and a manifest that preserves the narration and prompts.

## Install in Codex

Give Codex this request:

```text
Use $skill-installer to install the skill at the root of
https://github.com/AdelAlhajHussein/bulk-images-generation
with the installed name bulk-images-generation.
```

The skill lives at the repository root. For installers requiring explicit arguments, use repository `AdelAlhajHussein/bulk-images-generation`, path `.`, and name `bulk-images-generation`. Install the entire folder, including scripts and references. If the skill does not appear, start a new chat or restart Codex.

## Use

```text
Use $bulk-images-generation to read my entire lesson and generate
one educational image per section. Save the images and manifest
in a clearly named folder in this project.

[Paste a lesson with section numbers, titles, and narration]
```

For a first test, ask the skill to use its bundled `references/six-section-lesson.md` and prepare prompts only. Then ask it to generate the six images from the saved manifest.

## What it does

- Reads the complete lesson and preserves section order and narration.
- Selects visuals that explain the content instead of displaying the transcript.
- Uses one consistent style and requests exact 16:9 PNG images.
- Keeps text short and excludes humans unless explicitly requested.
- Saves one numbered image per section, plus `manifest.json` and `prompts.md`.
- Records progress after each accepted image and checks saved files before completion.

If interrupted, retain the output folder and ask: "Resume from this manifest and skip completed images." The skill does not automatically wake up after usage limits reset. An image interrupted before it is saved and recorded may require recovery or regeneration.

## Requirements and limitations

Use a Codex environment with local file access, Python 3.10+, and an available image-generation tool. Installing this skill does not add image-generation access or usage credits. With the built-in image tool, no external API key is required. Without a supported image tool, the skill can prepare prompts and a manifest; external integration requires a separate explicit choice.

The helper uses only Python's standard library. Codex performs the educational analysis and calls image tools; the Python script does not generate images. Actual dimensions are checked because a widescreen prompt alone does not guarantee 16:9 output. Scientific accuracy, label quality, and style consistency require visual review.

Offline helper tests have passed. Live image generation and export have not yet been tested end to end.

## Helper commands

Run from this repository's root (use `py -3` on Windows if needed):

```sh
python scripts/lesson_images.py prepare plan.json --output-root output
python scripts/lesson_images.py verify output/lesson-title-images/manifest.json
python -B scripts/test_lesson_images.py
```

See [the skill instructions](SKILL.md) and [workflow reference](references/workflow.md) for plan fields, attaching reviewed images, and failure handling. Lesson examples are test fixtures; the workflow is not tied to one subject.
