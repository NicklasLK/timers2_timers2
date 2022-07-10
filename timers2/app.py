import os

import boto3
from flask import Flask, render_template, redirect, url_for
from markupsafe import Markup

from .forms import TimerForm
from .utils import get_timers, put_timer


app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@app.template_filter()
def field_errors(field):
    return Markup("\n").join(
        Markup('<div class="invalid-feedback">{}</div>').format(error)
        for error in field.errors
    )


@app.route("/")
def index():
    timers = get_timers(table)

    return render_template(
        "index.html", user={"permissions": {"delete_timer": True}}, timers=timers
    )


@app.route("/add-timer", methods=["GET", "POST"])
def add_timer():
    user = {"primary_character_name": "Tross Yvormes"}

    form = TimerForm()
    if form.validate_on_submit():
        system_name, region_name = form.data["system"]

        put_timer(
            table,
            start_time=form.data["start_time"],
            system_name=system_name,
            region_name=region_name,
            corporation_ticker=form.data["corporation_ticker"],
            alliance_ticker=form.data["alliance_ticker"],
            standing_type=form.data["standing_type"],
            structure_type=form.data["structure_type"],
            timer_type=form.data["timer_type"],
            replace=form.data["replace"],
            notes=form.data["notes"],
            added_by=user["primary_character_name"],
        )

        return redirect(url_for("index"))

    return render_template("add_timer.html", form=form)


@app.errorhandler(404)
def resource_not_found(e):
    return render_template("404.html")
