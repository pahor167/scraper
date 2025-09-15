# SReality Scraper

This repository contains a small Python script that watches the Czech real estate portal [sreality.cz](https://www.sreality.cz/) for new listings.  It uses the site's JSON API and sends an email whenever new items matching a search query appear.

The script keeps track of previously seen listing IDs in a JSON file (``seen.json`` by default) so that repeated runs only notify about newly added properties.

## Usage

```bash
python sreality_scraper.py \
  --query "<SREALITY_API_URL>" \
  --smtp-host smtp.example.com \
  --smtp-port 587 \
  --email-from sender@example.com \
  --email-to recipient@example.com \
  --smtp-user user --smtp-password pass
```

The ``--query`` parameter must be a URL to the SReality JSON API for the desired search.  All other options configure the SMTP server used for sending notifications.  The script only relies on the Python standard library, making it suitable for restricted environments.

Run the command periodically, for example via ``cron``, to keep getting alerts about newly posted properties.
