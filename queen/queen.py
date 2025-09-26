# ...existing code...
from tinydb import TinyDB, Query
from datetime import datetime
class Queen:
    def __init__(self):
        from tinydb import TinyDB, Query
        self.hive = TinyDB('hive.json')
        self.query = Query()

    def report(self, agent, file):
        # Solo agrega si no existe ya ese registro
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.hive.contains((self.query.agent == agent) & (self.query.file == file)):
            self.hive.insert({'agent': agent, 'file': file,'datetime': now})
# ...existing code...