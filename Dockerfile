# 使用更轻量级的基础镜像
FROM python:3.12.4-alpine3.20 AS build

WORKDIR /app

# 预先安装系统依赖项
RUN apk add --no-cache --update openjdk21-jre

# 复制并安装 Python 依赖项
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY . .

# 使用更轻量级的基础镜像来创建最终镜像
FROM python:3.12.4-alpine3.20

WORKDIR /app

# 复制前一阶段的安装结果
COPY --from=build /usr/lib/jvm /usr/lib/jvm
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /app /app

ENTRYPOINT [ "python3", "-m", "maibox" ]

