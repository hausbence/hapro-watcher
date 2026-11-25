# HardverApró watcher

Checks the searches defined in `config.json` every 30 minutes and sends a push notification through [ntfy.sh](https://ntfy.sh) for each new listing on HardverApró that passes the filters.

## Setup
1. Install the ntfy app on your phone and subscribe to a **secret, hard-to-guess** topic (for example a long random string).
2. In the GitHub repository, go to Settings → Secrets and variables → Actions and add `NTFY_TOPIC` with the topic name as its value.
3. Go to the Actions tab → "HardverApró watcher" → Run workflow. The first run only saves the current listings and sends no notifications.

## Filters (`config.json`)
- `include`: regex the listing title must match (for PS5: `pro`)
- `exclude`: regex that rejects a title (wanted ads, repair services, etc.; the patterns are Hungarian)
- `min_price` / `max_price`: in HUF. Listings without a numeric price (wanted or trade ads) are always skipped.

## Local test
```
python watcher.py --dry-run
```
