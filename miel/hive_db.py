# miel/hive_db.py
from tinydb import TinyDB

hive = TinyDB('miel_db.json')

def add_pattern(agent, file_path):
    hive.insert({'agent': agent, 'file': file_path})
