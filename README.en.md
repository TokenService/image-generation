# image-generation

[中文](README.md) · **English**

Provided by [New.bi](https://api.new.bi), a professional, stable, and reliable AI model aggregation gateway.

Image generation CLI for an AI gateway. Drop it into an agent skills directory or use it as a standalone tool.

- Text-to-image, image-to-image, masked inpainting
- Transparent backgrounds, WebP/JPEG, animated GIF, SVG output
- Model discovery and a pinned default model

See [SKILL.en.md](SKILL.en.md) for full usage and verified behaviour.

## Layout

```
image-generation/
├── SKILL.md              Chinese skill doc (the file agents read by default)
├── SKILL.en.md           English skill doc
├── README.md
├── README.en.md
├── config.json           credential and default model, created by login / model, never committed
├── references/
│   ├── gemini-native.md  Gemini native endpoint
│   └── gemini-native.en.md
└── scripts/
    ├── gateway.py        single entry point, image code only
    ├── models.json       alias table and category rules
    └── defaults.json     packaged gateway address and timeout
```

## Quick start

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
python3 scripts/gateway.py model set gpt-image-2.6-flare
python3 scripts/gateway.py image generate --prompt "a red panda on a bench" --size 1024x1024
```

Files land in `outputs/image/<YYYY-MM-DD>/` inside the skill directory, not your current directory; override with `AIGW_OUTPUT_DIR`. The model cache lives in `~/.aigw/cache/` for six hours; relocate it with `AIGW_STATE_HOME`. `config.json` sits in the skill directory, while relative paths in commands resolve from your working directory.

For exact resolution or aspect ratio on Gemini models, use the native endpoint: [references/gemini-native.en.md](references/gemini-native.en.md).

## Supported models

| Family | Model |
| --- | --- |
| OpenAI GPT-Image | GPT-Image 2.6 (Flare, Sunburst), GPT-Image 2.5 (Flare, Sunburst), GPT-Image 2 |
| Google Gemini | Gemini 3 Pro Image, Gemini 3.1 Flash Image, Gemini 3.1 Flash Lite Image, Gemini 2.5 Flash Image, Nano Banana 2.1 |
| ByteDance Seedream | Seedream 5.0 Pro, Seedream 5.0, Seedream 4.5, Seedream 4.0 |
| xAI / Muse | Grok Imagine Image 2.0, Grok Imagine Image, Muse Image |

Run `models` for the available ids and prices. Pass `--model <id>` for one call, or `model set <id>` to write `model` into `config.json`; editing that file works too. In `models`, `price` above 0 is a fixed per-call price; `price` 0 with `ratio` above 0 bills by ratio. The two are not directly comparable.

## Search terms

text to image, AI image generator, nano banana, gpt-image, seedream, background removal, transparent PNG, inpainting, AI sticker, AI avatar, e-commerce product shot, AI poster, 4K image, animated GIF.

## Commands

| Command | Purpose |
| --- | --- |
| `login` | Store a credential, optionally with `--base-url` and `--group`. |
| `config` | Show resolved settings and where each value came from. |
| `models` | List image models visible to this key, with price and billing mode. |
| `model show` / `model set <id>` | Show or pin the default model. |
| `resolve <alias>` | Map an alias to concrete model ids. |
| `image generate` | Text to image. |
| `image edit` | Multipart image editing with optional mask and markup. |
| `image native` | Gemini native endpoint with exact 1K/2K/4K and ratio control, including image-to-image. |
| `doctor` | Verify the credential and connectivity. |

## Credentials

Resolution order, first match wins:

1. `api_key` in `config.json`
2. `AIGW_IMAGE_API_KEY`
3. `AIGW_API_KEY`
4. `OPENAI_API_KEY`

`base_url` follows the same chain and falls back to `scripts/defaults.json`. Every command prints JSON; failures return `{"ok": false, "error": {...}}` and exit non-zero.

## Requirements

Python 3.9 or newer. No third-party packages.
