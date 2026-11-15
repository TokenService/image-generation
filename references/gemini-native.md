# Gemini 原生端点

`gemini-*-image*` 也能走 `/v1/images/generations`，但 `size` 由网关换算。要精确控制 `imageSize`（1K / 2K / 4K）和 `aspectRatio`，用原生端点。

密钥放在请求头里。

## 请求

```
POST /v1beta/models/{model}:generateContent
Authorization: Bearer {api_key}
Content-Type: application/json
```

也支持 `x-goog-api-key` 头。不要用 `?key=`。

## 文生图

```bash
curl "https://api.new.bi/v1beta/models/gemini-3.1-flash-image-preview:generateContent" \
  -H "Authorization: Bearer sk-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{ "parts": [{ "text": "a red panda on a bench" }] }],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"],
      "imageConfig": { "imageSize": "2K", "aspectRatio": "16:9" }
    }
  }'
```

## 图生图

Gemini 原生没有单独的编辑端点，参考图作为 `inlineData` 放在同一个 `contents[].parts` 里，和提示词一起发：

```bash
curl "https://api.new.bi/v1beta/models/gemini-3.1-flash-image-preview:generateContent" \
  -H "Authorization: Bearer sk-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [
        { "text": "make the apple green, keep the same composition" },
        { "inlineData": { "mimeType": "image/png", "data": "<BASE64>" } }
      ]
    }],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"],
      "imageConfig": { "imageSize": "1K", "aspectRatio": "1:1" }
    }
  }'
```

可以放多张参考图，每张一个 `inlineData` part。`mimeType` 用 `image/png`、`image/jpeg`、`image/webp`。

## 响应

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          { "inlineData": { "mimeType": "image/jpeg", "data": "<BASE64>" } }
        ]
      }
    }
  ]
}
```

图片在带 `inlineData` 的 part 里，`data` 是 base64。可以有多张，逐个取。

## 型号

| 别名 | 型号 | 取向 |
| --- | --- | --- |
| 香蕉 Pro | `gemini-3-pro-image-preview` | 画质档，适合成品 |
| 香蕉 2 | `gemini-3.1-flash-image-preview` | 速度档，额外支持 8:1、4:1、1:4、1:8 |

## 比例与像素

| 比例 | 1K | 2K | 4K |
| --- | --- | --- | --- |
| 1:1 | 1024×1024 | 2048×2048 | 4096×4096 |
| 16:9 | 1376×768 | 2752×1536 | 5504×3072 |
| 9:16 | 768×1376 | 1536×2752 | 3072×5504 |
| 4:3 | 1200×896 | 2400×1792 | 4800×3584 |
| 3:4 | 896×1200 | 1792×2400 | 3584×4800 |
| 3:2 | 1264×848 | 2528×1696 | 5056×3392 |
| 2:3 | 848×1264 | 1696×2528 | 3392×5056 |
| 5:4 | 1152×928 | 2304×1856 | 4608×3712 |
| 4:5 | 928×1152 | 1856×2304 | 3712×4608 |
| 21:9 | 1584×672 | 3168×1344 | 6336×2688 |

超宽比例只有香蕉 2 支持。1K 下：8:1 是 2928×352，4:1 是 2064×512，1:4 是 512×2064，1:8 是 352×2928；2K、4K 分别按 ×2、×4 放大。

## 用命令行调用

`image native` 发送上面两种请求，密钥走 `Authorization` 头：

```bash
# 文生图
python3 scripts/gateway.py image native \
  --model gemini-3.1-flash-image-preview \
  --prompt "a red apple on a white table" \
  --size 1K --ratio 1:1

# 图生图，本地图片直接传
python3 scripts/gateway.py image native \
  --model gemini-3.1-flash-image-preview \
  --prompt "make the apple green, keep the same composition" \
  --image input.jpg --size 1K --ratio 1:1
```

`--size` 取 `1K`、`2K`、`4K`，`--ratio` 取上面的比例。实测 1K + 1:1 返回 1024×1024，文生图和图生图都正常。

需要手动发请求时用上面的 curl，其余用 `image native`。
