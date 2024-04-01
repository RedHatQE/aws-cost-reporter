import json
from datetime import datetime
import os
import boto3
import requests
from botocore.client import ClientError
from dateutil.relativedelta import relativedelta
from flask import Flask
from pyaml_env import parse_config

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
    total_cost = {}
    accounts = parse_config(os.getenv("AWS_COST_REPORTER_CONFIG", "accounts.yaml"))
    slack_webhook_url = None

    start = (datetime.today() - relativedelta(months=1)).strftime("%Y-%m-01")
    end = datetime.today().strftime("%Y-%m-01")

    for account, data in accounts.items():
        access_key_id = data["access_key_id"]
        secret_access_key = data["secret_access_key"]
        client = boto3.client(
            "ce",
            "us-east-1",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

        try:
            cost = client.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["AmortizedCost"],
            )
        except ClientError as exp:
            print(f"Failed to get cost for {account}: {exp}")
            continue

        _total_data = cost["ResultsByTime"][0]["Total"]["AmortizedCost"]
        _total_cost = _total_data["Amount"]
        _total_unit = _total_data["Unit"]
        total_cost[account] = (
            f"{float(_total_cost): .2f}{'$' if _total_unit == 'USD' else _total_unit}"
        )

    if slack_webhook_url:
        send_slack_message(message=total_cost, webhook_url=slack_webhook_url)

    html = ""
    html = """
<!DOCTYPE html>
<html>
<style>
table, th, td {
  border:1px solid black;
}
</style>
<body>
<h2>AWS Cost Report</h2>

<table style="width:50%">
  <tr>
    <th>Account</th>
    <th>Cost</th>
  </tr>
"""
    # Make table in HTML with total cost for each account
    for account, cost in total_cost.items():
        html += f"<tr><td>{account}</td><td>{cost}</td></tr>"

    html += """
</table>
</body>
</html>
"""

    return html


def main():
    FLASK_APP.logger.info(f"Starting {FLASK_APP.name} app")
    FLASK_APP.run(
        port=5000,
        host="0.0.0.0",
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
