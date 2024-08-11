# 使用更轻量级的基础镜像
FROM python:3.12.4-alpine3.20 AS builder

WORKDIR /app
# 复制并安装依赖项
COPY requirements.txt .
RUN apk update && apk add --no-cache --update openjdk21-jre tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    pip3 install --no-cache-dir -r requirements.txt &&  \
    rm -rf /app/requirements.txt

# 使用更轻量级的基础镜像来创建最终镜像
FROM alpine:3.20

WORKDIR /app

# 复制前一阶段的安装结果
COPY --from=builder / /
# 复制应用程序代码
COPY static static

COPY maibox maibox

ENTRYPOINT [ "python3", "-m", "maibox" ]

