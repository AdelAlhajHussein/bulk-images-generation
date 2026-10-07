# Image capability and portability

Inspected on 2026-10-05 in the current Codex desktop environment:

- A built-in image_gen.imagegen tool is callable (through orchestration as tools.image_gen__imagegen). Its parameters include prompt, transparent_background, and reference images. There is no declared destination or size argument. Request widescreen in the prompt, then check actual dimensions.
- The installed imagegen instructions specify that built-in generation needs no API key, saves beneath $CODEX_HOME/generated_images/..., and requires copying project assets into the workspace. Use actual result paths rather than guessed filenames.
- In this orchestration environment, display the returned result through generatedImage(result) rather than printing encoded image data. Follow the current tool's wait instructions.
- A local shell and Python support file saving and verification. This skill's helper uses only Python's standard library and makes no network calls.

These are capability observations, not a live generation test. Skill creation did not generate images. Recheck tools in future sessions: a skill cannot grant missing capabilities. Tool availability does not guarantee quota, exact dimensions, or successful export.

If built-in generation or export is unavailable, deliver the prompt package with incomplete statuses. An external integration would require an authorized image backend, credentials if required by that backend, supported widescreen output, PNG export, and mapping each result to its manifest entry. If an installed imagegen skill offers a CLI/API fallback, follow its current instructions only when explicitly requested or confirmed. Do not install SDKs, require an API key, choose a paid provider, or implement speculative integration during preparation.

Structure follows [official skill conventions](https://developers.openai.com/codex/skills): SKILL.md, optional agents/openai.yaml, and task-specific supporting files. The portable source lives at bulk-images-generation/ in this project. Invoke it by asking Codex to read its SKILL.md. For automatic discovery, copy/install it into a skill directory supported by the target environment, commonly repository .agents/skills/ or the personal skills directory. Source creation alone does not install the skill.
