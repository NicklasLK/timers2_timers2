import json
import os
import traceback
from datetime import timezone

import boto3
import httpx
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dateutil.parser import isoparse

from timers2.utils import get_system_names, get_timers, put_timer

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

EVENT_TYPE_MAP = {
    "station_defense": "STATION",
    "ihub_defense": "I_HUB",
    "tcu_defense": "TCU",
}


def handler(event, context):
    response = httpx.get("https://esi.evetech.net/v1/sovereignty/campaigns")
    response.raise_for_status()

    data = response.json()

    existing_campaigns = {
        esi_campaign_id
        for timer in get_timers(table, only_active=False, include_secret=True)
        if (esi_campaign_id := timer.get("esi_campaign_id"))
    }

    alliance_tickers = {}
    alliances = {
        standing["SK"][9:]: standing["standing_type"]
        for standing in table.query(
            KeyConditionExpression=(
                Key("PK").eq("STANDING") & Key("SK").begins_with("ALLIANCE#")
            )
        )["Items"]
    }

    with httpx.Client() as client:
        for item in data:
            if item["campaign_id"] in existing_campaigns:
                continue

            if item["event_type"] not in EVENT_TYPE_MAP:
                continue

            if item["defender_id"] in alliance_tickers:
                alliance_ticker = alliance_tickers[item["defender_id"]]
            else:
                try:
                    alliance_response = client.get(
                        "https://esi.evetech.net/v4/alliances/{}".format(
                            item["defender_id"]
                        )
                    )
                    alliance_response.raise_for_status()
                    alliance_ticker = alliance_response.json().get("ticker")
                    alliance_tickers[item["defender_id"]] = alliance_ticker
                except (ValueError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
                    traceback.print_exc()
                    continue

            if alliance_ticker not in alliances:
                continue

            try:
                system_name, region_name = get_system_names(
                    table, item["solar_system_id"]
                )
            except (ValueError, ClientError) as e:
                traceback.print_exc()
                continue

            if not alliance_ticker:
                continue

            start_time = isoparse(item["start_time"])
            if start_time.tzinfo is None or not start_time.tzinfo.utcoffset(start_time):
                start_time = start_time.replace(tzinfo=timezone.utc)
            else:
                start_time = start_time.astimezone(timezone.utc)

            put_timer(
                table,
                start_time=start_time,
                system_name=system_name,
                region_name=region_name,
                corporation_ticker="AUTO",
                alliance_ticker=alliance_ticker,
                standing_type=alliances[alliance_ticker],
                structure_type=EVENT_TYPE_MAP.get(item["event_type"], "Unknown"),
                timer_type="Unknown",
                replace="Not applicable",
                notes="",
                added_by="ESI",
                esi_campaign_id=item["campaign_id"],
            )
