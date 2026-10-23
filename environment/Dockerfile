FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY leads/ /opt/leads/

WORKDIR /opt/leads

# PATH 内可达的工具入口
RUN echo '#!/bin/sh\nexec python3 /opt/leads/leads_cli.py "$@"' > /usr/local/bin/leads \
    && chmod +x /usr/local/bin/leads

CMD ["/bin/bash"]
