# Plan schema and helper commands

Use Python 3.10+ (py -3 on Windows, python3 elsewhere). Resolve the helper relative to the skill; save plans and outputs in the user's workspace, not inside an installed skill.

After reading all narration, Codex writes a JSON object with the following required fields:

```json
{
  "lesson_title": "Lesson title",
  "audience": "Beginning learners",
  "style": "Clean illustration; navy outlines, teal accents, white background; simple sans-serif labels; consistent diagram arrows.",
  "allow_humans": false,
  "sections": [
    {
      "section_number": "1",
      "section_title": "Section title",
      "transcript": "Exact original narration, preserving line breaks.",
      "learning_goal": "The relationship the student should understand",
      "visual_concept": "Specific objects and relationships demonstrating the narration",
      "composition": "Wide view with a focal point and room for annotations",
      "accuracy_notes": "Required arrows, relationships, relative sizes, or simplifications",
      "labels": ["Short label"]
    }
  ]
}
```

Array order controls output order, regardless of original numbers (integers or strings). Labels may be empty. Set allow_humans true only on explicit user request. The helper does not analyze transcripts or generate images; Codex supplies the visual decisions and calls image tools.

From the project root:

```powershell
py -3 bulk-images-generation/scripts/lesson_images.py prepare plan.json --output-root output
```

Creates output/<lesson-title>-images/, or a numbered sibling on rerun. Outputs are manifest.json and readable prompts.md. Filenames use sequence positions with at least two digits and safe title slugs. Unicode titles are supported. The transcript is preserved in the manifest, not pasted into the image prompt.

After generation and visual review:

```powershell
py -3 bulk-images-generation/scripts/lesson_images.py attach output/lesson-title-images/manifest.json --order 1 --image "C:/actual/tool/result.png" --reviewed
```

For a revised generation prompt, add --prompt-file final-prompt.txt containing the exact submitted UTF-8 text. The manifest preserves initial_prompt and updates generated_image_prompt; prompts.md stays synchronized. Existing images are never overwritten. Run commands sequentially; this is not a concurrent queue.

Record failures and verify:

```powershell
py -3 bulk-images-generation/scripts/lesson_images.py block output/lesson-title-images/manifest.json --order 2 --reason "Backend could not export a 16:9 PNG"
py -3 bulk-images-generation/scripts/lesson_images.py verify output/lesson-title-images/manifest.json
```

Verification exits nonzero for incomplete entries, missing files, bad PNG signatures or dimensions, changed hashes, or extra PNGs in the folder. Header checks and hashes do not fully decode images or verify semantic correctness; visual review is required. Statuses are planned, blocked, and complete. Only attach --reviewed marks complete.

## Six-section test

Use [six-section-lesson.md](six-section-lesson.md). Ask Codex:

> Read bulk-images-generation/SKILL.md and use it with bulk-images-generation/references/six-section-lesson.md. Prepare prompts only. Save the plan and output package in this project.

Expect six distinct explanations, verbatim narration, one style, no humans, and planned filenames 01-the-water-cycle.png through 06-collection-and-infiltration.png. No images should yet be claimed. Then ask:

> Use the existing manifest to generate all six images with the built-in image tool, save them, and verify the completed lesson folder.

Also test another subject; do not reuse water-cycle content. Run helper checks without generation or credentials:

```powershell
py -3 bulk-images-generation/scripts/test_lesson_images.py
```
