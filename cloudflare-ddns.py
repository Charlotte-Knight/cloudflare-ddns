from cloudflare import Cloudflare
import logging
import requests
import time
from rich.logging import RichHandler
from rich.traceback import install
import os

install()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("cloudflare-ddns")


def get_records(client, zone_id):
    logger.debug("Fetching DNS records for zone %s:", zone_id)
    records = client.dns.records.list(zone_id=zone_id, type="A").result
    max_name_len = max(len(record.name) for record in records) if records else 0
    for record in records:
        logger.debug("  - %s: %s", record.name.ljust(max_name_len), record.content)
    return records


def get_public_ip(ip=None):
    logger.debug("Fetching public IP address")
    response = requests.get("https://api.ipify.org")
    response.raise_for_status()
    logger.debug(" Public IP address is %s", response.text)
    if ip and response.text != ip:
        logger.info("Public IP changed from %s to %s", ip, response.text)
    return response.text


def update_record(record, client, zone_id, ip):
    logger.info(" Updating record %s from %s to %s", record.name, record.content, ip)
    client.dns.records.edit(
        zone_id=zone_id,
        dns_record_id=record.id,
        name=record.name,
        type=record.type,
        content=ip,
    )


def check_update(client, zone_id, interval, ip=None):
    ip = get_public_ip(ip)
    records = get_records(client, zone_id)

    for r in records:
        if r.content != ip:
            update_record(r, client, zone_id, ip)
    logger.info("Records are up to date. Sleeping for %d seconds.", interval)
    time.sleep(interval)
    return ip


def main():
    api_token = os.getenv("API_TOKEN")
    zone_id = os.getenv("ZONE_ID")
    interval = int(os.getenv("REFRESH_INTERVAL", "60"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    client = Cloudflare(api_token=api_token)

    logger.setLevel(logging.DEBUG)
    ip = check_update(client, zone_id, interval)
    if not DEBUG:
        logger.setLevel(logging.INFO)

    while True:
        ip = check_update(client, zone_id, interval, ip)


if __name__ == "__main__":
    main()
