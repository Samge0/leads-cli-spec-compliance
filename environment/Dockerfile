FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# No network operations during build: python3/bash/sh from the base image
# cover everything this task needs (stdlib-only CLI, stdlib-only verifier).

COPY leads/ /opt/leads/

WORKDIR /opt/leads

# PATH 内可达的工具入口
RUN echo '#!/bin/sh\nexec python3 /opt/leads/leads_cli.py "$@"' > /usr/local/bin/leads \
    && chmod +x /usr/local/bin/leads

# Pre-create log dirs expected by the harness (oracle/verifier redirects here)
RUN mkdir -p /logs/agent /logs/verifier

CMD ["/bin/bash"]
