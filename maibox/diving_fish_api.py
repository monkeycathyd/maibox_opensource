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