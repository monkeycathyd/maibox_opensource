import asyncio
import threading
import time
from datetime import datetime

import requests

class DivingFishApi:
    def __init__(self, df_token: str):
        self.df_token = df_token
        self.session = requests.Session()
        self.headers = {
            "Import-Token": self.df_token,
        }
        self.session.headers.update(self.headers)
        self.username = self.get_player_records()["nickname"]

    def get_player_records(self):
        resp = self.session.get("https://www.diving-fish.com/api/maimaidxprober/player/records")
        if resp.status_code != 200:
            return {"nickname": None}
        return resp.json()

    def update_player_records(self, records: list[dict]):
        resp = self.session.post(
            url='https://www.diving-fish.com/api/maimaidxprober/player/update_records',
            json=records
        )
        return resp.status_code == 200


class DivingFishRatingRankApi:
    def __init__(self):
        self.all_rating = {}
        self._update_date = datetime.fromtimestamp(0)
        self._update_success = False
        threading.Thread(target=self.update).start()

    def update(self):
        self._update_success = False
        resp = requests.get("https://www.diving-fish.com/api/maimaidxprober/rating_ranking")
        if resp.status_code == 200:
            self.all_rating = {item[1]["username"]: {"ra": item[1]["ra"], "rank": item[0]}
                               for item in enumerate(sorted(resp.json(), key=lambda x: x["ra"], reverse=True), start=1)}
            self._update_date = datetime.now()
        self._update_success = True

    def update_status(self):
        return self._update_success


    def lookup_rating_and_rank(self, username: str):
        if username in self.all_rating.keys():
            return {
                "ra": self.all_rating[username]["ra"],
                "rank": self.all_rating[username]["rank"],
                "update_date": self._update_date.strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                "ra": -1,
                "rank": -1,
                "update_date": self._update_date.strftime("%Y-%m-%d %H:%M:%S")
            }

if __name__ == "__main__":
    ra = DivingFishRatingRankApi()
    while not ra.update_status():
        print("waiting")
        time.sleep(1)
    print(ra.lookup_rating_and_rank("Error063"))
