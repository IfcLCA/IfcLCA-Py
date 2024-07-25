from IfcLCA.utils import selector
from ifcopenshell.util.element import get_pset

class IfcLCAAnalysis:
    def __init__(self, ifc_file, db_reader, mapping):
        self.ifc_file = ifc_file
        self.db_reader = db_reader
        self.mapping = mapping

    def run(self):
        results = {}
        for mapping_query, carbon_db_id in self.mapping.items():
            elements = selector.filter_elements(self.ifc_file, mapping_query)
            total_carbon = 0
            for element in elements:
                volume = get_pset(self.ifc_file, element, "Qto_...BaseQuantities.GrossVolume").get('value', 0)
                material_data = self.db_reader.get_material_data(carbon_db_id)
                density = material_data.get('density', 0)
                carbon_per_unit = material_data.get('carbon_per_unit', 0)
                total_carbon += volume * density * carbon_per_unit
            results[carbon_db_id] = total_carbon
        return results