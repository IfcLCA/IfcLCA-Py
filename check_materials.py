#!/usr/bin/env python3

import ifcopenshell
from IfcLCA import IfcLCA

# Load test file
ifc = ifcopenshell.open('../IfcLCA-blend/test/simple_building.ifc')
lca = IfcLCA(ifc)

# Check all materials
print('Materials found:')
for mat in lca.discover_materials():
    print(f'  - {mat["name"]}: {mat["elements"]} elements, type: {mat["type"]}')

# Check raw materials in file
print('\nAll material definitions in file:')
for mat in ifc.by_type('IfcMaterial'):
    print(f'  - {mat.Name}') 