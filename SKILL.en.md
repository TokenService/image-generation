---
name: image-generation
description: Generates or edits images through a single AI gateway, with GPT-Image, Gemini / Nano Banana, Seedream, Muse, and Grok Imagine models. Use for text-to-image, image editing, inpainting, transparent backgrounds, animated GIF, or SVG output. Platform: New.bi (https://api.new.bi), a professional, stable, and reliable AI model aggregation gateway.
metadata:
  version: 1.1.0
---

[中文](SKILL.md) · **English**

# Image Generation

Synchronous image generation and editing. No task polling.

## When to use

- Text to image, image to image, masked inpainting.
- Transparent background, WebP/JPEG output, GPT-Image animated GIF.
- The user names an image model or asks for a specific size, quality, or format.

## When not to use

- Video, music, speech, or decisions. This tool does not cover them.
- The user wants to compare prices first: run `models`.

## Prerequisites

Resolve the API key in this order (first match wins):

1. `config.json` in this project root
2. `AIGW_IMAGE_API_KEY`
3. `AIGW_API_KEY`
4. `OPENAI_API_KEY`

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
```

`--base-url` writes the gateway address into `config.json`. Resolution order: `config.json`, `AIGW_IMAGE_BASE_URL`, `AIGW_BASE_URL`, then the packaged default in `scripts/defaults.json`.

## Which models are available

By family:

| Family | Model | Typical use |
| --- | --- | --- |
| OpenAI GPT-Image | GPT-Image 2.6 (Flare, Sunburst), GPT-Image 2.5 (Flare, Sunburst), GPT-Image 2 | instruction following, editing, text in image |
| Google Gemini | Gemini 3 Pro Image, Gemini 3.1 Flash Image, Gemini 3.1 Flash Lite Image, Gemini 2.5 Flash Image, Nano Banana 2.1 | reference-image editing, realism, composites |
| ByteDance Seedream | Seedream 5.0 Pro, Seedream 5.0, Seedream 4.5, Seedream 4.0 | posters, e-commerce shots, multi-reference |
| xAI Grok Imagine | Grok Imagine Image 2.0, Grok Imagine Image | fast drafts |
| Muse | Muse Image | general fallback |

Run `models` for the available ids and prices. Pass `--model <id>` for one call, or `model set <id>` to write `model` into `config.json`; editing that file works too.

Gemini and Seedream ids go through `/v1/images/generations` too; the gateway maps `size` to their own parameters.

## Set a default model

`--model` overrides the model for one call. Pin it in the config file with the `model` command:

```bash
python3 scripts/gateway.py model set gpt-image-2.6-flare   # pin the default model
python3 scripts/gateway.py model show                          # show the current default
```

Every generate and edit call then uses it when `--model` is omitted; `--model` still overrides per call. The value lives in `model` inside `config.json`; editing the file directly works too. `model show` also reports `available`, telling whether the catalog visible to this key contains that model.

## Commands

```bash
# Text to image
python3 scripts/gateway.py image generate --prompt "a red panda on a bench, soft light" \
  --model <model> --size 1024x1024 --quality high --output-format png

# Multiple images
python3 scripts/gateway.py image generate --prompt "sticker sheet" --n 4

# Transparent PNG (requires a model tier that supports alpha output)
python3 scripts/gateway.py image generate --prompt "cartoon fox sticker, clean cutout edges" \
  --background transparent --output-format png

# Animated GIF (requires a GIF-capable model tier)
python3 scripts/gateway.py image generate --prompt "a small robot waves, loop it" \
  --output-format gif --frame-count 9 --frame-duration-ms 200

# Edit / inpaint
python3 scripts/gateway.py image edit --prompt "make the sky sunset orange" \
  --image input.png --mask mask.png

# Edit with a transparent markup circle (GPT-Image 2.5+)
python3 scripts/gateway.py image edit --prompt "replace the circled object with a red apple" \
  --image input.png --markup markup.png

# Discover models and aliases
python3 scripts/gateway.py models
python3 scripts/gateway.py resolve nano-banana
```

## Parameters

| Flag | Required | Notes |
| --- | --- | --- |
| `--prompt` | yes | Text description. |
| `--model` | no | Exact model id. Defaults to the configured model, then to the only available one. |
| `--size` | no | `1024x1024`, `1536x1024`, `auto`, or model-specific values. The 1K tier is the cheapest; check `models` for the id. |
| `--n` | no | Image count. Hard limit 128. |
| `--quality` | no | `auto` / `low` / `medium` / `high`; GPT-Image 2.5+ also `xhigh`, `max`. |
| `--output-format` | no | `png` / `jpeg` / `webp`; GPT-Image 2.6 adds `svg`, `gif`. |
| `--background` | no | `transparent` requires `png` or `webp`. |
| `--moderation` | no | `auto` / `low`. |
| `--complexity` | no | GPT-Image 2.6 planning depth `low` / `medium` / `high`. Does not change billing. |
| `--output-compression` | no | 0-100, JPEG/WebP only. |
| `--frame-count` | no | 2-64, GIF only. Must be a non-negative integer. |
| `--frame-duration-ms` | no | 20-2000, GIF only. |
| `--markup` | no | Edit only. Transparent PNG overlay circling the edit region; GPT-Image 2.5+ only. |
| `--group` | no | Route to a specific billing group. |

## Endpoints

- `POST /v1/images/generations` — JSON, synchronous.
- `POST /v1/images/edits` — multipart, field name `image[]`, optional `mask`.

The response carries `data[]` items. Each item holds either `b64_json` or `url`. The CLI decodes base64, downloads URLs, and writes files to `outputs/image/<YYYY-MM-DD>/`. If a download is refused, the original URL is returned in `urls`.

Gemini image models accept `/v1/images/generations` too, with `size` mapped to `imageSize` plus `aspectRatio`. Verified: `2048x2048` returns 2048x2048. GPT-Image 2.6 also accepts explicit pixel sizes; verified `3840x2160` returns 3840x2160.

## Gemini native endpoint

For exact resolution or aspect ratio on `gemini-*-image*`, use `image native`. It calls the Gemini native endpoint and keeps the key in the `Authorization` header.

```bash
# text to image, 1K square
python3 scripts/gateway.py image native --model gemini-3.1-flash-image-preview \
  --prompt "a red apple on a white table" --size 1K --ratio 1:1

# image to image, local file
python3 scripts/gateway.py image native --model gemini-3.1-flash-image-preview \
  --prompt "make the apple green, keep the same composition" \
  --image input.jpg --size 1K --ratio 1:1
```

`--size` takes `1K`, `2K`, `4K`; `--ratio` takes values such as `1:1` or `16:9`. Verified: 1K with 1:1 returns 1024×1024 for both modes.

| Alias | Model | Focus |
| --- | --- | --- |
| Nano Banana Pro | `gemini-3-pro-image-preview` | quality tier |
| Nano Banana 2 | `gemini-3.1-flash-image-preview` | speed tier, supports 8:1, 4:1, 1:4, 1:8 |

The underlying request is `POST /v1beta/models/{model}:generateContent`; references travel as `inlineData` inside `contents[].parts`. Full request bodies and the ratio table are in [references/gemini-native.en.md](references/gemini-native.en.md).

## Output

```json
{"ok":true,"model":"gpt-image-2.6-sunburst-1k","files":["outputs/image/2026-01-01/a-green-apple-1-194002.png"],
 "sizes":["1254x1254"],"requested_size":"1024x1024","urls":[],"created":1794742738,
 "usage":{"total_tokens":2066},"est_cost":0.029,"elapsed_seconds":104.5,
 "model_note":"auto-selected the cheapest of 15 'gpt-image' matches; pass --model to choose",
 "size_note":"requested 1024x1024, got 1254x1254"}
```

- `sizes` holds the real dimensions read from each saved file; `requested_size` is the `--size` you passed. A mismatch adds `size_note`.
- `est_cost` is the fixed per-call price from the catalog; ratio-billed models return `null`.
- `model_note` appears only when `--model` was omitted and the cheapest alias match was auto-selected.
- `usage` and `elapsed_seconds` come from the upstream response and the wall clock.

## Resolution

| Need | Size value | Result |
| --- | --- | --- |
| 1K square | `1024x1024` | 1024x1024 or 1254x1254 |
| 2K square (Gemini) | `2048x2048` | 2048x2048 |
| 4K landscape | `3840x2160` | 3840x2160 |

The 1K tier only renders 1K; asking it for 4K still returns about 1254x1254. The CLI reads the real dimensions from each file and reports them in `sizes`.

`--output-format svg` supports `--n 1` only; the upstream rejects a larger batch. Keep GIF/SVG requests at `n=1` and split batches yourself.

## Formats and transparency

| Capability | Requirement |
| --- | --- |
| `png` / `jpeg` / `webp` | Generally available. |
| Transparent background | Needs `png` or `webp`. Only newer model tiers emit alpha; entry-level tiers reject it. |
| Animated GIF | Generated-image models from the 2.6 tier upward. Requires `--output-format gif` plus `--frame-count` (2-64) and `--frame-duration-ms` (20-2000). |
| SVG output | 2.6 tier upward, generation only. The edits endpoint rejects `svg` and `gif`. |

When a format is rejected with a 400, the selected model tier does not support it. Switch to a newer tier rather than retrying the same model.

Some models accept `background: transparent` without an error and still return an opaque image. Always verify the result instead of trusting the request:

```bash
file outputs/image/<date>/<name>.png     # "RGBA" or "color_type 6" means real alpha
```

An `RGB` result means the flag was ignored. Retry on a different model tier, or post-process the white background locally.

## Editing

`image edit` sends local files as multipart, so inputs do not need to be public. It is the image-to-image path.

| Mode | Flags | What it does |
| --- | --- | --- |
| Image to image | `--image` + `--prompt` | edits the input image: background, style, add or remove objects |
| Inpainting | `--image` + `--mask` | repaints only the masked area, everything else stays |
| Markup | `--image` + `--markup` | a transparent PNG circles the region to change, GPT-Image 2.5 and later |

`--image` is repeatable; up to 16 inputs are accepted. The edits endpoint returns `png` / `jpeg` / `webp` only; `svg` and `gif` are generation-only. The returned image keeps the input framing unless the prompt asks otherwise.

Verified: one local image through `image edit` works on both a GPT-Image model and a Gemini image model, each returning an edited image with the original composition preserved.

## Errors

| Status | Meaning | Action |
| --- | --- | --- |
| 400 | Invalid parameter or unsupported model capability | Fix the flag; check `models`. |
| 401 | Missing or invalid key | Re-run `login`, then `doctor`. |
| 402 | Insufficient quota | Tell the user to top up. |
| 429 | Rate limit or concurrency cap | Back off and retry. |
| 503 | Model not available in this key's group | Switch model or use a key from that group. |
| 5xx | Upstream failure | Retry once, then surface the message verbatim. |
