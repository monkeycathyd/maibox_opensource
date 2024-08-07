FROM python:3.12.4-alpine3.20

WORKDIR /app

COPY . .

RUN apk add --no-cache --update openjdk21-jre && \
    pip3 install --no-cache-dir -r requirements.txt

EXPOSE 80/tcp

ENTRYPOINT [ "python3", "-m", "maibox" ]
