FROM error063/maibox_base_system:1

WORKDIR /app

COPY . .

RUN pip3 install -r requirements.txt

RUN chmod +x entrypoint.sh

EXPOSE 80/tcp

ENTRYPOINT [ "/app/entrypoint.sh" ]
