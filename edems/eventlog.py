import pandas as pd

class EventLog:
    def __init__(self):
        self.rows = []

    def add(self, t, etype, **kwargs):
        row = {"t": float(t), "event": etype}
        row.update(kwargs)
        self.rows.append(row)

    def to_df(self):
        return pd.DataFrame(self.rows)
