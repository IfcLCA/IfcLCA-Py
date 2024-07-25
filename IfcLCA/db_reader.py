import json

class IfcLCADBReader:
    def __init__(self, db_path):
        self.db = self.load(db_path)

    def load(self, db_path):
        with open(db_path, 'r') as f:
            data = json.load(f)
        return data

    def get_material_data(self, material_id):
        return self.db.get(material_id, {})