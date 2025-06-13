"""
IFC LCA Reporter Module

Generates reports and exports results in various formats including:
- Text summaries
- CSV exports
- JSON data
- Visualization data
"""

import json
import csv
from typing import Dict, List, Any, Optional, TextIO
from datetime import datetime
import os
from .analysis import IfcLCAAnalysis
from .optioneering import IfcLCAOptioneering
import io


class IfcLCAReporter:
    """
    Class for generating LCA reports in various formats.
    
    Supports:
    - Human-readable text reports
    - CSV exports for spreadsheet analysis
    - JSON exports for web integration
    - Chart data preparation
    """
    
    def __init__(self, analysis_or_project: Any = None):
        """
        Initialize reporter.
        
        Args:
            analysis_or_project: Either an IfcLCAAnalysis instance or project name string
        """
        if isinstance(analysis_or_project, IfcLCAAnalysis):
            # Legacy API - initialized with analysis
            self.analysis = analysis_or_project
            self.project_name = "IFC LCA Analysis"
        elif isinstance(analysis_or_project, str):
            # New API - initialized with project name
            self.project_name = analysis_or_project
            self.analysis = None
        else:
            # Default
            self.project_name = "Unnamed Project"
            self.analysis = analysis_or_project if analysis_or_project else None
            
        self.timestamp = datetime.now()
        self.decimal_places = 2  # For formatting
    
    def generate_text_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate text report (legacy API).
        
        Args:
            output_file: Optional file path to save report
            
        Returns:
            Report content as string
        """
        if not self.analysis:
            return "No analysis available for reporting."
            
        report = self._generate_text_report(self.analysis)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def generate_csv_report(self, output_file: str) -> None:
        """
        Generate CSV report (legacy API).
        
        Args:
            output_file: File path to save CSV report
        """
        if not self.analysis:
            raise ValueError("No analysis available for reporting.")
            
        report = self._generate_csv_report(self.analysis)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def generate_json_report(self, output_file: str) -> None:
        """
        Generate JSON report (legacy API).
        
        Args:
            output_file: File path to save JSON report
        """
        if not self.analysis:
            raise ValueError("No analysis available for reporting.")
            
        report = self._generate_json_report(self.analysis)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def get_bar_chart_data(self, indicator: str = 'gwp') -> Dict[str, List]:
        """
        Get data for bar chart visualization.
        
        Args:
            indicator: Environmental indicator ('gwp', 'penr', 'ubp')
            
        Returns:
            Dictionary with 'labels' and 'values' lists
        """
        if not self.analysis:
            return {'labels': [], 'values': []}
            
        detailed_results = self.analysis.get_detailed_results()
        
        labels = []
        values = []
        
        for query, details in detailed_results.items():
            labels.append(details['material_name'])
            values.append(details.get(indicator, 0))
        
        return {'labels': labels, 'values': values}
    
    def get_pie_chart_data(self, indicator: str = 'gwp') -> Dict[str, List]:
        """
        Get data for pie chart visualization.
        
        Args:
            indicator: Environmental indicator ('gwp', 'penr', 'ubp')
            
        Returns:
            Dictionary with 'labels', 'values', and 'percentages'
        """
        if not self.analysis:
            return {'labels': [], 'values': [], 'percentages': []}
            
        bar_data = self.get_bar_chart_data(indicator)
        total = sum(bar_data['values'])
        
        percentages = []
        for value in bar_data['values']:
            if total > 0:
                percentages.append(value / total * 100)
            else:
                percentages.append(0)
        
        return {
            'labels': bar_data['labels'],
            'values': bar_data['values'],
            'percentages': percentages
        }
    
    def get_multi_indicator_data(self) -> Dict[str, Any]:
        """
        Get data for multi-indicator visualization.
        
        Returns:
            Dictionary with materials, indicators, and data matrix
        """
        if not self.analysis:
            return {'materials': [], 'indicators': [], 'data': []}
            
        detailed_results = self.analysis.get_detailed_results()
        
        materials = []
        data = []
        
        for query, details in detailed_results.items():
            materials.append(details['material_name'])
            data.append([
                details.get('gwp', 0),
                details.get('penr', 0),
                details.get('ubp', 0)
            ])
        
        return {
            'materials': materials,
            'indicators': ['gwp', 'penr', 'ubp'],
            'data': data
        }
    
    def generate_analysis_report(self, analysis: IfcLCAAnalysis, 
                               output_format: str = 'text') -> str:
        """
        Generate a report from LCA analysis results.
        
        Args:
            analysis: Completed IfcLCAAnalysis instance
            output_format: 'text', 'json', or 'csv'
            
        Returns:
            Report content as string
        """
        if output_format == 'text':
            return self._generate_text_report(analysis)
        elif output_format == 'json':
            return self._generate_json_report(analysis)
        elif output_format == 'csv':
            return self._generate_csv_report(analysis)
        else:
            raise ValueError(f"Unknown format: {output_format}")
    
    def _generate_text_report(self, analysis: IfcLCAAnalysis) -> str:
        """
        Generate text report from analysis results.
        
        Args:
            analysis: Completed IfcLCAAnalysis instance
            
        Returns:
            Formatted text report
        """
        if not analysis:
            return "No analysis available for reporting."
            
        detailed_results = analysis.get_detailed_results()
        results_by_indicator = analysis.get_results_by_indicator()
        
        # Calculate totals
        total_gwp = sum(results_by_indicator['gwp'].values())
        total_penr = sum(results_by_indicator['penr'].values())
        total_ubp = sum(results_by_indicator['ubp'].values())
        
        # Start report
        report = []
        report.append("=" * 60)
        report.append("IFC LCA Analysis Report")
        report.append("Generated: " + self.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        report.append("=" * 60)
        report.append("")
        
        # Project Information
        report.append("Project Information")
        report.append("-" * 30)
        report.append(f"Project: {self.project_name}")
        report.append(f"Analysis Date: {self.timestamp.strftime('%Y-%m-%d')}")
        report.append("")
        
        # Environmental Impact Results section
        report.append("Environmental Impact Results")
        report.append("")
        
        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 30)
        report.append(f"Total GWP:  {total_gwp:,.1f} kg CO₂-eq")
        report.append(f"Total PEnr: {total_penr:,.0f} MJ")
        report.append(f"Total UBP:  {total_ubp:,.0f} points")
        report.append("")
        
        # Material Details
        report.append("Material Details")
        report.append("-" * 30)
        
        if not detailed_results:
            report.append("No materials analyzed")
        else:
            for query, details in detailed_results.items():
                report.append("")
                report.append(details['material_name'])
                report.append(f"  Query: {query}")
                report.append(f"  Elements: {details['elements']}")
                report.append(f"  Volume: {details['total_volume']:.2f} m³")
                report.append(f"  Mass: {details['total_mass']:,.0f} kg")
                gwp_percent = (details['gwp'] / total_gwp * 100) if total_gwp > 0 else 0
                report.append(f"  GWP: {details['gwp']:,.1f} kg CO₂-eq ({gwp_percent:.1f}%)")
                report.append(f"  PEnr: {details['penr']:,.0f} MJ")
                report.append(f"  UBP: {details['ubp']:,.0f} points")
        
        # Top Contributors
        report.append("")
        report.append("=" * 30)
        report.append("TOP CONTRIBUTORS (by GWP)")
        report.append("-" * 30)
        
        # Sort materials by GWP
        sorted_materials = sorted(
            detailed_results.items(),
            key=lambda x: x[1]['gwp'],
            reverse=True
        )
        
        for i, (query, details) in enumerate(sorted_materials, 1):
            gwp_percent = (details['gwp'] / total_gwp * 100) if total_gwp > 0 else 0
            report.append(f"{i}. {details['material_name']}: {gwp_percent:.1f}%")
        
        return "\n".join(report)
    
    def _generate_json_report(self, analysis: IfcLCAAnalysis) -> str:
        """
        Generate JSON report from analysis results.
        
        Args:
            analysis: Completed IfcLCAAnalysis instance
            
        Returns:
            JSON report content
        """
        if not analysis:
            return "{}"
            
        detailed_results = analysis.get_detailed_results()
        results_by_indicator = analysis.get_results_by_indicator()
        
        # Calculate totals
        total_gwp = sum(results_by_indicator['gwp'].values())
        total_penr = sum(results_by_indicator['penr'].values())
        total_ubp = sum(results_by_indicator['ubp'].values())
        
        # Prepare materials list
        materials = []
        for query, details in detailed_results.items():
            materials.append({
                'name': details['material_name'],
                'query': query,
                'elements': details['elements'],
                'volume': details['total_volume'],
                'mass': details['total_mass'],
                'impacts': {
                    'gwp': details['gwp'],
                    'penr': details['penr'],
                    'ubp': details['ubp']
                }
            })
        
        # Create report structure
        total_elements = sum(details['elements'] for details in detailed_results.values())
        report = {
            'project': self.project_name,
            'timestamp': self.timestamp.isoformat(),
            'summary': {
                'total_gwp': total_gwp,
                'total_penr': total_penr,
                'total_ubp': total_ubp,
                'total_materials': len(materials),
                'total_elements': total_elements
            },
            'totals': {
                'gwp': total_gwp,
                'penr': total_penr,
                'ubp': total_ubp
            },
            'materials': materials,
            'results_by_indicator': results_by_indicator,
            'detailed_results': detailed_results
        }
        
        return json.dumps(report, indent=2)
    
    def _generate_csv_report(self, analysis: IfcLCAAnalysis) -> str:
        """
        Generate CSV report from analysis results.
        
        Args:
            analysis: Completed IfcLCAAnalysis instance
            
        Returns:
            CSV report content
        """
        if not analysis:
            return "No analysis available for reporting."
            
        detailed_results = analysis.get_detailed_results()
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'Material', 'Database ID', 'Elements', 'Volume (m³)', 'Mass (kg)',
            'GWP (kg CO₂-eq)', 'PEnr (MJ)', 'UBP (points)'
        ])
        
        writer.writeheader()
        
        for query, details in detailed_results.items():
            writer.writerow({
                'Material': details['material_name'],
                'Database ID': details.get('database_id', ''),
                'Elements': details['elements'],
                'Volume (m³)': f"{details['total_volume']:.2f}",
                'Mass (kg)': f"{details['total_mass']:.0f}",
                'GWP (kg CO₂-eq)': f"{details['gwp']:.1f}",
                'PEnr (MJ)': f"{details['penr']:.0f}",
                'UBP (points)': f"{details['ubp']:.0f}"
            })
        
        # Add total row to CSV
        results_by_indicator = analysis.get_results_by_indicator()
        writer.writerow({
            'Material': 'TOTAL',
            'Database ID': '',
            'Elements': '',
            'Volume (m³)': '',
            'Mass (kg)': '',
            'GWP (kg CO₂-eq)': f"{sum(results_by_indicator['gwp'].values()):.1f}",
            'PEnr (MJ)': f"{sum(results_by_indicator['penr'].values()):.0f}",
            'UBP (points)': f"{sum(results_by_indicator['ubp'].values()):.0f}"
        })
        
        return output.getvalue()
    
    def generate_optioneering_report(self, optioneering: IfcLCAOptioneering,
                                   output_format: str = 'text') -> str:
        """
        Generate report from optioneering results.
        
        Args:
            optioneering: Completed IfcLCAOptioneering instance
            output_format: 'text', 'json', or 'csv'
            
        Returns:
            Report content as string
        """
        if output_format == 'text':
            return optioneering.generate_report()
        elif output_format == 'json':
            return json.dumps(optioneering.export_comparison_data(), indent=2)
        elif output_format == 'csv':
            return self._generate_optioneering_csv(optioneering)
        else:
            raise ValueError(f"Unknown format: {output_format}")
    
    def _generate_optioneering_csv(self, optioneering: IfcLCAOptioneering) -> str:
        """Generate CSV report for optioneering results."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['IFC LCA Optioneering Report', self.project_name])
        writer.writerow(['Generated', self.timestamp.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Column headers
        writer.writerow([
            'Option',
            'Description',
            'GWP (kg CO₂-eq)',
            'PEnr (MJ)',
            'UBP (points)',
            'Improvement (%)'
        ])
        
        # Data rows
        for result in optioneering.results:
            writer.writerow([
                result['option_name'],
                result.get('description', ''),
                f"{result['summary']['total_gwp']:.1f}",
                f"{result['summary']['total_penr']:.0f}",
                f"{result['summary']['total_ubp']:.0f}",
                f"{result['improvement']:.1f}"
            ])
        
        return output.getvalue()
    
    def save_report(self, content: str, filename: str, directory: str = '.'):
        """
        Save report content to file.
        
        Args:
            content: Report content
            filename: Output filename
            directory: Output directory (default: current)
        """
        filepath = os.path.join(directory, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Report saved to: {filepath}")
    
    def generate_visualization_data(self, analysis: IfcLCAAnalysis) -> Dict[str, Any]:
        """
        Generate data structured for visualization libraries.
        
        Returns:
            Dictionary with chart-ready data
        """
        detailed_results = analysis.get_detailed_results()
        results_by_indicator = analysis.get_results_by_indicator()
        
        # Prepare data for different chart types
        materials = []
        gwp_values = []
        penr_values = []
        ubp_values = []
        volumes = []
        
        for query, details in detailed_results.items():
            materials.append(details['material_name'])
            gwp_values.append(details['gwp'])
            penr_values.append(details.get('penr', 0))
            ubp_values.append(details.get('ubp', 0))
            volumes.append(details['total_volume'])
        
        # Calculate percentages
        total_gwp = sum(gwp_values)
        gwp_percentages = [
            (v / total_gwp * 100) if total_gwp > 0 else 0
            for v in gwp_values
        ]
        
        return {
            'materials': materials,
            'indicators': {
                'gwp': {
                    'values': gwp_values,
                    'percentages': gwp_percentages,
                    'total': total_gwp,
                    'unit': 'kg CO₂-eq'
                },
                'penr': {
                    'values': penr_values,
                    'total': sum(penr_values),
                    'unit': 'MJ'
                },
                'ubp': {
                    'values': ubp_values,
                    'total': sum(ubp_values),
                    'unit': 'points'
                }
            },
            'quantities': {
                'volumes': volumes,
                'unit': 'm³'
            },
            'chart_types': {
                'pie': {
                    'labels': materials,
                    'values': gwp_values
                },
                'bar': {
                    'categories': materials,
                    'series': [
                        {'name': 'GWP', 'data': gwp_values},
                        {'name': 'PEnr', 'data': penr_values}
                    ]
                },
                'treemap': {
                    'data': [
                        {
                            'name': mat,
                            'value': gwp,
                            'percentage': pct
                        }
                        for mat, gwp, pct in zip(materials, gwp_values, gwp_percentages)
                    ]
                }
            }
        }
    
    def generate_comparison_chart_data(self, optioneering: IfcLCAOptioneering) -> Dict[str, Any]:
        """
        Generate data for comparing optioneering options.
        
        Returns:
            Dictionary with comparison chart data
        """
        comparison_data = optioneering.export_comparison_data()
        
        # Add chart-specific formatting
        comparison_data['charts'] = {
            'improvement_bar': {
                'categories': comparison_data['options'],
                'values': comparison_data['indicators']['improvement']
            },
            'gwp_comparison': {
                'categories': comparison_data['options'],
                'values': comparison_data['indicators']['gwp']
            },
            'waterfall': self._prepare_waterfall_data(optioneering.results)
        }
        
        return comparison_data
    
    def _prepare_waterfall_data(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare data for waterfall chart showing cumulative improvements."""
        if not results:
            return []
        
        waterfall_data = []
        baseline = results[0]['summary']['total_gwp']
        current_value = baseline
        
        waterfall_data.append({
            'name': 'Baseline',
            'value': baseline,
            'type': 'total'
        })
        
        for result in results[1:]:
            reduction = current_value - result['summary']['total_gwp']
            if reduction != 0:
                waterfall_data.append({
                    'name': result['option_name'],
                    'value': -reduction,
                    'type': 'change'
                })
                current_value = result['summary']['total_gwp']
        
        waterfall_data.append({
            'name': 'Final',
            'value': current_value,
            'type': 'total'
        })
        
        return waterfall_data