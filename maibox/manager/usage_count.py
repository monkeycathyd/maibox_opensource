class UsageCount:
    handled_user_count = dict()
    handled_count = 0
    def add(self, wxid):
        if wxid not in self.handled_user_count:
            self.handled_user_count[wxid] = 0
        self.handled_user_count[wxid] += 1
        self.handled_count += 1

    def get(self, wxid=None):
        my_count = 0
        if wxid is not None:
            my_count = self.handled_user_count.get(wxid, 0)
        return len(self.handled_user_count.keys()), self.handled_count, my_count