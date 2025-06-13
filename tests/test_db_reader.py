"""
Tests for IfcLCA database readers

Tests KBOB, ÖKOBAUDAT, and custom database readers
"""

import pytest
import os
import json
import csv
import tempfile
from IfcLCA.db_reader import (
    IfcLCADBReader,
    KBOBReader,
    OkobaudatReader,
    CustomJSONReader,
    get_database_reader
)


class TestKBOBReader:
    """Test KBOB database reader functionality"""
    
    def test_default_kbob_data(self):
        """Test loading default KBOB data"""
        reader = KBOBReader()
        
        # Check that default data is loaded
        assert len(reader.db) > 0
        assert 'KBOB_CONCRETE_C30_37' in reader.db
        
        # Check material data structure
        concrete_data = reader.get_material_data('KBOB_CONCRETE_C30_37')
        assert concrete_data['name'] == 'Concrete C30/37'
        assert concrete_data['category'] == 'Concrete'
        assert concrete_data['density'] == 2400
        assert concrete_data['gwp'] == 0.100
        assert concrete_data['penr'] == 1.01
        assert concrete_data['ubp'] == 125
        assert concrete_data['unit'] == 'kg'
        
        # Check backward compatibility
        assert concrete_data['carbon_per_unit'] == 0.100
    
    def test_custom_kbob_file(self):
        """Test loading custom KBOB JSON file"""
        # Create temporary JSON file
        custom_data = {
            "TEST_MATERIAL": {
                "name": "Test Material",
                "category": "Test",
                "density": 1000,
                "gwp": 0.5,
                "penr": 5.0,
                "ubp": 50,
                "unit": "kg"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(custom_data, f)
            temp_path = f.name
        
        try:
            reader = KBOBReader(temp_path)
            
            # Check custom data is loaded
            assert 'TEST_MATERIAL' in reader.db
            test_data = reader.get_material_data('TEST_MATERIAL')
            assert test_data['name'] == 'Test Material'
            assert test_data['gwp'] == 0.5
        finally:
            os.unlink(temp_path)
    
    def test_material_search(self):
        """Test material search functionality"""
        reader = KBOBReader()
        
        # Search for concrete materials
        results = reader.search_materials('concrete')
        assert len(results) > 0
        assert all('concrete' in r['name'].lower() for r in results)
        
        # Search for steel
        results = reader.search_materials('steel')
        assert len(results) >= 2  # Reinforcing and structural steel
        
        # Search by category
        results = reader.search_materials('wood')
        assert len(results) >= 2  # Glulam and CLT
    
    def test_get_all_materials(self):
        """Test getting all materials"""
        reader = KBOBReader()
        materials = reader.get_all_materials()
        
        assert len(materials) == len(reader.db)
        # Check sorting by category and name
        prev_category = ""
        for mat in materials:
            assert 'id' in mat
            assert 'name' in mat
            assert 'category' in mat
            assert 'gwp' in mat
            if mat['category'] == prev_category:
                # Within same category, should be sorted by name
                pass
            prev_category = mat['category']


class TestOkobaudatReader:
    """Test ÖKOBAUDAT database reader"""
    
    def test_okobaudat_csv_loading(self):
        """Test loading ÖKOBAUDAT CSV file"""
        # Create temporary CSV file with ÖKOBAUDAT format
        csv_content = """ID;Name;Category;Rohdichte;GWP-total;PENRT;Bezugseinheit
1.1.01;Beton C20/25;Beton;2300;0,0896;0,951;kg
1.1.02;Beton C25/30;Beton;2350;0,0941;1,01;kg
1.2.01;Bewehrungsstahl;Stahl;7850;0,769;9,46;kg
2.1.01;Vollziegel;Mauerwerk;1800;0,160;2,51;kg
3.1.01;Brettschichtholz;Holz;470;-0,655;8,66;kg"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            reader = OkobaudatReader(temp_path)
            
            # Check materials loaded
            assert len(reader.db) == 5
            assert '1.1.01' in reader.db
            
            # Check data parsing (note: German decimal comma should be converted)
            concrete = reader.get_material_data('1.1.01')
            assert concrete['name'] == 'Beton C20/25'
            assert concrete['density'] == 2300
            assert concrete['gwp'] == pytest.approx(0.0896)
            assert concrete['penr'] == pytest.approx(0.951)
            
            # Check negative values (biogenic carbon)
            timber = reader.get_material_data('3.1.01')
            assert timber['gwp'] == pytest.approx(-0.655)
        finally:
            os.unlink(temp_path)
    
    def test_okobaudat_unit_conversion(self):
        """Test ÖKOBAUDAT unit conversion from m³ to kg"""
        csv_content = """ID;Name;Category;Rohdichte;GWP-total;PENRT;Bezugseinheit
4.1.01;Dämmstoff;Dämmung;100;329;8860;m³"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            reader = OkobaudatReader(temp_path)
            
            # Check unit conversion (per m³ to per kg)
            insulation = reader.get_material_data('4.1.01')
            assert insulation['gwp'] == pytest.approx(329 / 100)  # 3.29 kg CO2/kg
            assert insulation['penr'] == pytest.approx(8860 / 100)  # 88.6 MJ/kg
        finally:
            os.unlink(temp_path)
    
    def test_missing_csv_file(self):
        """Test error handling for missing CSV file"""
        with pytest.raises(ValueError, match="CSV file not found"):
            OkobaudatReader("/non/existent/file.csv")


class TestCustomJSONReader:
    """Test custom JSON database reader"""
    
    def test_custom_json_loading(self):
        """Test loading custom JSON database"""
        custom_data = {
            "CUSTOM_MAT_1": {
                "name": "Custom Material 1",
                "category": "Custom",
                "density": 1500,
                "gwp": 0.2,
                "penr": 2.0,
                "ubp": 200
            },
            "CUSTOM_MAT_2": {
                "name": "Custom Material 2",
                "category": "Custom",
                "density": 800,
                "carbon_per_unit": 0.15  # Test legacy field
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(custom_data, f)
            temp_path = f.name
        
        try:
            reader = CustomJSONReader(temp_path)
            
            # Check materials loaded
            assert len(reader.db) == 2
            
            # Check data normalization
            mat1 = reader.get_material_data('CUSTOM_MAT_1')
            assert mat1['gwp'] == 0.2
            assert mat1['carbon_per_unit'] == 0.2  # Legacy field populated
            
            mat2 = reader.get_material_data('CUSTOM_MAT_2')
            assert mat2['gwp'] == 0.15  # From carbon_per_unit
            assert mat2['carbon_per_unit'] == 0.15
            assert mat2['penr'] == 0  # Default value
        finally:
            os.unlink(temp_path)


class TestDatabaseFactory:
    """Test database reader factory function"""
    
    def test_get_kbob_reader(self):
        """Test getting KBOB reader"""
        reader = get_database_reader('KBOB')
        assert isinstance(reader, KBOBReader)
        assert len(reader.db) > 0
        
        # Test case insensitive
        reader = get_database_reader('kbob')
        assert isinstance(reader, KBOBReader)
    
    def test_get_okobaudat_reader(self):
        """Test getting ÖKOBAUDAT reader with path"""
        # Create dummy CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ID;Name\n1;Test")
            temp_path = f.name
        
        try:
            reader = get_database_reader('OKOBAUDAT', temp_path)
            assert isinstance(reader, OkobaudatReader)
        finally:
            os.unlink(temp_path)
        
        # Test missing path
        with pytest.raises(ValueError, match="requires a database file path"):
            get_database_reader('OKOBAUDAT')
    
    def test_unknown_database_type(self):
        """Test error for unknown database type"""
        with pytest.raises(ValueError, match="Unknown database type"):
            get_database_reader('INVALID')


class TestDatabaseReaderInterface:
    """Test the abstract database reader interface"""
    
    def test_interface_consistency(self):
        """Test all readers implement the same interface"""
        reader = KBOBReader()
        
        # Check required methods exist
        assert hasattr(reader, 'get_material_data')
        assert hasattr(reader, 'search_materials')
        assert hasattr(reader, 'get_all_materials')
        
        # Check method signatures
        material_data = reader.get_material_data('KBOB_CONCRETE_C30_37')
        assert isinstance(material_data, dict)
        
        search_results = reader.search_materials('concrete')
        assert isinstance(search_results, list)
        
        all_materials = reader.get_all_materials()
        assert isinstance(all_materials, list) 