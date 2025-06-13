"""
Tests for IFC LCA Analysis module

Tests core LCA calculations, multi-indicator support, and results
"""

import pytest
import os
import ifcopenshell
from IfcLCA import IfcLCAAnalysis, KBOBReader


class TestIfcLCAAnalysis:
    """Test core LCA analysis functionality"""
    
    @pytest.fixture
    def ifc_file(self):
        """Load the test IFC file"""
        test_paths = [
            "../../IfcLCA-blend/test/simple_building.ifc",
            "../IfcLCA-blend/test/simple_building.ifc",
            "IfcLCA-blend/test/simple_building.ifc",
            "test/simple_building.ifc"
        ]
        
        for path in test_paths:
            if os.path.exists(path):
                return ifcopenshell.open(path)
        
        pytest.skip("Test IFC file not found")
    
    @pytest.fixture
    def db_reader(self):
        """Get KBOB database reader"""
        return KBOBReader()
    
    @pytest.fixture
    def simple_mapping(self):
        """Get simple material mapping for test file"""
        return {
            "Concrete C30/37": "KBOB_CONCRETE_C30_37",
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING"
        }
    
    def test_basic_analysis(self, ifc_file, db_reader, simple_mapping):
        """Test basic LCA analysis"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        results = analysis.run()
        
        # Check results structure
        assert isinstance(results, dict)
        assert "KBOB_CONCRETE_C30_37" in results
        assert "KBOB_STEEL_REINFORCING" in results
        
        # Check values are positive
        assert results["KBOB_CONCRETE_C30_37"] > 0
        assert results["KBOB_STEEL_REINFORCING"] > 0
    
    def test_multi_indicator_results(self, ifc_file, db_reader, simple_mapping):
        """Test multi-indicator environmental results"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        analysis.run()
        
        results_by_indicator = analysis.get_results_by_indicator()
        
        # Check all indicators present
        assert 'gwp' in results_by_indicator
        assert 'penr' in results_by_indicator
        assert 'ubp' in results_by_indicator
        
        # Check each indicator has results
        for indicator in ['gwp', 'penr', 'ubp']:
            assert len(results_by_indicator[indicator]) == 2  # Two materials
            assert all(v >= 0 for v in results_by_indicator[indicator].values())
    
    def test_detailed_results(self, ifc_file, db_reader, simple_mapping):
        """Test detailed results with quantities"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        analysis.run()
        
        detailed = analysis.get_detailed_results()
        
        # Check concrete results
        concrete = detailed.get("Concrete C30/37")
        assert concrete is not None
        assert concrete['material_name'] == 'Concrete C30/37'
        assert concrete['elements'] == 2  # Wall and slab
        assert concrete['total_volume'] > 0
        assert concrete['total_mass'] > 0
        assert concrete['gwp'] > 0
        
        # Check steel results
        steel = detailed.get("Steel Reinforcement")
        assert steel is not None
        assert steel['elements'] == 2  # Slab and column
    
    def test_unit_scaling(self, ifc_file, db_reader, simple_mapping):
        """Test unit scaling from mm to m"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        
        # Check unit scale detection (file uses mm)
        assert analysis._unit_scale == 0.001  # mm to m
        
        # Run analysis
        analysis.run()
        detailed = analysis.get_detailed_results()
        
        # Check volumes are in m³
        concrete = detailed["Concrete C30/37"]
        # Wall: 0.3m × 4m × 3m = 3.6 m³
        # Slab: partial volume from 22 m³ total
        assert concrete['total_volume'] > 3.6  # At least wall volume
    
    def test_calculate_concrete_wall(self, ifc_file, db_reader, simple_mapping):
        """Test specific calculation for concrete wall"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        analysis.run()
        
        # Expected calculation for wall:
        # Volume: 3.6 m³
        # Density: 2400 kg/m³ 
        # Mass: 3.6 × 2400 = 8640 kg
        # GWP: 8640 × 0.100 = 864 kg CO₂
        
        results = analysis.results['gwp']
        detailed = analysis.get_detailed_results()
        
        # Check wall contribution (part of concrete total)
        concrete_details = detailed["Concrete C30/37"]
        assert concrete_details['total_volume'] >= 3.6
        assert concrete_details['total_mass'] >= 8640
        assert concrete_details['gwp'] >= 864
    
    def test_calculate_reinforced_slab(self, ifc_file, db_reader, simple_mapping):
        """Test calculation for slab with layers"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        analysis.run()
        
        detailed = analysis.get_detailed_results()
        
        # Slab has 22 m³ total volume
        # Concrete layer: 200mm / 220mm = 90.9%
        # Steel layer: 20mm / 220mm = 9.1%
        
        # Check both materials have contributions from slab
        concrete = detailed["Concrete C30/37"]
        steel = detailed["Steel Reinforcement"]
        
        # Concrete should include slab contribution
        # Expected: ~20 m³ × 2400 kg/m³ × 0.100 = ~4800 kg CO₂
        assert concrete['gwp'] > 4800  # Plus wall contribution
        
        # Steel should include slab contribution  
        # Expected: ~2 m³ × 7850 kg/m³ × 0.750 = ~11775 kg CO₂
        assert steel['gwp'] > 10000  # Significant contribution
    
    def test_empty_mapping(self, ifc_file, db_reader):
        """Test analysis with empty mapping"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, {})
        results = analysis.run()
        
        assert results == {}
        assert analysis.get_detailed_results() == {}
    
    def test_partial_mapping(self, ifc_file, db_reader):
        """Test analysis with partial material mapping"""
        partial_mapping = {
            "Concrete C30/37": "KBOB_CONCRETE_C30_37"
            # Steel not mapped
        }
        
        analysis = IfcLCAAnalysis(ifc_file, db_reader, partial_mapping)
        results = analysis.run()
        
        # Only concrete should have results
        assert len(results) == 1
        assert "KBOB_CONCRETE_C30_37" in results
        assert results["KBOB_CONCRETE_C30_37"] > 0
    
    def test_invalid_database_id(self, ifc_file, db_reader):
        """Test handling of invalid database IDs"""
        invalid_mapping = {
            "Concrete C30/37": "INVALID_ID"
        }
        
        analysis = IfcLCAAnalysis(ifc_file, db_reader, invalid_mapping)
        results = analysis.run()
        
        # Should handle gracefully
        assert results == {} or "INVALID_ID" not in results
    
    def test_summary_generation(self, ifc_file, db_reader, simple_mapping):
        """Test summary text generation"""
        analysis = IfcLCAAnalysis(ifc_file, db_reader, simple_mapping)
        analysis.run()
        
        summary = analysis.generate_summary()
        
        # Check summary contains expected sections
        assert "IFC LCA Analysis Results" in summary
        assert "Material Breakdown" in summary
        assert "TOTALS" in summary
        assert "kg CO₂-eq" in summary
        
        # Check materials are mentioned
        assert "Concrete C30/37" in summary
        assert "Steel" in summary or "Reinforcing steel" in summary


class TestQuantityExtraction:
    """Test quantity extraction from IFC"""
    
    @pytest.fixture
    def ifc_file(self):
        """Load the test IFC file"""
        test_paths = [
            "../../IfcLCA-blend/test/simple_building.ifc",
            "../IfcLCA-blend/test/simple_building.ifc",
            "IfcLCA-blend/test/simple_building.ifc",
            "test/simple_building.ifc"
        ]
        
        for path in test_paths:
            if os.path.exists(path):
                return ifcopenshell.open(path)
        
        pytest.skip("Test IFC file not found")
    
    def test_get_element_volume(self, ifc_file):
        """Test volume extraction from elements"""
        db_reader = KBOBReader()
        analysis = IfcLCAAnalysis(ifc_file, db_reader, {})
        
        # Test wall volume
        wall = ifc_file.by_type('IfcWall')[0]
        volume = analysis._get_element_volume(wall)
        assert volume == pytest.approx(3.6, rel=0.01)  # 3.6 m³
        
        # Test slab volume
        slab = ifc_file.by_type('IfcSlab')[0]
        volume = analysis._get_element_volume(slab)
        assert volume == pytest.approx(22.0, rel=0.01)  # 22 m³
        
        # Test column volume
        column = ifc_file.by_type('IfcColumn')[0]
        volume = analysis._get_element_volume(column)
        assert volume == pytest.approx(0.25, rel=0.01)  # 0.25 m³
    
    def test_material_fraction_calculation(self, ifc_file):
        """Test material fraction calculation for layers"""
        db_reader = KBOBReader()
        analysis = IfcLCAAnalysis(ifc_file, db_reader, {})
        
        # Test slab with two layers
        slab = ifc_file.by_type('IfcSlab')[0]
        
        # Concrete fraction (200mm of 220mm total)
        concrete_fraction = analysis._get_material_fraction(slab, "Concrete C30/37")
        assert concrete_fraction == pytest.approx(200/220, rel=0.01)
        
        # Steel fraction (20mm of 220mm total)
        steel_fraction = analysis._get_material_fraction(slab, "Steel Reinforcement")
        assert steel_fraction == pytest.approx(20/220, rel=0.01)


class TestComplexScenarios:
    """Test complex analysis scenarios"""
    
    @pytest.fixture
    def ifc_file(self):
        """Load the test IFC file"""
        test_paths = [
            "../../IfcLCA-blend/test/simple_building.ifc",
            "../IfcLCA-blend/test/simple_building.ifc",
            "IfcLCA-blend/test/simple_building.ifc",
            "test/simple_building.ifc"
        ]
        
        for path in test_paths:
            if os.path.exists(path):
                return ifcopenshell.open(path)
        
        pytest.skip("Test IFC file not found")
    
    def test_query_based_mapping(self, ifc_file):
        """Test using query strings in mapping"""
        db_reader = KBOBReader()
        
        # Use IFC class queries
        query_mapping = {
            "IfcWall:Concrete*": "KBOB_CONCRETE_C30_37",
            "IfcColumn": "KBOB_STEEL_STRUCTURAL"
        }
        
        analysis = IfcLCAAnalysis(ifc_file, db_reader, query_mapping)
        results = analysis.run()
        
        # Should find wall and column
        assert len(results) == 2
        assert results["KBOB_CONCRETE_C30_37"] > 0  # Wall
        assert results["KBOB_STEEL_STRUCTURAL"] > 0  # Column
    
    def test_total_building_carbon(self, ifc_file):
        """Test total building carbon calculation"""
        db_reader = KBOBReader()
        
        # Map all materials
        full_mapping = {
            "Concrete C30/37": "KBOB_CONCRETE_C30_37",
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING",
            "Brick": "KBOB_BRICK_CLAY"  # Not used in model
        }
        
        analysis = IfcLCAAnalysis(ifc_file, db_reader, full_mapping)
        results = analysis.run()
        
        # Calculate total
        total_gwp = sum(results.values())
        
        # Rough estimate check:
        # Concrete: ~25.6 m³ × 2400 kg/m³ × 0.1 = ~6144 kg CO₂
        # Steel: ~2.25 m³ × 7850 kg/m³ × 0.75 = ~13246 kg CO₂
        # Total: ~19390 kg CO₂
        
        assert total_gwp > 15000  # Should be significant
        assert total_gwp < 25000  # But not unrealistic 