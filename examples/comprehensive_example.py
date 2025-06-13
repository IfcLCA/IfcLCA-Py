#!/usr/bin/env python3
"""
Comprehensive Example of IfcLCA-Py Usage

This example demonstrates all major features of the IfcLCA-Py package:
1. Loading and validating IFC files
2. Material discovery and mapping
3. Running LCA analysis
4. Optioneering for optimization
5. Generating reports
"""

import os
import sys
import ifcopenshell

# Add parent directory to path if running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from IfcLCA import (
    IfcLCA,
    IfcLCAAnalysis,
    IfcLCAOptioneering,
    IfcLCAReporter,
    KBOBReader,
    get_database_reader
)


def main():
    """Run comprehensive IfcLCA example."""
    
    # 1. Setup
    print("=== IfcLCA-Py Comprehensive Example ===\n")
    
    # Load IFC file
    ifc_path = "../IfcLCA-blend/test/simple_building.ifc"
    if not os.path.exists(ifc_path):
        print(f"Error: Test IFC file not found at {ifc_path}")
        print("Please ensure you have the test file from the IfcLCA-blend directory")
        return
    
    print(f"Loading IFC file: {ifc_path}")
    ifc_file = ifcopenshell.open(ifc_path)
    print(f"Loaded: {ifc_file.schema} with {len(ifc_file.by_type('IfcElement'))} elements\n")
    
    # 2. Initialize database reader
    print("Loading KBOB environmental database...")
    db_reader = KBOBReader()  # Uses built-in KBOB data
    print(f"Database loaded with {len(db_reader.db)} materials\n")
    
    # 3. Initialize IfcLCA interface
    lca = IfcLCA(ifc_file, db_reader)
    
    # 4. Validate model
    print("Validating IFC model for LCA...")
    validation = lca.validate_model_for_lca()
    print(f"Model validation: {'PASSED' if validation['valid'] else 'FAILED'}")
    print(f"  Total elements: {validation['total_elements']}")
    print(f"  With materials: {validation['elements_with_materials']} ({validation['material_coverage']:.0%})")
    print(f"  With quantities: {validation['elements_with_quantities']} ({validation['quantity_coverage']:.0%})")
    
    if validation['warnings']:
        print("  Warnings:")
        for warning in validation['warnings']:
            print(f"    - {warning}")
    print()
    
    # 5. Discover materials
    print("Discovering materials in the model...")
    materials = lca.get_all_materials()
    print(f"Found {len(materials)} unique materials:")
    for mat_name, count, mat_type in materials:
        print(f"  - {mat_name}: {count} elements ({mat_type})")
    print()
    
    # 6. Auto-map materials
    print("Attempting automatic material mapping...")
    mapping = lca.auto_map_materials()
    
    # Manual adjustments if needed
    if "Steel Reinforcement" in [m[0] for m in materials] and "Steel Reinforcement" not in mapping:
        mapping["Steel Reinforcement"] = "KBOB_STEEL_REINFORCING"
        print("  Manually mapped: Steel Reinforcement -> Reinforcing steel")
    
    print(f"\nMaterial mapping complete: {len(mapping)} materials mapped")
    for ifc_mat, db_id in mapping.items():
        db_data = db_reader.get_material_data(db_id)
        print(f"  {ifc_mat} -> {db_data['name']}")
    print()
    
    # 7. Run baseline analysis
    print("Running baseline LCA analysis...")
    analysis = lca.run_analysis(mapping)
    
    # Display results
    print("\nBaseline Results:")
    print(analysis.generate_summary())
    
    # 8. Optioneering - explore alternatives
    print("\n\n=== OPTIONEERING ANALYSIS ===")
    print("Exploring low-carbon alternatives...\n")
    
    optioneering = IfcLCAOptioneering(ifc_file, db_reader, mapping)
    
    # Add substitution options
    optioneering.add_substitution_rule({
        'name': 'Recycled Concrete',
        'description': 'Replace standard concrete with recycled concrete',
        'substitutions': {
            'Concrete C30/37': 'KBOB_CONCRETE_RC'
        }
    })
    
    optioneering.add_substitution_rule({
        'name': 'Timber Structure',
        'description': 'Replace concrete with CLT where possible',
        'substitutions': {
            'Concrete C30/37': 'KBOB_TIMBER_CLT'
        }
    })
    
    # Compare different concrete options
    if 'Concrete C30/37' in mapping:
        optioneering.add_material_comparison(
            'Concrete C30/37',
            ['KBOB_CONCRETE_C25_30', 'KBOB_CONCRETE_RC', 'KBOB_CONCRETE_C35_45'],
            name="Concrete Options"
        )
    
    # Run optioneering
    print("Running optioneering scenarios...")
    opt_results = optioneering.run()
    
    # Show results
    print(optioneering.generate_report())
    
    # 9. Generate reports
    print("\n\n=== GENERATING REPORTS ===")
    reporter = IfcLCAReporter(project_name="Simple Building Example")
    
    # Text report
    text_report = reporter.generate_analysis_report(analysis, 'text')
    reporter.save_report(text_report, 'lca_report.txt')
    
    # CSV report
    csv_report = reporter.generate_analysis_report(analysis, 'csv')
    reporter.save_report(csv_report, 'lca_report.csv')
    
    # JSON report
    json_report = reporter.generate_analysis_report(analysis, 'json')
    reporter.save_report(json_report, 'lca_report.json')
    
    # Optioneering reports
    opt_text = reporter.generate_optioneering_report(optioneering, 'text')
    reporter.save_report(opt_text, 'optioneering_report.txt')
    
    opt_csv = reporter.generate_optioneering_report(optioneering, 'csv')
    reporter.save_report(opt_csv, 'optioneering_report.csv')
    
    print("\nReports generated:")
    print("  - lca_report.txt")
    print("  - lca_report.csv")
    print("  - lca_report.json")
    print("  - optioneering_report.txt")
    print("  - optioneering_report.csv")
    
    # 10. Visualization data
    print("\nGenerating visualization data...")
    viz_data = reporter.generate_visualization_data(analysis)
    print(f"Visualization data prepared for {len(viz_data['materials'])} materials")
    print(f"Chart types available: {', '.join(viz_data['chart_types'].keys())}")
    
    # 11. Material summary
    print("\n\n=== MATERIAL USAGE SUMMARY ===")
    material_summary = lca.get_material_summary()
    for mat_name, summary in material_summary.items():
        print(f"\n{mat_name}:")
        print(f"  Used in: {summary['elements']} elements")
        print(f"  Total volume: {summary['total_volume']:.2f} m³")
        print(f"  Element types: {', '.join(summary['element_types'])}")
        if summary['layers']:
            print(f"  Used in {len(summary['layers'])} layered constructions")
    
    print("\n\nExample completed successfully!")


if __name__ == "__main__":
    main() 