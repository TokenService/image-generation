# image-generation

**中文** · [English](README.en.md)

由 [New.bi](https://api.new.bi) 提供，专业、稳定、可靠的大模型聚合中转平台。

图片生成和编辑的命令行工具，也可以直接当 agent 技能用。

能做文生图、图生图、掩码改局部、透明背景、动图、SVG。视频、音乐、语音、决策不在这里。

## 安装

放到任意目录即可，用 `python3 scripts/gateway.py` 运行。

## 开始

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
python3 scripts/gateway.py model set gpt-image-2.6-flare
python3 scripts/gateway.py image generate --prompt "a red panda on a bench" --size 1024x1024
```

图片存在技能目录下的 `outputs/image/<日期>/`，不是当前工作目录；`AIGW_OUTPUT_DIR` 可以改。模型缓存放在 `~/.aigw/cache/`，保留 6 小时，`AIGW_STATE_HOME` 可以改。`config.json` 在技能目录里，命令里的相对路径按当前工作目录算。

Gemini 型号要精确控制分辨率或比例时走原生端点，见 [references/gemini-native.md](references/gemini-native.md)。

## 支持的模型

| 系列 | 型号 |
| --- | --- |
| OpenAI GPT-Image | GPT-Image 2.6（Flare、Sunburst）、GPT-Image 2.5（Flare、Sunburst）、GPT-Image 2 |
| Google Gemini | Gemini 3 Pro Image、Gemini 3.1 Flash Image、Gemini 3.1 Flash Lite Image、Gemini 2.5 Flash Image、Nano Banana 2.1 |
| 字节 Seedream | Seedream 5.0 Pro、Seedream 5.0、Seedream 4.5、Seedream 4.0 |
| xAI / Muse | Grok Imagine Image 2.0、Grok Imagine Image、Muse Image |

用 `models` 查可用模型和价格。单次指定用 `--model <id>`；固定默认用 `model set <id>`，它写进项目根目录 `config.json` 的 `model` 字段，也可以直接改这个文件。 `models` 里 `price` 大于 0 是按次固定价，`price` 为 0 且 `ratio` 大于 0 是按倍率计费，两者不能直接比大小。

## 常见搜索词

文生图、AI 画图、AI 生成图片、nano banana 出图、gpt-image 改图、seedream 海报、AI 换背景、AI 抠图、透明底 PNG、局部重绘 inpainting、AI 贴纸、AI 头像、电商主图、产品图、AI 海报、4K 出图、AI 动图 GIF。

## 命令

| 命令 | 做什么 |
| --- | --- |
| `login` | 存密钥，可同时存网关地址和分组。 |
| `config` | 看当前生效的配置，以及每个值从哪来。 |
| `models` | 列出这个密钥能看到的图片模型，带价格。 |
| `model show` / `model set <id>` | 看或设置默认模型。 |
| `resolve <别名>` | 别名换成具体模型 id。 |
| `image generate` | 文生图。 |
| `image edit` | 编辑图片，可带掩码或标记层。 |
| `image native` | Gemini 原生端点，精确控制 1K/2K/4K 与比例，支持图生图。 |
| `doctor` | 检查密钥和连通性。 |

每个命令都输出 JSON。出错时输出 `{"ok": false, "error": {...}}`，退出码非零。

## 密钥

按顺序找，先用找到的：

1. `config.json` 里的 `api_key`
2. `AIGW_IMAGE_API_KEY`
3. `AIGW_API_KEY`
4. `OPENAI_API_KEY`

网关地址同样逐级回退，最后用 `scripts/defaults.json` 里的。

## 文件

```
image-generation/
├── SKILL.md              中文说明，agent 读这个
├── SKILL.en.md           英文说明
├── config.json           密钥和默认模型，login 生成，不进 git
├── references/
│   ├── gemini-native.md  Gemini 原生端点用法
│   └── gemini-native.en.md
└── scripts/
    ├── gateway.py        入口
    ├── models.json       别名和分类规则
    └── defaults.json     默认网关地址和超时
```

细节、参数和实测结果见 [SKILL.md](SKILL.md)。

需要 Python 3.9 及以上。
