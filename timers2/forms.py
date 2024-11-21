import os
import re
from datetime import datetime, timedelta, timezone

import boto3
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField, validators

from .utils import STRUCTURE_TYPES, get_system_region_name

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


class DatetimeField(StringField):
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)

        if "Reinforced until " in self.data:
            time_start_index = self.data.index("Reinforced until ") + 17
            datestr = self.data[time_start_index : time_start_index + 19]
            self.data = datetime.strptime(datestr, "%Y.%m.%d %H:%M:%S")
            return

        timer_matches = list(
            re.finditer(r"(?P<time_amt>[0-9]+)[ ]*(?P<dhms>[dhms]{1})", self.data)
        )

        if not timer_matches:
            self.data = None

        timer_time = datetime.now(tz=timezone.utc)
        for this_match in timer_matches:
            dhms = this_match.group("dhms")
            delta_amt = int(this_match.group("time_amt"))
            if dhms == "d":
                timer_time = timer_time + timedelta(days=delta_amt)
            elif dhms == "h":
                timer_time = timer_time + timedelta(hours=delta_amt)
            elif dhms == "m":
                timer_time = timer_time + timedelta(minutes=delta_amt)
            elif dhms == "s":
                timer_time = timer_time + timedelta(seconds=delta_amt)

        self.data = timer_time

    def _value(self):
        return (
            str(self.raw_data[0])
            if self.raw_data and len(self.raw_data) > 0 and self.raw_data[0] is not None
            else ""
        )


class SystemField(StringField):
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)

        try:
            self.data = (self.data, get_system_region_name(table, self.data))
        except ValueError:
            self.data = None

    def _value(self):
        return (
            str(self.raw_data[0])
            if self.raw_data and len(self.raw_data) > 0 and self.raw_data[0] is not None
            else ""
        )


class TimerForm(FlaskForm):
    start_time = DatetimeField(
        "Date/time",
        validators=[validators.DataRequired()],
    )
    system = SystemField(
        "System",
        validators=[validators.DataRequired(message="Invalid solar system")],
    )
    corporation_ticker = StringField(
        "Corporation ticker", validators=[validators.InputRequired()]
    )
    alliance_ticker = StringField("Alliance ticker")
    standing_type = SelectField(
        "Standing",
        choices=["Friendly", "Hostile", "It's complicated", "Unknown"],
        validators=[validators.InputRequired()],
    )
    structure_type = SelectField(
        "Structure type",
        choices=STRUCTURE_TYPES.items(),
        validators=[validators.InputRequired()],
    )
    timer_type = SelectField(
        "Timer type",
        choices=[
            "Shield",
            "Armor",
            "Anchoring",
            "Structure",
            "Armor + Structure",
            "Not Applicable",
            "Unknown",
        ],
        validators=[validators.InputRequired()],
    )
    replace = SelectField(
        "Replace",
        choices=[
            "Not Applicable",
            "Logistics Replacement",
            "Corp Replacement",
        ],
        validators=[validators.InputRequired()],
    )
    notes = TextAreaField("Notes")


class StandingForm(FlaskForm):
    ticker = StringField("Corporation ticker", validators=[validators.InputRequired()])
    standing_type = SelectField(
        "Standing",
        choices=["Friendly", "Hostile", "It's complicated", "Unknown"],
        validators=[validators.InputRequired()],
    )
    notes = TextAreaField("Notes")
