import json
import datetime
import os
import boto3
import requests
from botocore.client import ClientError
from flask import Flask
from flask.logging import default_handler
from pyaml_env import parse_config
import calendar
import croniter
from simple_logger.logger import get_logger
from multiprocessing import Process
import time


FLASK_APP = Flask("AWS Cost Reporter")
FLASK_APP.logger.removeHandler(default_handler)
FLASK_APP.logger.addHandler(get_logger(FLASK_APP.logger.name).handlers[0])


def send_slack_message(message, webhook_url):
    slack_data = {"text": message}
    FLASK_APP.logger.info(f"Sending message to slack: {message}")
    response = requests.post(
        webhook_url,
        data=json.dumps(slack_data),
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        FLASK_APP.logger.error(
            f"Request to slack returned an error {response.status_code} with the following message: {response.text}"
        )


def update_cost_reporter():
    msg = ""
    total_cost = {}
    config_data = parse_config(os.getenv("AWS_COST_REPORTER_CONFIG", "accounts.yaml"))
    slack_webhook_url = config_data.get("slack-webhook-url")
    app_extrenal_url = config_data.get("app-external-url")

    _today = datetime.datetime.today()
    this_month_start = datetime.datetime(_today.year, _today.month, 1).strftime(
        "%Y-%m-%d"
    )
    this_month_end = datetime.datetime.today().strftime("%Y-%m-%d")

    _last_month = _today.month - 1
    last_month_start = datetime.datetime(_today.year, _last_month, 1).strftime(
        "%Y-%m-%d"
    )
    last_month_end = datetime.datetime(
        _today.year, _last_month, calendar.monthrange(_today.year, _last_month)[1]
    ).strftime("%Y-%m-%d")

    for account, data in config_data["accounts"].items():
        total_cost[account] = {}
        access_key_id = data["access_key_id"]
        secret_access_key = data["secret_access_key"]
        client = boto3.client(
            "ce",
            "us-east-1",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

        try:
            this_month_cost = client.get_cost_and_usage(
                TimePeriod={"Start": this_month_start, "End": this_month_end},
                Granularity="MONTHLY",
                Metrics=["AmortizedCost"],
            )
            last_month_cost = client.get_cost_and_usage(
                TimePeriod={"Start": last_month_start, "End": last_month_end},
                Granularity="MONTHLY",
                Metrics=["AmortizedCost"],
            )
        except ClientError as exp:
            FLASK_APP.logger.info(f"Failed to get cost for {account}: {exp}")
            continue

        _this_month_total_cost_data = this_month_cost["ResultsByTime"][0]["Total"][
            "AmortizedCost"
        ]
        _this_month_total_cost = _this_month_total_cost_data["Amount"]

        _last_month_total_cost_data = last_month_cost["ResultsByTime"][0]["Total"][
            "AmortizedCost"
        ]
        _last_month_total_cost = _last_month_total_cost_data["Amount"]

        _total_unit = _this_month_total_cost_data["Unit"]
        _unit_symbol = "$" if _total_unit == "USD" else _total_unit
        total_cost[account][f"{this_month_start}/{this_month_end}"] = (
            f"{float(_this_month_total_cost): .2f}{_unit_symbol}"
        )
        total_cost[account][f"{last_month_start}/{last_month_end}"] = (
            f"{float(_last_month_total_cost): .2f}{_unit_symbol}"
        )
        msg += (
            f"{account}:\n"
            f"\t[{this_month_start}/{this_month_end}] {float(_this_month_total_cost): .2f}{_unit_symbol}\n"
            f"\t[{last_month_start}/{last_month_end}]{float(_last_month_total_cost): .2f}{_unit_symbol}\n"
        )

    if msg and slack_webhook_url:
        slack_msg = f"""
```{msg}
To force update send run curl {app_extrenal_url}
```
"""
        FLASK_APP.logger.info(f"Sending message to slack: {slack_msg}")
        send_slack_message(message=slack_msg, webhook_url=slack_webhook_url)

    return msg


def run_in_background(cron):
    FLASK_APP.logger.info("Starting cost reporter in background")
    while True:
        now = datetime.datetime.now()
        next_run = cron.get_next(datetime.datetime)
        delta = next_run - now
        if delta.total_seconds() > 0:
            time.sleep(delta.total_seconds())
            try:
                FLASK_APP.logger.info("Running scheduled cost reporter")
                update_cost_reporter()
            except Exception as exp:
                FLASK_APP.logger.info(f"Failed to update cost reporter: {exp}")


@FLASK_APP.route("/update")
def webhook_update():
    FLASK_APP.logger.info("Updating cost reporter from webhook")
    return update_cost_reporter()


def main():
    config_data = parse_config(os.getenv("AWS_COST_REPORTER_CONFIG", "accounts.yaml"))
    if cron := config_data.get("cron"):
        cron = croniter.croniter(cron, datetime.datetime.now())
        proc = Process(target=run_in_background, kwargs={"cron": cron})
        proc.start()

    FLASK_APP.logger.info(f"Starting {FLASK_APP.name} app")
    FLASK_APP.run(
        port=5000,
        host="0.0.0.0",
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
