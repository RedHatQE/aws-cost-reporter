import os
import pytest

import yaml

from app.reporter import update_cost_reporter, get_current_and_previous_months_dates


@pytest.fixture
def aws_static_costs():
    return {"current_month": 700, "previous_month": 800}


@pytest.fixture
def aws_accounts_file():
    aws_accounts_filename = os.path.join(
        f"{os.getcwd()}/app/tests", "test_accounts.yaml"
    )
    os.environ["AWS_COST_REPORTER_CONFIG"] = aws_accounts_filename

    return aws_accounts_filename


@pytest.fixture
def aws_account_names(aws_accounts_file):
    with open(aws_accounts_file, "r") as fd:
        aws_accounts_data = yaml.safe_load(stream=fd)
        _aws_account_names = aws_accounts_data["accounts"].keys()

        yield _aws_account_names


@pytest.fixture
def expected_cost_report_message(aws_static_costs, aws_account_names):
    this_month_start, this_month_end, last_month_start, last_month_end = (
        get_current_and_previous_months_dates()
    )
    cost_report_message = ""
    for aws_account_name in aws_account_names:
        cost_report_message += (
            f"{aws_account_name}:\n\t[{this_month_start}/{this_month_end}]{float(aws_static_costs['current_month']): .2f}$\n"
            f"\t[{last_month_start}/{last_month_end}]{float(aws_static_costs['previous_month']): .2f}$\n"
        )

    return cost_report_message


@pytest.fixture
def mock_boto3_client(mocker, aws_static_costs, aws_account_names):
    mocked_client = mocker.MagicMock()
    mocked_client.get_cost_and_usage.side_effect = [
        {
            "ResultsByTime": [
                {
                    "Total": {
                        "NetUnblendedCost": {
                            "Amount": aws_static_costs["current_month"],
                            "Unit": "USD",
                        }
                    }
                }
            ]
        },
        {
            "ResultsByTime": [
                {
                    "Total": {
                        "NetUnblendedCost": {
                            "Amount": aws_static_costs["previous_month"],
                            "Unit": "USD",
                        }
                    }
                }
            ]
        },
    ] * len(aws_account_names)
    mocker.patch("boto3.client", return_value=mocked_client)
    return mocked_client


def test_aws_cost_report(expected_cost_report_message, mock_boto3_client):
    actual_cost_report_message = update_cost_reporter()
    assert actual_cost_report_message == expected_cost_report_message, (
        f"AWS cost report message does not match the expected.\n"
        f"Actual: {actual_cost_report_message}, expected: {expected_cost_report_message}"
    )
