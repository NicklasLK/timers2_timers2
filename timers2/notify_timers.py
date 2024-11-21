import logging
import os
from datetime import datetime, timedelta, timezone

import boto3
import httpx
from boto3.dynamodb.conditions import Attr

from .utils import get_timers

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
logger = logging.getLogger(__name__)
DISCORD_WEBHOOK = os.environ["NOTIFY_DISCORD_WEBHOOK"]


def send_message(content):
    try:
        resp = httpx.post(
            DISCORD_WEBHOOK,
            json={
                "username": "Timers2",
                "content": content,
                "allowed_mentions": {"parse": ["everyone"]},
            },
        )
        print(resp.text)
        resp.raise_for_status()
    except:
        logger.error("Failed to send message on webhook", exc_info=True)


def handler(event, context):
    timers = get_timers(table, only_active=False, include_secret=True)

    now = datetime.now(tz=timezone.utc)
    for timer in timers:
        if timer["structure_type"] != "ORBITAL_SKYHOOK":
            continue

        if timer["start_time"] - timedelta(hours=1) <= now and not timer.get(
            "notified_1h"
        ):
            send_message(
                "@here {} Skyhook timer in {} at {} expires within 1 hour (notes: {})".format(
                    timer["standing_type"],
                    timer["system_name"],
                    timer["start_time"],
                    timer["notes"] if timer["notes"] else "None",
                )
            )
            table.update_item(
                Key={"PK": timer["PK"], "SK": timer["SK"]},
                UpdateExpression="SET notified_1h = :true",
                ExpressionAttributeValues={":true": True},
                ConditionExpression=Attr("PK").exists(),
            )

        if timer["start_time"] - timedelta(minutes=5) <= now and not timer.get(
            "notified_5m"
        ):
            send_message(
                "@here {} Skyhook timer in {} at {} expires within 5 minutes (notes: {})".format(
                    timer["standing_type"],
                    timer["system_name"],
                    timer["start_time"],
                    timer["notes"] if timer["notes"] else "None",
                )
            )
            table.update_item(
                Key={"PK": timer["PK"], "SK": timer["SK"]},
                UpdateExpression="SET notified_5m = :true",
                ExpressionAttributeValues={":true": True},
                ConditionExpression=Attr("PK").exists(),
            )


if __name__ == "__main__":
    handler(None, None)
