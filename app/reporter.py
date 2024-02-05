import json
import os
import requests

import click
import yaml
from awscost.cost_explorer import CostExplorer
from dateutil.relativedelta import relativedelta
from datetime import datetime


def config_to_dict(config):
    with open(config) as fd:
        return yaml.safe_load(fd)


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
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=os.environ.get("AWS_COST_REPORT_CONFIG_FILE"),
    help="AWS cost report config file",
)
def main(months, aws_profiles, slack_webhook_url, config):
    config_dict = config_to_dict(config=config) if config else {}
    months = config_dict.get("months", months)
    aws_profiles = config_dict.get("aws-profiles", aws_profiles)
    slack_webhook_url = config_dict.get("slack-webhook-url", slack_webhook_url)
    aws_profiles = (
        aws_profiles if isinstance(aws_profiles, list) else aws_profiles.split(",")
    )

    start = (datetime.today() - relativedelta(months=months)).strftime("%Y-%m-01")
    end = datetime.today().strftime("%Y-%m-01")

    for aws_profile in aws_profiles:
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
