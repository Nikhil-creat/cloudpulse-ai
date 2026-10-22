FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip && rm -rf /var/lib/apt/lists/*
# Terraform CLI for dry-run / blast radius checks
ARG TF_VERSION=1.9.8
RUN curl -fsSL https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip -o /tmp/tf.zip \
 && unzip /tmp/tf.zip -d /usr/local/bin && rm /tmp/tf.zip
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN useradd -m app && chown -R app /srv
USER app
