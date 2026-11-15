# Gemini native endpoint

`gemini-*-image*` models also work through `/v1/images/generations`, but the gateway maps `size`. Use the native endpoint when you need exact `imageSize` (1K / 2K / 4K) and `aspectRatio`.

Send the key in the request header.

## Request

```
POST /v1beta/models/{model}:generateContent
Authorization: Bearer {api_key}
Content-Type: application/json
```

`x-goog-api-key` also works. Do not use `?key=`.

## Text to image

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

## Image to image

Gemini has no separate edit endpoint natively. Reference images go into the same `contents[].parts` as `inlineData`, next to the prompt:

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

Multiple references are allowed, one `inlineData` part each. Use `image/png`, `image/jpeg`, or `image/webp`.

## Response

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

Images sit in parts carrying `inlineData`; `data` is base64. A reply can hold more than one image.

## Models

| Alias | Model | Focus |
| --- | --- | --- |
| Nano Banana Pro | `gemini-3-pro-image-preview` | quality tier, final output |
| Nano Banana 2 | `gemini-3.1-flash-image-preview` | speed tier, also supports 8:1, 4:1, 1:4, 1:8 |

## Ratios and pixels

| Ratio | 1K | 2K | 4K |
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

Ultra-wide ratios are Nano Banana 2 only. At 1K: 8:1 is 2928×352, 4:1 is 2064×512, 1:4 is 512×2064, 1:8 is 352×2928. 2K and 4K scale by ×2 and ×4.

## From the CLI

`image native` sends both request shapes above and keeps the key in the `Authorization` header:

```bash
# text to image
python3 scripts/gateway.py image native \
  --model gemini-3.1-flash-image-preview \
  --prompt "a red apple on a white table" \
  --size 1K --ratio 1:1

# image to image, local file
python3 scripts/gateway.py image native \
  --model gemini-3.1-flash-image-preview \
  --prompt "make the apple green, keep the same composition" \
  --image input.jpg --size 1K --ratio 1:1
```

`--size` takes `1K`, `2K`, `4K`; `--ratio` takes the ratios above. Verified: 1K with 1:1 returns 1024×1024 for both text-to-image and image-to-image.

Use the curl above only for hand-built requests; otherwise use `image native`.
