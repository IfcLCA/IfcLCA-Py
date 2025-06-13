"""
Tests for LCA reporting module

Tests report generation in multiple formats
"""

import pytest
import os
import tempfile
import json
import csv
from IfcLCA import IfcLCA, IfcLCAReporter


class TestIfcLCAReporter:
    """Test LCA reporting functionality"""
    
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
    def completed_analysis(self, ifc_file_path):
        """Create completed LCA analysis"""
        from IfcLCA import KBOBReader
        db_reader = KBOBReader()
        lca = IfcLCA(ifc_file_path, db_reader)
        lca.map_materials({
            "Concrete C30/37": "KBOB_CONCRETE_C30_37",
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING"
        })
        lca.run_analysis()
        return lca.analysis
    
    def test_text_report(self, completed_analysis):
        """Test generating text report"""
        reporter = IfcLCAReporter(completed_analysis)
        
        # Generate text report to string
        report = reporter.generate_text_report()
        
        # Check report content
        assert "IFC LCA Analysis Report" in report
        assert "=" * 60 in report  # Header separator
        
        # Check sections
        assert "Project Information" in report
        assert "Environmental Impact Results" in report
        assert "Material Details" in report
        
        # Check data
        assert "Concrete C30/37" in report
        assert "Steel Reinforcement" in report
        assert "GWP" in report
        assert "Total" in report or "TOTAL" in report
    
    def test_text_report_to_file(self, completed_analysis):
        """Test saving text report to file"""
        reporter = IfcLCAReporter(completed_analysis)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            # Generate report to file
            reporter.generate_text_report(temp_path)
            
            # Check file exists and has content
            assert os.path.exists(temp_path)
            with open(temp_path, 'r') as f:
                content = f.read()
            
            assert len(content) > 100
            assert "IFC LCA Analysis Report" in content
        finally:
            os.unlink(temp_path)
    
    def test_csv_report(self, completed_analysis):
        """Test generating CSV report"""
        reporter = IfcLCAReporter(completed_analysis)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            # Generate CSV report
            reporter.generate_csv_report(temp_path)
            
            # Read and verify CSV
            with open(temp_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Check headers
            assert 'Material' in rows[0]
            assert 'Database ID' in rows[0]
            assert 'Volume (m³)' in rows[0]
            assert 'Mass (kg)' in rows[0]
            assert 'GWP (kg CO₂-eq)' in rows[0]
            
            # Check data rows
            assert len(rows) >= 3  # 2 materials + total
            
            # Find concrete row
            concrete_row = next(r for r in rows if r['Material'] == 'Concrete C30/37')
            assert float(concrete_row['Mass (kg)']) > 0
            assert float(concrete_row['GWP (kg CO₂-eq)']) > 0
            
            # Check total row
            total_row = next(r for r in rows if r['Material'] == 'TOTAL')
            assert float(total_row['GWP (kg CO₂-eq)']) > 0
        finally:
            os.unlink(temp_path)
    
    def test_json_report(self, completed_analysis):
        """Test generating JSON report"""
        reporter = IfcLCAReporter(completed_analysis)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Generate JSON report
            reporter.generate_json_report(temp_path)
            
            # Read and verify JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            # Check structure
            assert 'project' in data
            assert 'timestamp' in data
            assert 'summary' in data
            assert 'materials' in data
            assert 'totals' in data
            
            # Check summary
            assert data['summary']['total_materials'] == 2
            assert data['summary']['total_elements'] > 0
            
            # Check materials
            assert len(data['materials']) == 2
            concrete = next(m for m in data['materials'] if m['name'] == 'Concrete C30/37')
            assert concrete['volume'] > 0
            assert concrete['mass'] > 0
            assert concrete['impacts']['gwp'] > 0
            
            # Check totals
            assert data['totals']['gwp'] > 0
            assert data['totals']['penr'] > 0
            assert data['totals']['ubp'] > 0
        finally:
            os.unlink(temp_path)
    
    def test_visualization_data(self, completed_analysis):
        """Test getting visualization-ready data"""
        reporter = IfcLCAReporter(completed_analysis)
        
        # Get bar chart data
        bar_data = reporter.get_bar_chart_data('gwp')
        
        # Check structure
        assert 'labels' in bar_data
        assert 'values' in bar_data
        assert len(bar_data['labels']) == len(bar_data['values'])
        assert len(bar_data['labels']) == 2  # Two materials
        
        # Check data
        assert 'Concrete C30/37' in bar_data['labels']
        assert all(v > 0 for v in bar_data['values'])
        
        # Get pie chart data
        pie_data = reporter.get_pie_chart_data('gwp')
        assert 'labels' in pie_data
        assert 'values' in pie_data
        assert 'percentages' in pie_data
        assert sum(pie_data['percentages']) == pytest.approx(100, rel=0.01)
    
    def test_multi_indicator_visualization(self, completed_analysis):
        """Test visualization data for multiple indicators"""
        reporter = IfcLCAReporter(completed_analysis)
        
        # Get data for all indicators
        multi_data = reporter.get_multi_indicator_data()
        
        # Check structure
        assert 'materials' in multi_data
        assert 'indicators' in multi_data
        assert 'data' in multi_data
        
        # Check indicators
        assert 'gwp' in multi_data['indicators']
        assert 'penr' in multi_data['indicators']
        assert 'ubp' in multi_data['indicators']
        
        # Check data matrix
        assert len(multi_data['data']) == len(multi_data['materials'])
        assert all(len(row) == len(multi_data['indicators']) for row in multi_data['data'])
    
    def test_empty_analysis_report(self):
        """Test reporting with empty analysis"""
        from IfcLCA import IfcLCAAnalysis, KBOBReader
        import ifcopenshell
        
        # Create empty analysis
        empty_file = ifcopenshell.file()
        analysis = IfcLCAAnalysis(empty_file, KBOBReader(), {})
        analysis.run()
        
        reporter = IfcLCAReporter(analysis)
        
        # Should handle empty results gracefully
        text_report = reporter.generate_text_report()
        assert "No materials analyzed" in text_report or "Total: 0" in text_report
        
        # Visualization data should be empty but valid
        bar_data = reporter.get_bar_chart_data('gwp')
        assert bar_data['labels'] == []
        assert bar_data['values'] == []
    
    def test_report_formatting(self, completed_analysis):
        """Test report formatting options"""
        reporter = IfcLCAReporter(completed_analysis)
        
        # Test with custom decimal places
        reporter.decimal_places = 1
        report = reporter.generate_text_report()
        
        # Check numbers are formatted with 1 decimal
        # This is implementation dependent, but we can check for patterns
        import re
        # Look for numbers with exactly 1 decimal place
        decimal_pattern = r'\d+\.\d{1}(?!\d)'
        matches = re.findall(decimal_pattern, report)
        assert len(matches) > 0  # Should find some 1-decimal numbers
    
    def test_comparative_report(self, ifc_file_path):
        """Test comparative reporting between scenarios"""
        from IfcLCA import KBOBReader
        db_reader = KBOBReader()
        
        # Create two analyses with different mappings
        lca1 = IfcLCA(ifc_file_path, db_reader)
        lca1.map_materials({
            "Concrete C30/37": "KBOB_CONCRETE_C30_37",
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING"
        })
        lca1.run_analysis()
        
        lca2 = IfcLCA(ifc_file_path, db_reader)
        lca2.map_materials({
            "Concrete C30/37": "KBOB_CONCRETE_C20_25",  # Lower carbon
            "Steel Reinforcement": "KBOB_STEEL_REINFORCING"
        })
        lca2.run_analysis()
        
        # Create reporters
        reporter1 = IfcLCAReporter(lca1.analysis)
        reporter2 = IfcLCAReporter(lca2.analysis)
        
        # Get data for comparison
        data1 = reporter1.get_bar_chart_data('gwp')
        data2 = reporter2.get_bar_chart_data('gwp')
        
        # Total for scenario 2 should be lower (lower carbon concrete)
        total1 = sum(data1['values'])
        total2 = sum(data2['values'])
        assert total2 < total1 