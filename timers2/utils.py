import random
import string
from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Attr, Key
from dateutil.parser import isoparse

STRUCTURE_TYPES = {
    "I_HUB": "I-hub",
    "POCO": "PoCo",
    "TOWER": "Tower",
    "TCU": "TCU",
    "OTHER_UNKNOWN": "Other/Unknown",
    "ATHANOR": "Athanor",
    "ASTRAHAUS": "Astrahaus",
    "RAITARU": "Raitaru",
    "AZBEL": "Azbel",
    "FORTIZAR": "Fortizar",
    "TATARA": "Tatara",
    "SOTIYO": "Sotiyo",
    "KEEPSTAR": "Keepstar",
    "ANSIBLEX": "Ansiblex",
    "ORBITAL_SKYHOOK": "Orbital Skyhook",
}


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

    if start_time.tzinfo is None or not start_time.tzinfo.utcoffset(start_time):
        start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time = start_time.astimezone(timezone.utc)

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


def is_timer_secret(timer):
    return timer["structure_type"] == "ORBITAL_SKYHOOK"


def get_timers(table, *, only_active=True, include_secret=False):
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

            if not include_secret and is_timer_secret(timer):
                continue

            timer["structure_type_name"] = STRUCTURE_TYPES[timer["structure_type"]]

            timers.append(timer)

        exclusive_start_key = response.get("LastEvaluatedKey")
        if not exclusive_start_key:
            break

    return timers


def get_standings(table):
    standings = []

    exclusive_start_key = None
    while True:
        kwargs = {"KeyConditionExpression": Key("PK").eq("STANDING")}
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key

        response = table.query(**kwargs)

        for standing in response["Items"]:
            standing["ticker"] = standing["SK"][9:]
            standings.append(standing)

        exclusive_start_key = response.get("LastEvaluatedKey")
        if not exclusive_start_key:
            break

    return standings
