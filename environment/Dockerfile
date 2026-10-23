# ===== leads-cli 镜像 =====
# 名录查询工具修复任务：单文件 CLI + 纯标准库，构建秒级、零外网
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

# ---- 工具与数据 ----
COPY leads/ /opt/leads/

WORKDIR /opt/leads

# 工具调用入口（PATH 内可达，默认参数即数据集）
RUN echo '#!/bin/sh\nexec python3 /opt/leads/leads_cli.py "$@"' > /usr/local/bin/leads \
    && chmod +x /usr/local/bin/leads

CMD ["/bin/bash"]
