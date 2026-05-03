# Fly.io Deployment

## 1. Login

```bash
fly auth login
```

## 2. Pick the app name

The current `fly.toml` uses:

```toml
app = "compliance-ai-news"
```

Fly app names are global. If this name is already taken, change both:

```toml
app = "your-unique-ai-news-name"
SCHEDULER_API_BASE_URL = "http://your-unique-ai-news-name.internal:8080"
```

## 3. Create the app

```bash
fly apps create compliance-ai-news
```

If you changed the app name in `fly.toml`, use that name in the command.

## 4. Create Postgres

```bash
fly postgres create --name compliance-ai-news-db
fly postgres attach --app compliance-ai-news compliance-ai-news-db
```

`fly postgres attach` sets `DATABASE_URL` automatically.

## 5. Set secrets

Do not upload `.env`. Set production secrets directly in Fly:

```bash
fly secrets set \
  REDIS_URL="redis://unused:6379/0" \
  LLM_ENABLED="true" \
  LLM_API_KEY="YOUR_LLM_KEY" \
  LLM_BASE_URL="YOUR_LLM_BASE_URL" \
  LLM_MODEL="YOUR_MODEL" \
  SERPAPI_API_KEY="YOUR_SERPAPI_KEY" \
  TAVILY_API_KEY="YOUR_TAVILY_KEY" \
  SLACK_BOT_TOKEN="YOUR_SLACK_BOT_TOKEN" \
  SLACK_SIGNING_SECRET="YOUR_SLACK_SIGNING_SECRET" \
  SLACK_APPROVAL_CHANNEL_ID="YOUR_SLACK_CHANNEL_ID" \
  --app compliance-ai-news
```

Redis is not actively used yet.

## 6. Deploy

```bash
fly deploy --app compliance-ai-news
```

## 7. Verify

```bash
fly status --app compliance-ai-news
fly logs --app compliance-ai-news
curl https://compliance-ai-news.fly.dev/health
```

## 8. Update Slack URLs

After deployment, replace the ngrok URLs in Slack with:

```text
https://compliance-ai-news.fly.dev/webhooks/slack/events
https://compliance-ai-news.fly.dev/webhooks/slack/actions
https://compliance-ai-news.fly.dev/webhooks/slack/commands
```

If you changed the app name, replace `ai-news` in those URLs.

## 9. Scheduler

The scheduler runs every 24 hours because `fly.toml` sets:

```toml
SCHEDULER_INTERVAL_MINUTES = "1440"
```
