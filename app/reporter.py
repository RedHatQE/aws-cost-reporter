import json
from datetime import datetime
import os
import boto3
import requests
from botocore.client import ClientError
from flask import Flask
from pyaml_env import parse_config
import calendar

FLASK_APP = Flask("AWS Cost Reporter")


def send_slack_message(message, webhook_url):
    slack_data = {"text": message}
    print(f"Sending message to slack: {message}")
    response = requests.post(
        webhook_url,
        data=json.dumps(slack_data),
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        raise ValueError(
            f"Request to slack returned an error {response.status_code} with the following message: {response.text}"
        )


@FLASK_APP.route("/")
def reporter():
    msg = ""
    total_cost = {}
    config_data = parse_config(os.getenv("AWS_COST_REPORTER_CONFIG", "accounts.yaml"))
    slack_webhook_url = config_data.get("slack-webhook-url")
    app_extrenal_url = config_data.get("app-external-url")

    _today = datetime.today()
    this_month_start = datetime(_today.year, _today.month, 1).strftime("%Y-%m-%d")
    this_month_end = datetime.today().strftime("%Y-%m-%d")

    _last_month = _today.month - 1
    last_month_start = datetime(_today.year, _last_month, 1).strftime("%Y-%m-%d")
    last_month_end = datetime(
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
            print(f"Failed to get cost for {account}: {exp}")
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
            f"\t[{last_month_start}/{last_month_end}]{float(_last_month_total_cost): .2f}{_unit_symbol}"
        )

    if slack_webhook_url:
        slack_msg = f"{app_extrenal_url}\n{msg}"
        send_slack_message(message=slack_msg, webhook_url=slack_webhook_url)

    return msg


def main():
    FLASK_APP.logger.info(f"Starting {FLASK_APP.name} app")
    FLASK_APP.run(
        port=5000,
        host="0.0.0.0",
        use_reloader=True,
    )


if __name__ == "__main__":
    main()
