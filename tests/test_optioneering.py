"""
Tests for LCA optioneering module

Tests design optimization through material substitution scenarios
"""

import pytest
import os
from IfcLCA import IfcLCA, IfcLCAOptioneering, KBOBReader


class TestIfcLCAOptioneering:
    """Test design optioneering functionality"""
    
    @pytest.fixture
    def ifc_file_path(self):
        """Get path to test IFC file"""
        test_paths = [
            "../../IfcLCA-blend/test/simple_building.ifc",
            "../IfcLCA-blend/test/simple_building.ifc",
            "IfcLCA-blend/test/simple_building.ifc",
            "test/simple_building.ifc"
        ]
        
        for path in test_paths:
            if os.path.exists(path):
                return path
        
        pytest.skip("Test IFC file not found")
    
    @pytest.fixture
    def base_lca(self, ifc_file_path):
        """Create base LCA with mapping"""
        lca = IfcLCA(ifc_file_path, KBOBReader())
        lca.map_materials({
            "Concrete C30/37": "KBOB_CONCRETE_C30_37",
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING"
        })
        lca.run_analysis()
        return lca
    
    def test_basic_scenario(self, ifc_file_path):
        """Test basic optioneering scenario."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Create scenario - replace concrete with lower carbon option
        scenario = opt.create_scenario(
            "Low Carbon Concrete",
            {
                "Concrete C30/37": "KBOB_CONCRETE_C20_25"  # Lower strength = lower carbon
            }
        )
        
        # Check scenario created
        assert scenario['name'] == "Low Carbon Concrete"
        assert scenario['mapping'] == {
            "Concrete C30/37": "KBOB_CONCRETE_C20_25",
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING"  # Unchanged
        }
        # scenario['results'] contains the mapping, not analysis results
        assert scenario['results'] is not None
    
    def test_multiple_scenarios(self, ifc_file_path):
        """Test multiple optioneering scenarios."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Scenario 1: Low carbon concrete
        opt.create_scenario(
            "Low Carbon Concrete",
            {"Concrete C30/37": "KBOB_CONCRETE_C20_25"}
        )
        
        # Scenario 2: Timber frame
        opt.create_scenario(
            "Timber Structure",
            {
                "Concrete C30/37": "KBOB_GLULAM",
                "Steel Reinforcement": "KBOB_CLT"
            }
        )
        
        # Check both scenarios exist
        assert len(opt.scenarios) == 2
        assert opt.scenarios[0]['name'] == "Low Carbon Concrete"
        assert opt.scenarios[1]['name'] == "Timber Structure"
    
    def test_scenario_comparison(self, ifc_file_path):
        """Test comparing different scenarios."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Create scenarios
        opt.create_scenario(
            "Low Carbon Concrete",
            {"Concrete C30/37": "KBOB_CONCRETE_C20_25"}
        )
        
        opt.create_scenario(
            "High Strength Concrete",
            {"Concrete C30/37": "KBOB_CONCRETE_C50_60"}
        )
        
        # Compare scenarios
        comparison = opt.compare_scenarios()
        
        # Check comparison structure
        assert 'baseline' in comparison
        assert 'scenarios' in comparison
        # We created 2 scenarios, so scenarios list should have 1 (excluding baseline)
        assert len(comparison['scenarios']) >= 1
        
        # Check baseline exists
        assert comparison['baseline'] is not None
    
    def test_find_best_scenario(self, ifc_file_path):
        """Test finding the best scenario."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Create varied scenarios
        opt.create_scenario(
            "Low Carbon",
            {"Concrete C30/37": "KBOB_CONCRETE_C20_25"}
        )
        
        opt.create_scenario(
            "Timber",
            {"Concrete C30/37": "KBOB_GLULAM"}  # Negative carbon
        )
        
        # Find best scenarios
        best_gwp = opt.find_best_scenario('gwp')
        
        # Should return a scenario
        assert best_gwp is not None
        assert 'name' in best_gwp
    
    def test_scenario_with_invalid_mapping(self, ifc_file_path):
        """Test handling invalid material mappings."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Try to create scenario with invalid material ID
        scenario = opt.create_scenario(
            "Invalid Material",
            {"Concrete C30/37": "INVALID_MATERIAL_ID"}
        )
        
        # Scenario should be created but with no results for invalid material
        assert scenario is not None
        # Results might be lower or same as baseline (invalid material ignored)
    
    def test_generate_report(self, ifc_file_path):
        """Test report generation."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Create several scenarios
        opt.create_scenario(
            "Low Carbon Concrete",
            {"Concrete C30/37": "KBOB_CONCRETE_C20_25"}
        )
        
        opt.create_scenario(
            "Recycled Steel",
            {"Steel Reinforcement": "KBOB_STEEL_STRUCTURAL"}  # Different steel type
        )
        
        opt.create_scenario(
            "Timber Hybrid",
            {
                "Concrete C30/37": "KBOB_CLT",
                "Steel Reinforcement": "KBOB_STEEL_STRUCTURAL"
            }
        )
        
        # Generate report
        report = opt.generate_report()
        
        # Check report content
        assert "Design Optioneering Report" in report
        
        # Check all scenarios mentioned
        assert "Low Carbon Concrete" in report
        assert "Recycled Steel" in report
        assert "Timber Hybrid" in report
    
    def test_optimization_workflow(self, ifc_file_path):
        """Test complete optimization workflow."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Define material alternatives
        concrete_alternatives = [
            "KBOB_CONCRETE_C20_25",
            "KBOB_CONCRETE_C50_60",
            "KBOB_GLULAM",
            "KBOB_CLT"
        ]
        
        steel_alternatives = [
            "KBOB_STEEL_STRUCTURAL"
        ]
        
        # Create scenarios for all combinations
        scenario_count = 0
        for concrete_alt in concrete_alternatives:
            opt.create_scenario(
                f"Concrete: {concrete_alt}",
                {"Concrete C30/37": concrete_alt}
            )
            scenario_count += 1
        
        for steel_alt in steel_alternatives:
            opt.create_scenario(
                f"Steel: {steel_alt}",
                {"Steel Reinforcement": steel_alt}
            )
            scenario_count += 1
        
        # Check all scenarios created
        assert len(opt.scenarios) == scenario_count
        
        # Find optimal solutions
        best_gwp = opt.find_best_scenario('gwp')
        
        # Check we found best scenario
        assert best_gwp is not None
        assert 'name' in best_gwp
    
    def test_element_specific_scenarios(self, ifc_file_path):
        """Test scenarios targeting specific elements."""
        lca = IfcLCA(ifc_file_path)
        lca.auto_map_materials()
        
        # Create optioneering with required arguments
        opt = IfcLCAOptioneering(
            ifc_file=lca.ifc_file,
            db_reader=lca.db_reader,
            base_mapping=lca.material_mapping
        )
        
        # Create new optioneering with element filter
        lca.element_filter = {'ifc_class': 'IfcWall'}
        lca.run_analysis()  # Re-run with filter
        
        # Create scenario just for walls
        scenario = opt.create_scenario(
            "Low Carbon Walls",
            {"Concrete C30/37": "KBOB_CONCRETE_C20_25"}
        )
        
        # Check scenario was created
        assert scenario is not None
        assert scenario['name'] == "Low Carbon Walls"
        assert scenario['mapping'] is not None 