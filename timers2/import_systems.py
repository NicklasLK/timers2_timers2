import os
import asyncio

import boto3
import httpx

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


async def get_region(client, systems, region_id):
    region_response = await client.get(
        "https://esi.evetech.net/v1/universe/regions/{}".format(region_id)
    )
    region_response.raise_for_status()

    region = region_response.json()
    for constellation_id in region["constellations"]:
        constellation_response = await client.get(
            "https://esi.evetech.net/v1/universe/constellations/{}".format(
                constellation_id
            )
        )
        constellation_response.raise_for_status()

        constellation = constellation_response.json()
        for system_id in constellation["systems"]:
            systems[system_id] = {
                "PK": "SYSTEM",
                "GSI1PK": "SYSTEM#{}".format(system_id),
                "region_name": region["name"],
            }


async def get_regions():
    async with httpx.AsyncClient() as client:
        regions_response = await client.get(
            "https://esi.evetech.net/v1/universe/regions"
        )
        regions_response.raise_for_status()

        systems = {}
        await asyncio.gather(
            *(get_region(client, systems, x) for x in regions_response.json())
        )

        return systems


def handler(event, context):
    systems = asyncio.run(get_regions())

    system_ids = list(systems.keys())
    with table.batch_writer() as batch:
        for i in range(0, len(system_ids), 1000):
            names_response = httpx.post(
                "https://esi.evetech.net/v3/universe/names",
                json=system_ids[i : i + 1000],
            )
            names_response.raise_for_status()

            names = names_response.json()
            for system in names:
                systems[system["id"]]["SK"] = "SYSTEM#{}".format(system["name"])
                batch.put_item(Item=systems[system["id"]])
