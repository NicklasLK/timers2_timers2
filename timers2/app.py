import os

import boto3
from flask import Flask, render_template

from .utils import get_timers


app = Flask(__name__)


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@app.route("/")
def index():
    timers = get_timers(table)

    return render_template(
        "index.html", user={"permissions": {"delete_timer": True}}, timers=timers
    )


@app.errorhandler(404)
def resource_not_found(e):
    return render_template("404.html")
