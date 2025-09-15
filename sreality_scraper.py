"""Simple scraper for SReality.cz listings.

This module fetches listings from SReality for a given query URL
and sends an email whenever new listings are found.  Previously
seen listings are stored in a local JSON file so that subsequent
runs only notify about new results.

The scraper uses only Python's standard library in order to work in
restricted environments where installing extra packages is not
possible.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable, List, Set
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import smtplib


@dataclass
class Listing:
    """Represents a single real-estate listing."""

    id: str
    title: str
    locality: str
    price: str
    url: str


class SRealityScraper:
    """Scrape listings from SReality and keep track of seen items."""

    def __init__(self, query_url: str, storage_path: str = "seen.json"):
        self.query_url = query_url
        self.storage_path = storage_path

    # ------------------------------------------------------------------
    # Fetching and parsing
    # ------------------------------------------------------------------
    def fetch_listings(self) -> List[Listing]:
        """Fetch listings from the SReality API.

        The ``query_url`` should point to the JSON API endpoint provided by
        SReality.  The method returns a list of :class:`Listing` objects.
        """

        req = Request(self.query_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as resp:
            data = json.load(resp)

        estates = data.get("_embedded", {}).get("estates", [])
        listings: List[Listing] = []
        for item in estates:
            estate_id = str(item.get("hash_id") or item.get("id"))
            name = item.get("name", "")
            locality = item.get("locality", "")
            price_info = item.get("price_czk", {})
            price = str(
                price_info.get("value_raw")
                or price_info.get("value")
                or price_info.get("txt")
                or ""
            )
            link = item.get("_links", {}).get("self", {}).get("href", "")
            if link.startswith("/"):
                link = "https://www.sreality.cz" + link
            listings.append(Listing(estate_id, name, locality, price, link))
        return listings

    # ------------------------------------------------------------------
    # State handling
    # ------------------------------------------------------------------
    def _load_seen(self) -> Set[str]:
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    return set(str(x) for x in data)
                except json.JSONDecodeError:
                    return set()
        return set()

    def _save_seen(self, ids: Iterable[str]) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f, ensure_ascii=False, indent=2)

    def find_new(self, listings: Iterable[Listing]) -> List[Listing]:
        seen = self._load_seen()
        new_items = [l for l in listings if l.id not in seen]
        if new_items:
            seen.update(l.id for l in new_items)
            self._save_seen(seen)
        return new_items

    # ------------------------------------------------------------------
    # Email notification
    # ------------------------------------------------------------------
    @staticmethod
    def send_email(
        listings: Iterable[Listing],
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        to_addr: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ) -> None:
        """Send an email about new listings.

        Parameters correspond to typical SMTP configuration.  The email body
        contains a simple text listing of the new items.
        """

        msg = EmailMessage()
        msg["Subject"] = f"New SReality listings ({len(listings)})"
        msg["From"] = from_addr
        msg["To"] = to_addr
        lines = []
        for l in listings:
            line = f"{l.title} — {l.locality} — {l.price} — {l.url}"
            lines.append(line)
        msg.set_content("\n".join(lines))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                try:
                    server.starttls()
                except smtplib.SMTPException:
                    pass
            if username and password:
                server.login(username, password)
            server.send_message(msg)


# ----------------------------------------------------------------------
# Command line interface
# ----------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape SReality and send email notifications")
    parser.add_argument("--query", required=True, help="SReality API query URL")
    parser.add_argument("--storage", default="seen.json", help="Path to JSON file storing seen listing IDs")
    parser.add_argument("--smtp-host", required=True, help="SMTP server host")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP server port")
    parser.add_argument("--smtp-user", help="SMTP username")
    parser.add_argument("--smtp-password", help="SMTP password")
    parser.add_argument("--email-from", required=True, help="From address")
    parser.add_argument("--email-to", required=True, help="Recipient address")
    parser.add_argument("--no-tls", action="store_true", help="Disable TLS for SMTP")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scraper = SRealityScraper(args.query, args.storage)
    try:
        listings = scraper.fetch_listings()
    except (URLError, HTTPError) as exc:
        raise SystemExit(f"Failed to fetch listings: {exc}")
    new_items = scraper.find_new(listings)
    if not new_items:
        print("No new listings found.")
        return
    SRealityScraper.send_email(
        new_items,
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        from_addr=args.email_from,
        to_addr=args.email_to,
        username=args.smtp_user,
        password=args.smtp_password,
        use_tls=not args.no_tls,
    )
    print(f"Notified about {len(new_items)} new listings.")


if __name__ == "__main__":
    main()
