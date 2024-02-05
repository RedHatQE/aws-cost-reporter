# Get AWS total cost and report to slack

This is a simple tool to get AWS total cost and report to slack.

## Usage (Local)

```bash
poetry install
poetry run python app/reporter.py --help
```

## Usage (Container)

```bash
docker build -t aws-cost-slack-reporter .
docker run --rm aws-cost-slack-reporter --help
```

## Configuration

```yaml
aws-profiles: # AWS profiles to generate cost report
    - default
    - prod
months: 1 # number of months to report
slack-webhook-url: <slack-webhook-url>
```
