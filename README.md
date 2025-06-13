# IfcLCA-Py

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![IfcOpenShell](https://img.shields.io/badge/IfcOpenShell-required-green.svg)](http://ifcopenshell.org/)

IfcLCA-Py is a Python package for performing Life Cycle Assessment (LCA) on building models using Industry Foundation Classes (IFC) files. It provides a comprehensive toolkit for analyzing the environmental impact of construction projects.

## Features

- **IFC Model Analysis**: Extract materials and quantities from IFC files
- **Multi-Database Support**: Built-in support for KBOB (Swiss) and ÖKOBAUDAT (German) databases
- **Environmental Indicators**: Calculate GWP (Global Warming Potential), PEnr (Primary Energy), and UBP (Environmental Impact Points)
- **Material Mapping**: Automatic and manual mapping of IFC materials to environmental databases
- **Optioneering**: Compare different material options to optimize environmental performance
- **Comprehensive Reporting**: Generate reports in text, CSV, and JSON formats
- **Blender Integration**: Full integration available via IfcLCA-blend add-on

## Installation

```bash
pip install ifclca
```

Or install from source:

```bash
git clone https://github.com/IfcLCA/IfcLCA-Py.git
cd IfcLCA-Py
pip install -e .
```

## Quick Start

```python
import ifcopenshell
from IfcLCA import IfcLCA, KBOBReader, IfcLCAReporter

# Load IFC file
ifc_file = ifcopenshell.open("building.ifc")

# Initialize database and LCA interface
db_reader = KBOBReader()  # Uses built-in KBOB data
lca = IfcLCA(ifc_file, db_reader)

# Discover and map materials
materials = lca.get_all_materials()
mapping = lca.auto_map_materials()

# Run analysis
analysis = lca.run_analysis(mapping)

# Generate report
reporter = IfcLCAReporter("My Building")
report = reporter.generate_analysis_report(analysis, 'text')
print(report)
```

## Detailed Usage

### 1. Loading IFC Files

```python
import ifcopenshell
ifc_file = ifcopenshell.open("path/to/building.ifc")
```

### 2. Database Selection

**KBOB (Swiss database) - Built-in:**
```python
from IfcLCA import KBOBReader
db_reader = KBOBReader()  # Uses default KBOB 2022 data
# Or load custom KBOB JSON:
db_reader = KBOBReader("path/to/custom_kbob.json")
```

**ÖKOBAUDAT (German database):**
```python
from IfcLCA import OkobaudatReader
db_reader = OkobaudatReader("path/to/OEKOBAUDAT.csv")
```

### 3. Material Discovery and Mapping

```python
from IfcLCA import IfcLCA

# Initialize
lca = IfcLCA(ifc_file, db_reader)

# Validate model
validation = lca.validate_model_for_lca()
if not validation['valid']:
    print("Warnings:", validation['warnings'])

# Get all materials
materials = lca.get_all_materials()
for mat_name, count, mat_type in materials:
    print(f"{mat_name}: {count} elements ({mat_type})")

# Auto-map materials
mapping = lca.auto_map_materials()

# Or manual mapping
mapping = {
    "Concrete C30/37": "KBOB_CONCRETE_C30_37",
    "Steel": "KBOB_STEEL_STRUCTURAL"
}
```

### 4. Running Analysis

```python
# Run analysis
analysis = lca.run_analysis(mapping)

# Get results by indicator
results = analysis.get_results_by_indicator()
print(f"Total GWP: {sum(results['gwp'].values()):.1f} kg CO₂-eq")
print(f"Total PEnr: {sum(results['penr'].values()):.0f} MJ")

# Get detailed results
detailed = analysis.get_detailed_results()
for material, details in detailed.items():
    print(f"{material}: {details['gwp']:.1f} kg CO₂-eq")
```

### 5. Optioneering

```python
from IfcLCA import IfcLCAOptioneering

# Create optioneering analysis
opt = IfcLCAOptioneering(ifc_file, db_reader, mapping)

# Add alternatives
opt.add_substitution_rule({
    'name': 'Low Carbon Concrete',
    'description': 'Use recycled concrete',
    'substitutions': {
        'Concrete C30/37': 'KBOB_CONCRETE_RC'
    }
})

# Compare material options
opt.add_material_comparison(
    'Concrete C30/37',
    ['KBOB_CONCRETE_C25_30', 'KBOB_CONCRETE_RC'],
    name="Concrete Alternatives"
)

# Run and get results
results = opt.run()
print(opt.generate_report())
```

### 6. Reporting

```python
from IfcLCA import IfcLCAReporter

reporter = IfcLCAReporter("Project Name")

# Generate different formats
text_report = reporter.generate_analysis_report(analysis, 'text')
csv_report = reporter.generate_analysis_report(analysis, 'csv')
json_report = reporter.generate_analysis_report(analysis, 'json')

# Save reports
reporter.save_report(text_report, 'report.txt')

# Get visualization data
viz_data = reporter.generate_visualization_data(analysis)
# Use viz_data with your preferred charting library
```

## IFC Requirements

For best results, your IFC file should include:

- **Material assignments**: Using IfcMaterial, IfcMaterialLayerSet, or IfcMaterialConstituentSet
- **Quantities**: BaseQuantities with GrossVolume or NetVolume
- **Proper units**: IfcUnitAssignment for correct scaling

## Environmental Indicators

The package calculates three main indicators:

- **GWP (Global Warming Potential)**: kg CO₂-equivalent
- **PEnr (Primary Energy non-renewable)**: MJ
- **UBP (Environmental Impact Points)**: Swiss Eco-points

## Database Format

### KBOB JSON Format
```json
{
  "MATERIAL_ID": {
    "name": "Material Name",
    "category": "Category",
    "density": 2400,
    "gwp": 0.1,
    "penr": 1.0,
    "ubp": 120,
    "unit": "kg"
  }
}
```

### ÖKOBAUDAT CSV Format
The CSV should include columns for:
- ID/UUID
- Name
- Category
- Density (kg/m³)
- GWP-total or GWP100
- PENRT or PENR
- Unit reference

## Advanced Features

### Custom Element Filtering
```python
from IfcLCA.utils import selector

# Filter by complex criteria
elements = selector.filter_elements(ifc_file, {
    'ifc_class': 'IfcWall',
    'material': 'Concrete*',
    'property': {'IsExternal': True}
})
```

### Material Layer Analysis
```python
# Get detailed material information
for element in ifc_file.by_type('IfcElement'):
    materials = selector.get_element_materials(element)
    for mat_info in materials:
        print(f"Material: {mat_info['name']}")
        if mat_info['layer_thickness']:
            print(f"  Layer thickness: {mat_info['layer_thickness']}")
        if mat_info['fraction']:
            print(f"  Fraction: {mat_info['fraction']}")
```

## Examples

See the `examples/` directory for:
- `comprehensive_example.py`: Full workflow demonstration
- Integration with Blender via IfcLCA-blend

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the LICENSE file for details.

## Acknowledgments

- IfcOpenShell community for the excellent IFC toolkit
- KBOB and ÖKOBAUDAT for providing open environmental data
