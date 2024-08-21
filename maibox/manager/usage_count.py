class UsageCount:
    handled_user_count = dict(unknown=0)
    def add(self, wxid="unknown"):
        if wxid not in self.handled_user_count:
            self.handled_user_count[wxid] = 0
        self.handled_user_count[wxid] += 1

    def get(self, wxid="unknown"):
        my_count = 0
        if wxid is not None:
            my_count = self.handled_user_count.get(wxid, 0)
        return len(self.handled_user_count.keys()), sum(self.handled_user_count.values()), my_count