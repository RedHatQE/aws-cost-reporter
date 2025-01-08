FROM python:3.13

COPY app/* /aws-cost-reporter/app/
COPY pyproject.toml poetry.lock README.md /aws-cost-reporter/
WORKDIR /aws-cost-reporter
RUN python3 -m pip install pip --upgrade \
  && python3 -m pip install poetry \
  && poetry config cache-dir /aws-cost-reporter \
  && poetry config virtualenvs.in-project true \
  && poetry config installer.max-workers 10 \
  && poetry install

ENTRYPOINT ["poetry", "run", "python", "app/reporter.py"]
