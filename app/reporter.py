import json
import os
import requests

import click
from awscost.cost_explorer import CostExplorer
from dateutil.relativedelta import relativedelta
from datetime import datetime


def send_slack_message(message, webhook_url):
    slack_data = {"text": message}
    click.echo(f"Sending message to slack: {message}")
    response = requests.post(
        webhook_url,
        data=json.dumps(slack_data),
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        raise ValueError(
            f"Request to slack returned an error {response.status_code} with the following message: {response.text}"
        )


@click.command("aws-reporter")
@click.option(
    "-m",
    "--months",
    default=1,
    show_default=True,
    help="Number of months to report",
)
@click.option(
    "--aws-profiles",
    default="",
    help="comma separated strings of AWS profiles to generate cost report",
)
@click.option(
    "--slack-webhook-url",
    default=os.environ.get("SLACK_WEBHOOK_URL"),
    help="Slack webhook url",
    show_default=True,
)
def main(months, aws_profiles, slack_webhook_url):
    start = (datetime.today() - relativedelta(months=months)).strftime("%Y-%m-01")
    end = datetime.today().strftime("%Y-%m-01")

    for aws_profile in aws_profiles.split(","):
        _aws_profile = os.environ["AWS_PROFILE"] = (
            aws_profile if aws_profile else "default"
        )
        cost_explorer = CostExplorer(
            granularity="MONTHLY",
            start=start,
            end=end,
            dimensions=["SERVICE"],
            metrics="UnblendedCost",
            threshold=1.0,
        )
        total_cost = cost_explorer.get_cost_and_usage_total()
        msg = f"Profile {_aws_profile}:\n\t"
        for values in total_cost.values():
            for month, total in values.items():
                msg += f"Date: {month}: {total}$\n\t"

        click.echo(msg)

        if slack_webhook_url:
            send_slack_message(message=msg, webhook_url=slack_webhook_url)

        os.unsetenv("AWS_PROFILE")


if __name__ == "__main__":
    main()
