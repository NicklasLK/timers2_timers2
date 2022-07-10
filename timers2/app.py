import os

import boto3
from flask import Flask, render_template

app = Flask(__name__)


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@app.route("/")
def index():
    return render_template("index.html")


@app.errorhandler(404)
def resource_not_found(e):
    return render_template("404.html")
