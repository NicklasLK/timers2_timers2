import random
import string
from datetime import datetime, timezone, timedelta

from dateutil.parser import isoparse
from boto3.dynamodb.conditions import Key, Attr


def get_system_region_name(table, system_name):
    response = table.query(
        KeyConditionExpression=Key("PK").eq("SYSTEM")
        & Key("SK").eq("SYSTEM#{}".format(system_name)),
    )
    if not len(response.get("Items", [])) == 1:
        raise ValueError()

    item = response["Items"][0]

    return item["region_name"]


def get_system_names(table, system_id):
    response = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq("SYSTEM#{}".format(system_id)),
    )
    if not len(response.get("Items", [])) == 1:
        raise ValueError()

    item = response["Items"][0]

    return item["SK"][7:], item["region_name"]


def get_timer_suffix():
    return "".join(random.sample(string.ascii_letters + string.digits, 10))


def put_timer(
    table,
    *,
    start_time,
    system_name,
    region_name,
    corporation_ticker,
    alliance_ticker,
    standing_type,
    structure_type,
    timer_type,
    replace,
    notes,
    added_by,
    esi_campaign_id=None
):
    item = {
        "PK": "TIMER",
        "SK": "TIMER#{}#{}".format(
            start_time.isoformat(timespec="seconds"),
            get_timer_suffix(),
        ),
        "TTL": int((start_time + timedelta(hours=24)).timestamp()),
        "system_name": system_name,
        "region_name": region_name,
        "corporation_ticker": corporation_ticker,
        "alliance_ticker": alliance_ticker,
        "standing_type": standing_type,
        "structure_type": structure_type,
        "timer_type": timer_type,
        "replace": replace,
        "notes": notes,
        "added_by": added_by,
    }

    if esi_campaign_id:
        item["esi_campaign_id"] = esi_campaign_id

    table.put_item(Item=item, ConditionExpression=Attr("PK").not_exists())


def get_timers(table, only_active=True):
    timers = []

    now = datetime.now(tz=timezone.utc)

    exclusive_start_key = None
    while True:
        kwargs = {"KeyConditionExpression": Key("PK").eq("TIMER")}
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key

        response = table.query(**kwargs)

        for timer in response["Items"]:
            sk_parts = timer["SK"].split("#")
            if len(sk_parts) != 3:
                continue

            timer["start_time"] = isoparse(sk_parts[1])
            if only_active and timer["start_time"] < now - timedelta(hours=1):
                continue

            timers.append(timer)

        exclusive_start_key = response.get("LastEvaluatedKey")
        if not exclusive_start_key:
            break

    return timers
