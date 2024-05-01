import os
from unittest.mock import MagicMock
from pytest_mock.plugin import MockerFixture

import pytest
from pyaml_env import parse_config
from typing import Dict, List

from app.reporter import update_cost_reporter, get_current_and_previous_months_dates


@pytest.fixture
def aws_static_costs() -> Dict[str, int]:
    return {"current_month": 700, "previous_month": 800}


@pytest.fixture
def aws_accounts_file() -> str:
    aws_accounts_filename = "app/tests/manifests/test_accounts.yaml"
    os.environ["AWS_COST_REPORTER_CONFIG"] = aws_accounts_filename

    return aws_accounts_filename


@pytest.fixture
def aws_account_names(aws_accounts_file: str) -> List[str]:
    return [
        account_name
        for account_name, account_data in parse_config(path=aws_accounts_file)[
            "accounts"
        ].items()
    ]


@pytest.fixture
def expected_cost_report_message(
    aws_static_costs: Dict[str, int], aws_account_names: List[str]
) -> str:
    this_month_start, this_month_end, last_month_start, last_month_end = (
        get_current_and_previous_months_dates()
    )
    return (
        f"{aws_account_names[0]}:\n"
        f"\t[{this_month_start}/{this_month_end}]{float(aws_static_costs['current_month']): .2f}$\n"
        f"\t[{last_month_start}/{last_month_end}]{float(aws_static_costs['previous_month']): .2f}$\n"
        f"{aws_account_names[1]}:\n"
        f"\t[{this_month_start}/{this_month_end}]{float(aws_static_costs['current_month']): .2f}$\n"
        f"\t[{last_month_start}/{last_month_end}]{float(aws_static_costs['previous_month']): .2f}$\n"
    )


@pytest.fixture
def mocked_boto3_client(
    mocker: MockerFixture,
    aws_static_costs: Dict[str, int],
    aws_account_names: List[str],
) -> MagicMock:
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


def test_aws_cost_report(
    expected_cost_report_message: str, mocked_boto3_client: MagicMock
) -> None:
    actual_cost_report_message = update_cost_reporter()
    assert actual_cost_report_message == expected_cost_report_message
