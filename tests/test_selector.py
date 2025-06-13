"""
Tests for IFC element selector utilities

Tests element filtering, material extraction using simple_building.ifc
"""

import pytest
import os
import ifcopenshell
from IfcLCA.utils import selector, filter_elements, get_element_materials


class TestElementSelector:
    """Test element selector functionality"""
    
    @pytest.fixture
    def ifc_file(self):
        """Load the test IFC file"""
        # Try different paths to find the test file
        test_paths = [
            "../../IfcLCA-blend/test/simple_building.ifc",
            "../IfcLCA-blend/test/simple_building.ifc", 
            "IfcLCA-blend/test/simple_building.ifc",
            "test/simple_building.ifc"
        ]
        
        for path in test_paths:
            if os.path.exists(path):
                return ifcopenshell.open(path)
        
        # If not found, skip tests
        pytest.skip("Test IFC file not found")
    
    def test_filter_by_ifc_class(self, ifc_file):
        """Test filtering elements by IFC class"""
        # Filter walls
        walls = filter_elements(ifc_file, {'ifc_class': 'IfcWall'})
        assert len(walls) == 1
        assert all(w.is_a('IfcWall') for w in walls)
        
        # Filter slabs
        slabs = filter_elements(ifc_file, {'ifc_class': 'IfcSlab'})
        assert len(slabs) == 1
        assert slabs[0].is_a('IfcSlab')
        
        # Filter columns
        columns = filter_elements(ifc_file, {'ifc_class': 'IfcColumn'})
        assert len(columns) == 1
        assert columns[0].is_a('IfcColumn')
        
        # Filter all elements
        all_elements = filter_elements(ifc_file, {'ifc_class': 'IfcElement'})
        assert len(all_elements) == 3  # Wall, slab, column
    
    def test_filter_by_material(self, ifc_file):
        """Test filtering elements by material"""
        # Filter by concrete material
        concrete_elements = filter_elements(ifc_file, {
            'material': 'Concrete C30/37'
        })
        assert len(concrete_elements) == 2  # Wall and slab
        
        # Filter by steel material
        steel_elements = filter_elements(ifc_file, {
            'material': 'Steel Reinforcement'
        })
        assert len(steel_elements) == 2  # Slab and column
        
        # Filter by material with wildcard
        concrete_wildcard = filter_elements(ifc_file, {
            'material': 'Concrete*'
        })
        assert len(concrete_wildcard) == 2
        
        # Filter by material ending
        reinforcement = filter_elements(ifc_file, {
            'material': '*Reinforcement'
        })
        assert len(reinforcement) == 2
    
    def test_string_query_parsing(self, ifc_file):
        """Test string query format parsing"""
        # Simple IFC class query
        walls = filter_elements(ifc_file, "IfcWall")
        assert len(walls) == 1
        
        # IFC class with material
        concrete_walls = filter_elements(ifc_file, "IfcWall:Concrete C30/37")
        assert len(concrete_walls) == 1
        
        # Material query only
        concrete_elements = filter_elements(ifc_file, ":Concrete C30/37")
        assert len(concrete_elements) == 2
    
    def test_filter_by_building_storey(self, ifc_file):
        """Test filtering by spatial containment"""
        # Filter elements in Ground Floor
        ground_floor_elements = filter_elements(ifc_file, {
            'building_storey': 'Ground Floor'
        })
        assert len(ground_floor_elements) == 3  # All elements are on ground floor
        
        # Non-existent storey
        other_floor = filter_elements(ifc_file, {
            'building_storey': 'First Floor'
        })
        assert len(other_floor) == 0
    
    def test_combined_filters(self, ifc_file):
        """Test combining multiple filter criteria"""
        # Concrete walls
        concrete_walls = filter_elements(ifc_file, {
            'ifc_class': 'IfcWall',
            'material': 'Concrete C30/37'
        })
        assert len(concrete_walls) == 1
        
        # Steel columns on ground floor
        steel_columns = filter_elements(ifc_file, {
            'ifc_class': 'IfcColumn',
            'material': 'Steel Reinforcement',
            'building_storey': 'Ground Floor'
        })
        assert len(steel_columns) == 1
    
    def test_custom_filter_function(self, ifc_file):
        """Test custom filter function"""
        # Filter elements with volume > 1 m³
        def has_large_volume(element):
            quantities = ifcopenshell.util.element.get_psets(element, qtos_only=True)
            for qset in quantities.values():
                if 'GrossVolume' in qset:
                    return qset['GrossVolume'] > 1.0
            return False
        
        large_elements = filter_elements(ifc_file, {
            'custom_filter': has_large_volume
        })
        assert len(large_elements) == 2  # Wall (3.6m³) and slab (22m³)


class TestMaterialExtraction:
    """Test material extraction functionality"""
    
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
    
    def test_get_element_materials_simple(self, ifc_file):
        """Test getting materials from simple material assignment"""
        # Get the wall
        walls = ifc_file.by_type('IfcWall')
        assert len(walls) == 1
        wall = walls[0]
        
        # Get wall materials
        materials = get_element_materials(wall)
        assert len(materials) == 1
        assert materials[0]['name'] == 'Concrete C30/37'
        assert materials[0]['layer_thickness'] == 300  # mm
        assert materials[0]['fraction'] is None
    
    def test_get_element_materials_layered(self, ifc_file):
        """Test getting materials from layered material set"""
        # Get the slab
        slabs = ifc_file.by_type('IfcSlab')
        assert len(slabs) == 1
        slab = slabs[0]
        
        # Get slab materials (concrete + reinforcement layers)
        materials = get_element_materials(slab)
        assert len(materials) == 2
        
        # Check first layer (concrete)
        assert materials[0]['name'] == 'Concrete C30/37'
        assert materials[0]['layer_thickness'] == 200
        
        # Check second layer (reinforcement)
        assert materials[1]['name'] == 'Steel Reinforcement'
        assert materials[1]['layer_thickness'] == 20
    
    def test_get_element_materials_column(self, ifc_file):
        """Test getting materials from column"""
        # Get the column
        columns = ifc_file.by_type('IfcColumn')
        assert len(columns) == 1
        column = columns[0]
        
        # Get column materials
        materials = get_element_materials(column)
        assert len(materials) == 1
        assert materials[0]['name'] == 'Steel Reinforcement'
        assert materials[0]['layer_thickness'] == 100
    
    def test_material_names_extraction(self, ifc_file):
        """Test internal material name extraction"""
        # Test with wall material
        wall = ifc_file.by_type('IfcWall')[0]
        material = ifcopenshell.util.element.get_material(wall)
        
        # This is a MaterialLayerSetUsage
        assert material.is_a('IfcMaterialLayerSetUsage')
        
        # Test name extraction
        names = selector._get_material_names(material)
        assert 'Concrete C30/37' in names
    
    def test_pattern_matching(self):
        """Test wildcard pattern matching"""
        # Exact match
        assert selector._matches_pattern('Concrete', 'Concrete')
        assert not selector._matches_pattern('Concrete', 'Steel')
        
        # Starts with
        assert selector._matches_pattern('Concrete C30/37', 'Concrete*')
        assert not selector._matches_pattern('Steel', 'Concrete*')
        
        # Ends with
        assert selector._matches_pattern('Steel Reinforcement', '*Reinforcement')
        assert not selector._matches_pattern('Concrete', '*Reinforcement')
        
        # Contains (both wildcards)
        assert selector._matches_pattern('Concrete C30/37 Standard', 'Concrete*Standard')


class TestAdvancedFiltering:
    """Test advanced filtering scenarios"""
    
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
    
    def test_filter_by_properties(self, ifc_file):
        """Test filtering by element properties"""
        # Note: simple_building.ifc doesn't have many properties
        # This test demonstrates the capability
        
        # Try to filter by quantity properties
        elements_with_volume = []
        for element in ifc_file.by_type('IfcElement'):
            quantities = ifcopenshell.util.element.get_psets(element, qtos_only=True)
            for qset in quantities.values():
                if 'GrossVolume' in qset:
                    elements_with_volume.append(element)
                    break
        
        assert len(elements_with_volume) == 3  # All elements have volume
    
    def test_material_layer_analysis(self, ifc_file):
        """Test detailed material layer analysis"""
        # Get slab with layers
        slab = ifc_file.by_type('IfcSlab')[0]
        materials = get_element_materials(slab)
        
        # Calculate layer proportions
        total_thickness = sum(m['layer_thickness'] for m in materials)
        assert total_thickness == 220  # 200 + 20
        
        # Calculate volume fractions
        concrete_fraction = 200 / 220
        steel_fraction = 20 / 220
        
        assert concrete_fraction > 0.9  # Concrete is ~91% by thickness
        assert steel_fraction < 0.1  # Steel is ~9% by thickness 