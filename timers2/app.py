import os

import boto3
from flask import Flask, abort, redirect, render_template, request, session, url_for
from flask_pyoidc import OIDCAuthentication
from flask_pyoidc.provider_configuration import ClientMetadata, ProviderConfiguration
from flask_pyoidc.redirect_uri_config import RedirectUriConfig
from flask_pyoidc.user_session import UserSession
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup

from .forms import StandingForm, TimerForm
from .utils import get_standings, get_timers, put_timer

PERMISSION_ROLES = {
    "urn:sso:alliance:test-alliance": ["view_timers", "add_timer"],
    "urn:sso:allies": ["view_timers", "add_timer"],
    "urn:sso:leadership:high-command": [
        "delete_timer",
        "view_standings",
        "add_standing",
        "delete_standing",
        "view_secret_timers",
    ],
    "urn:sso:diplomatic:alliance-diplomats": [
        "delete_timer",
        "view_standings",
        "add_standing",
        "delete_standing",
    ],
    "urn:sso:military:fc:skirmish": ["delete_timer"],
    "urn:sso:military:military-coordinator": ["delete_timer"],
    "urn:sso:leadership:test-command": ["delete_timer"],
    "urn:sso:logistics:alliance-logistics": ["view_secret_timers"],
}


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
csrf = CSRFProtect(app)
auth = OIDCAuthentication(
    {
        "default": ProviderConfiguration(
            issuer="https://sso.pleaseignore.com/auth/realms/auth-ng",
            client_metadata=ClientMetadata(
                client_id=os.environ["OIDC_CLIENT_ID"],
                client_secret=os.environ["OIDC_CLIENT_SECRET"],
                post_logout_redirect_uris=[os.environ["BASE_URL"]],
            ),
            auth_request_params={"scope": ["openid"] + list(PERMISSION_ROLES.keys())},
        )
    },
    app,
    RedirectUriConfig(os.environ["BASE_URL"] + "/callback", "callback"),
)


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@app.before_request
def request_started():
    user_session = UserSession(session, provider_name="default")
    if not user_session.is_authenticated():
        request.primary_character_name = None
        request.permissions = {}

        return

    user_roles = user_session.id_token["realm_access"]["roles"]

    request.primary_character_name = user_session.id_token["character"]
    request.permissions = {
        permission: True
        for role, permissions in PERMISSION_ROLES.items()
        for permission in permissions
        if role in user_roles
    }


@app.template_filter()
def field_errors(field):
    return Markup("\n").join(
        Markup('<div class="invalid-feedback">{}</div>').format(error)
        for error in field.errors
    )


@app.route("/")
@auth.oidc_auth("default")
def index():
    if not request.permissions.get("view_timers"):
        return abort(403)

    timers = get_timers(
        table, include_secret=request.permissions.get("view_secret_timers")
    )

    return render_template("index.html", timers=timers)


@app.route("/add-timer", methods=["GET", "POST"])
@auth.oidc_auth("default")
def add_timer():
    if not request.permissions.get("add_timer"):
        return abort(403)

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
            added_by=request.primary_character_name,
        )

        return redirect(url_for("index"))

    return render_template("add_timer.html", form=form)


@app.route("/delete-timer/<id>", methods=["POST"])
@auth.oidc_auth("default")
def delete_timer(id):
    if not request.permissions.get("delete_timer"):
        return abort(403)

    table.delete_item(Key={"PK": "TIMER", "SK": id})

    return redirect(url_for("index"))


@app.route("/standings")
@auth.oidc_auth("default")
def standings():
    if not request.permissions.get("view_standings"):
        return abort(403)

    return render_template("standings.html", standings=get_standings(table))


@app.route("/add-standing", methods=["GET", "POST"])
@auth.oidc_auth("default")
def add_standing():
    if not request.permissions.get("add_standing"):
        return abort(403)

    form = StandingForm()
    if form.validate_on_submit():
        table.put_item(
            Item={
                "PK": "STANDING",
                "SK": "ALLIANCE#{}".format(form.data["ticker"]),
                "standing_type": form.data["standing_type"],
                "notes": form.data["notes"],
            }
        )

        return redirect(url_for("standings"))

    return render_template("add_standing.html", form=form)


@app.route("/delete-standing/<id>", methods=["POST"])
@auth.oidc_auth("default")
def delete_standing(id):
    if not request.permissions.get("delete_standing"):
        return abort(403)

    table.delete_item(Key={"PK": "STANDING", "SK": id})

    return redirect(url_for("standings"))


@app.errorhandler(404)
def resource_not_found(e):
    return render_template("404.html")
