# Get AWS total cost

This is a simple tool to get AWS total cost

## Usage (Local)

```bash
poetry install
poetry run python app/reporter.py
```

## Usage (Container)

```bash
docker build -t aws-cost-slack-reporter .
docker run --rm aws-cost-slack-reporter
```

## Configuration
accounts YAML file with AWS credentials:

```yaml
accounts:
  account-name:
    secret_access_key: "Secret Access Key" # pragma: allowlist secret
    access_key_id: "Access Key ID" # pragma: allowlist secret
```
export AWS_COST_REPORTER_CONFIG="path to accounts YAML file"

## Tests
Run AWS costs reporting tests:

```bash
poetry run pytest tests
```
