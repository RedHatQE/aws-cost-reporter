FROM python:3.12

COPY app/* /aws-cost-slack-reporter/app/
COPY pyproject.toml poetry.lock /aws-cost-slack-reporter/
WORKDIR /aws-cost-slack-reporter
RUN python3 -m pip install pip --upgrade \
    && python3 -m pip install poetry \
    && poetry config cache-dir /aws-cost-slack-reporter \
    && poetry config virtualenvs.in-project true \
    && poetry config installer.max-workers 10 \
    && poetry install

ENTRYPOINT ["poetry", "run", "python", "app/reporter.py"]
