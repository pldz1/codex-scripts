---
name: azure-image-gen
description: Generate images with an Azure OpenAI GPT-Image-2 deployment. Use when the user asks to create, draw, render, visualize, or generate an image through their Azure OpenAI endpoint, especially when Codex's built-in image generation is unavailable. Do not use for merely analyzing an existing image.
---

Use this skill to generate image files through the user's Azure OpenAI GPT-Image-2 deployment.

## Required configuration

The script reads credentials only from environment variables. Never ask the user to paste a key into chat, a command argument, `SKILL.md`, or `auth.json`.

Required:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT` or `AZURE_OPENAI_BASE_URL`
- `AZURE_OPENAI_IMAGE_DEPLOYMENT` or `AZURE_OPENAI_DEPLOYMENT_NAME`

Optional:

- `AZURE_OPENAI_IMAGE_API_VERSION` defaults to `preview`

If configuration is missing, direct the user to `references/configuration.md`.

## Workflow

1. Resolve this skill's directory from the path of this `SKILL.md` shown by Codex.
2. Check configuration without exposing secrets:

   ```bash
   python3 <skill-dir>/scripts/azure_image_generate.py --check
   ```

3. Turn the user's request into a precise image prompt. Preserve requested text, composition, aspect ratio, style, camera, lighting, and exclusions. Do not silently add brand marks, signatures, or watermarks.
4. Choose parameters:
   - Default `--size 1024x1024` unless the user requests another size or aspect ratio.
   - Default `--quality high`.
   - Default `--n 1`; the API accepts 1–10.
   - Default `--format png`; use `jpeg` only when the user requests it or smaller files matter.
   - For GPT-Image-2 custom sizes, both edges must be multiples of 16, the aspect ratio cannot exceed 3:1, the long edge cannot exceed 3840 px, and total pixels must be between 655360 and 8294400.
5. Run the generator. Prefer stdin for the prompt so complex prompts are not exposed as process arguments:

   ```bash
   python3 <skill-dir>/scripts/azure_image_generate.py \
     --size 1024x1024 \
     --quality high \
     --format png \
     --output-dir ./generated-images <<'AZURE_IMAGE_PROMPT'
   Put the complete image prompt here.
   AZURE_IMAGE_PROMPT
   ```

6. The script prints one JSON object. Read the `files` array and verify each listed file exists.
7. Report the generated file path(s), model deployment, size, and quality. When image inspection is available, inspect the output and mention obvious mismatches; otherwise do not claim visual details you did not verify.
8. If the request fails:
   - `401`: configuration or API key problem.
   - `404` / `DeploymentNotFound`: wrong deployment name or endpoint.
   - `429`: quota/rate limit; retry later or lower `n`.
   - content-policy error: explain that Azure's image safety filter rejected the request and ask for a compliant revision.
   - invalid size: choose a valid GPT-Image-2 size while preserving the requested aspect ratio as closely as possible.

## Boundaries

- This skill generates new images. It does not edit an existing image.
- Do not print, log, or save the API key.
- Do not place generated images inside the skill directory unless the user explicitly requests that location.
- Do not claim the image was generated until the script exits successfully and the output file exists.
