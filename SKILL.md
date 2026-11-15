---
name: image-generation
description: 通过统一 AI 网关生成或编辑图片，可选 GPT-Image、Gemini / Nano Banana、Seedream、Muse、Grok Imagine 等模型。支持文生图、图生图、局部重绘、透明背景、动图、SVG。 平台：New.bi（https://api.new.bi），专业、稳定、可靠的大模型聚合中转平台。
metadata:
  version: 1.1.0
---

**中文** · [English](SKILL.en.md)

# 图片生成

同步接口，提交后直接返回图片，没有任务轮询。

## 什么时候用

- 文生图、图生图、用掩码改局部。
- 要透明背景、WebP/JPEG、动图或 SVG。
- 用户指定了模型，或指定了尺寸、质量、格式。

## 什么时候不用

- 视频、音乐、语音、决策，这些不在这个工具里。
- 想先比价，跑 `models`。

## 准备

密钥按顺序查找，先用找到的：

1. 项目根目录 `config.json` 里的 `api_key`
2. `AIGW_IMAGE_API_KEY`
3. `AIGW_API_KEY`
4. `OPENAI_API_KEY`

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
```

`login --base-url` 会把网关地址写进 `config.json`。地址按 `config.json` → `AIGW_IMAGE_BASE_URL` → `AIGW_BASE_URL` → `scripts/defaults.json` 的顺序取。

## 能用哪些模型

按系列分：

| 系列 | 型号 | 常见用途 |
| --- | --- | --- |
| OpenAI GPT-Image | GPT-Image 2.6（Flare、Sunburst）、GPT-Image 2.5（Flare、Sunburst）、GPT-Image 2 | 指令理解、改图、图里写字 |
| Google Gemini | Gemini 3 Pro Image、Gemini 3.1 Flash Image、Gemini 3.1 Flash Lite Image、Gemini 2.5 Flash Image、Nano Banana 2.1 | 参考图编辑、写实、多图合成 |
| 字节 Seedream | Seedream 5.0 Pro、Seedream 5.0、Seedream 4.5、Seedream 4.0 | 海报、电商图、多参考 |
| xAI Grok Imagine | Grok Imagine Image 2.0、Grok Imagine Image | 快速出图 |
| Muse | Muse Image | 通用备选 |

用 `models` 查可用模型和价格。单次指定用 `--model <id>`；固定默认用 `model set <id>`，它写进项目根目录 `config.json` 的 `model` 字段，也可以直接改这个文件。 `models` 里 `price` 大于 0 是按次固定价，`price` 为 0 且 `ratio` 大于 0 是按倍率计费，两者不能直接比大小。

Gemini 和 Seedream 的型号也走 `/v1/images/generations`，`size` 由网关换算成各家自己的参数。

## 固定默认模型

```bash
python3 scripts/gateway.py model set gpt-image-2.6-flare
python3 scripts/gateway.py model show
```

设置后生成和编辑不带 `--model` 都用它，`--model` 仍可临时覆盖。值写在项目根目录 `config.json` 的 `model` 字段，手改这个文件也一样。 `model show` 会告诉你这个模型在不在当前密钥的目录里。

## 生成

```bash
python3 scripts/gateway.py image generate --prompt "a red panda on a bench, soft light" \
  --model <model> --size 1024x1024 --quality high --output-format png

# 一次四张
python3 scripts/gateway.py image generate --prompt "sticker sheet" --n 4

# 透明 PNG，需要较新的模型层级
python3 scripts/gateway.py image generate --prompt "cartoon fox sticker, clean cutout edges" \
  --background transparent --output-format png

# 动图
python3 scripts/gateway.py image generate --prompt "a small robot waves, loop it" \
  --output-format gif --frame-count 9 --frame-duration-ms 200
```

## 编辑

`image edit` 把本地图交给模型，按指令改图，也就是常说的图生图。三种用法：

| 方式 | 参数 | 说明 |
| --- | --- | --- |
| 图生图 | `--image` + `--prompt` | 直接基于输入图改内容，比如换背景、换风格、加或去掉物体 |
| 局部重绘 | `--image` + `--mask` | 用掩码指定重绘区域，其余部分保持不动 |
| 标记圈选 | `--image` + `--markup` | 透明 PNG 圈出要改的位置，GPT-Image 2.5 及以上支持 |

```bash
# 图生图：换背景
python3 scripts/gateway.py image edit --prompt "put the subject on a beach at sunset" \
  --image input.png

# 局部重绘
python3 scripts/gateway.py image edit --prompt "make the sky sunset orange" \
  --image input.png --mask mask.png

# 用透明层圈出要改的地方，GPT-Image 2.5+
python3 scripts/gateway.py image edit --prompt "replace the circled object with a red apple" \
  --image input.png --markup markup.png
```

`--image` 可重复，最多 16 张，可以同时给多张参考图。编辑端点只支持 `png`、`jpeg`、`webp` 输出，SVG 和动图只能生成不能编辑。

本地文件直接上传，不需要先传到公网。

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--prompt` | 是 | 画面描述。 |
| `--model` | 否 | 模型 id。先用配置文件里的，再退到目录里唯一的一个。 |
| `--size` | 否 | `1024x1024`、`1536x1024`、`auto` 或模型支持的值。价格最低的是 1K 档，具体型号看 `models`。 |
| `--n` | 否 | 张数，最多 128。 |
| `--quality` | 否 | `auto` / `low` / `medium` / `high`；2.5 以上还有 `xhigh`、`max`。 |
| `--output-format` | 否 | `png` / `jpeg` / `webp`；2.6 增加 `svg`、`gif`。 |
| `--background` | 否 | 透明要配 `png` 或 `webp`。 |
| `--moderation` | 否 | `auto` / `low`。 |
| `--complexity` | 否 | 2.6 的规划深度，`low` / `medium` / `high`，不影响计费。 |
| `--output-compression` | 否 | 0 到 100，只对 JPEG/WebP 生效。 |
| `--frame-count` | 否 | 2 到 64，只对动图生效。 |
| `--frame-duration-ms` | 否 | 20 到 2000，只对动图生效。 |
| `--markup` | 否 | 只在编辑时用，GPT-Image 2.5 及以上。 |
| `--group` | 否 | 指定计费分组。 |

## 接口

- `POST /v1/images/generations`，JSON，同步返回。
- `POST /v1/images/edits`，multipart，图片字段名 `image[]`，可选 `mask`。

返回 `data[]`，每项是 `b64_json` 或 `url`。命令行会解码或下载，存到 `outputs/image/<日期>/`。下载被拒时，原始 URL 放在 `urls` 里返回。

Gemini 图片模型也走这个接口，`size` 会转成 `imageSize` 加 `aspectRatio`，实测 `2048x2048` 返回 2048x2048。GPT-Image 2.6 支持直接写像素，实测 `3840x2160` 返回 3840x2160。

## Gemini 原生端点

`gemini-*-image*` 要精确控制分辨率或比例时，用 `image native`。它走 Gemini 原生接口，密钥放在 `Authorization` 头里。

```bash
# 文生图，1K 方图
python3 scripts/gateway.py image native --model gemini-3.1-flash-image-preview \
  --prompt "a red apple on a white table" --size 1K --ratio 1:1

# 图生图，本地图片直接传
python3 scripts/gateway.py image native --model gemini-3.1-flash-image-preview \
  --prompt "make the apple green, keep the same composition" \
  --image input.jpg --size 1K --ratio 1:1
```

`--size` 取 `1K`、`2K`、`4K`，`--ratio` 取 `1:1`、`16:9` 这类比例。实测 1K + 1:1 返回 1024×1024，文生图和图生图都一样。

| 别名 | 型号 | 取向 |
| --- | --- | --- |
| 香蕉 Pro | `gemini-3-pro-image-preview` | 画质档 |
| 香蕉 2 | `gemini-3.1-flash-image-preview` | 速度档，支持 8:1、4:1、1:4、1:8 |

底层请求是 `POST /v1beta/models/{model}:generateContent`，参考图以 `inlineData` 放进 `contents[].parts`。完整请求体、比例与像素对照表见 [references/gemini-native.md](references/gemini-native.md)。

## 输出

```json
{"ok":true,"model":"gpt-image-2.6-sunburst-1k","files":["outputs/image/2026-01-01/a-green-apple-1-194002.png"],
 "sizes":["1254x1254"],"requested_size":"1024x1024","urls":[],"created":1794742738,
 "usage":{"total_tokens":2066},"est_cost":0.029,"elapsed_seconds":104.5,
 "model_note":"auto-selected the cheapest of 15 'gpt-image' matches; pass --model to choose",
 "size_note":"requested 1024x1024, got 1254x1254"}
```

- `sizes` 是落盘后从文件头读出来的真实宽高，`requested_size` 是传进来的 `--size`。两者不一致时会多一个 `size_note`。
- `est_cost` 取自模型目录里的单次固定价；按倍率计费的模型给 `null`。
- `model_note` 只在没传 `--model`、按别名自动选了最便宜一个时出现。
- `usage` 和 `elapsed_seconds` 是上游返回的用量与实际耗时。

## 尺寸

| 想要 | 传 | 实测 |
| --- | --- | --- |
| 1K 方图 | `1024x1024` | 1024x1024 或 1254x1254 |
| 2K 方图（Gemini） | `2048x2048` | 2048x2048 |
| 4K 横图 | `3840x2160` | 3840x2160 |

1K 档的模型只出 1K，向它请求 4K 实际还是 1254x1254 左右。命令行会读产物尺寸放进 `sizes`，以那个为准。

SVG 只支持 `--n 1`，传多了上游报错。动图和 SVG 都按单张请求，批量自己拆。

## 格式与透明

| 能力 | 条件 |
| --- | --- |
| png / jpeg / webp | 都能用。 |
| 透明背景 | 要 png 或 webp，且模型层级够新。入门档会拒绝。 |
| 动图 | 2.6 及以上的生成模型，要 `--output-format gif` 加帧数和帧时长。 |
| SVG | 2.6 及以上，只能生成，不能编辑。 |

报 400 说格式不支持，就是模型层级不够，换个新的，别用同一个模型重试。

有的模型收下 `background: transparent` 却不报错，返回的图还是不透明。查一下产物：

```bash
file outputs/image/<日期>/<文件名>.png
```

出现 `RGBA` 或 `color_type 6` 才是真透明。`RGB` 说明参数被忽略，换模型或自己抠图。

## 错误

| 状态 | 原因 | 怎么办 |
| --- | --- | --- |
| 400 | 参数不对，或模型不支持这项能力 | 改参数，用 `models` 确认。 |
| 401 | 密钥缺失或无效 | 重新 `login`，跑 `doctor`。 |
| 402 | 余额不足 | 充值。 |
| 429 | 限流或并发到顶 | 等一会重试。 |
| 503 | 这个分组的密钥用不了该模型 | 换模型或换密钥。 |
| 5xx | 上游故障 | 重试一次，还不行就把报错原样贴出来。 |
