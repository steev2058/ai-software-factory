# OpenRouter Reusable n8n Node Config

Use an **HTTP Request** node:

- Method: `POST`
- URL: `https://openrouter.ai/api/v1/chat/completions`
- Authentication: None (manual headers)
- Headers:
  - `Authorization: Bearer {{$env.OPENROUTER_API_KEY}}`
  - `Content-Type: application/json`
  - `HTTP-Referer: https://your-domain-or-vps`
  - `X-Title: AI Software Factory`

Body (JSON):

```json
{
  "model": "={{$json.model}}",
  "messages": "={{$json.messages}}",
  "temperature": 0.2
}
```

## Fallback handling pattern

If request fails:
1. Set `model = fallback`
2. Retry once
3. If fails again, use next in `fallback_chain`
