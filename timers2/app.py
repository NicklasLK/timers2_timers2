import os

import boto3
from boto3.dynamodb.conditions import Key
from dateutil.parser import isoparse
from flask import Flask, render_template

app = Flask(__name__)


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@app.route("/")
def index():
    timers = table.query(KeyConditionExpression=Key("PK").eq("TIMER"))["Items"]

    for timer in timers:
        sk_parts = timer["SK"].split("#")
        if len(sk_parts) != 3:
            continue

        timer["start_time"] = isoparse(sk_parts[1])

    return render_template(
        "index.html", user={"permissions": {"delete_timer": True}}, timers=timers
    )


@app.errorhandler(404)
def resource_not_found(e):
    return render_template("404.html")
