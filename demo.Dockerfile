FROM ghcr.io/joheli/streamlighter:0.1-py3.14

WORKDIR /app

COPY demo_requirements.txt /app/demo_requirements.txt

RUN pip install --user --no-cache-dir -r /app/demo_requirements.txt
