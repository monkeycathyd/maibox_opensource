import datetime
import os
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import time

import maibox.config as config
from maibox.auto_bot import get_preview

server_config = config.get_config()

class AutoRemove(threading.Thread):
    def run(self):
        print("Auto remove thread is started")
        with open("time_avg", "w") as f:
            f.write("")
        with open("./time_test", "w") as f:
            f.write("")
        while True:
            if int(datetime.datetime.now().strftime("%M")) % 5 == 0:
                try:
                    with open("time_test", "r") as f:
                        result = list(map(int, f.read().split()))
                    with open("time_avg", "w") as f:
                        f.write(f"{sum(result) / len(result):.4f}")
                    with open("time_test", "w") as f:
                        f.write("")

                    time.sleep(60)
                except:
                    pass

class AutoTest(threading.Thread):
    def run(self):
        print("Title server testing thread is started")
        while True:
            try:
                print("Title server testing")
                ctime = int(time.time() * 1000)
                if not get_preview(server_config["settings"]["default_test_uid"], None):
                    print("Title server testing failed")
                else:
                    print("Title server testing success")
                used = int(time.time() * 1000) - ctime
                print(f"{used}ms")
                time.sleep(0.5)
            except KeyboardInterrupt:
                os._exit(0)

class ErrorEMailSender(threading.Thread):
    def __init__(self, subject, content):
        super().__init__()
        self.subject = f"{datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")} {subject}"
        self.content = content

    def run(self):
        time.sleep(0.5)
        sender_email = server_config["email"]["sender"]
        password = server_config["email"]["password"]
        host = server_config["email"]["host"]
        port = server_config["email"]["port"]
        receiver_emails = server_config["email"]["receiver"]  # list of receiver email

        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = ", ".join(receiver_emails)
        message['Subject'] = self.subject

        message.attach(MIMEText(self.content, 'plain'))

        att = MIMEText(open('./logging.log', 'rb').read(), 'base64', 'utf-8')
        att["Content-Type"] = 'application/octet-stream'
        att["Content-Disposition"] = f'attachment; filename="logging-{int(time.time())}.log"'
        message.attach(att)

        try:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(sender_email, password)
                text = message.as_string()
                server.sendmail(sender_email, receiver_emails, text)
                print("Email sent successfully")
                server.quit()
            with open('logging.log', "w") as f:
                f.write("")
        except Exception as e:
            print(f"Error occurred: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    AutoTest().start()