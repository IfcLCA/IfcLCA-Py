from ifcopenshell.util.element import get_pset

class IfcLCA:
    def __init__(self, ifc_file, db_reader):
        self.ifc_file = ifc_file
        self.db_reader = db_reader

    def map_materials(self, material_name, query):
        # Logic to map materials to elements based on the query
        pass

    def get_quantity(self, element, quantity_name):
        quantity = get_pset(self.ifc_file, element, quantity_name)
        return quantity.get('value', 0) if quantity else 0