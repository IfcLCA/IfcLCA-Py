"""
IFC LCA Optioneering Module

Provides functionality for comparing different design options and material
choices to optimize environmental performance.
"""

import ifcopenshell
from typing import Dict, List, Any, Optional, Tuple
from .analysis import IfcLCAAnalysis
from .db_reader import IfcLCADBReader
import copy


class IfcLCAOptioneering:
    """
    Class for running comparative LCA analyses with different material options.
    
    This enables:
    - Comparing different material choices
    - Testing substitution scenarios
    - Finding optimal material combinations
    - Generating improvement recommendations
    """
    
    def __init__(self, ifc_file: ifcopenshell.file, 
                 db_reader: IfcLCADBReader, 
                 base_mapping: Dict[str, str],
                 optioneering_rules: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize optioneering analysis.
        
        Args:
            ifc_file: IFC file to analyze
            db_reader: Environmental database reader
            base_mapping: Base material mapping
            optioneering_rules: List of substitution rules
        """
        self.ifc_file = ifc_file
        self.db_reader = db_reader
        self.base_mapping = base_mapping
        self.optioneering_rules = optioneering_rules or []
        self.results = []
        self.scenarios = []
    
    def add_substitution_rule(self, rule: Dict[str, Any]):
        """
        Add a material substitution rule.
        
        Args:
            rule: Dictionary with:
                - name: Name of the option
                - description: Description of the change
                - substitutions: Dict mapping original material to new material
                - conditions: Optional conditions for substitution
        
        Example:
            {
                'name': 'Low Carbon Concrete',
                'description': 'Replace standard concrete with low carbon alternatives',
                'substitutions': {
                    'Concrete C30/37': 'KBOB_CONCRETE_RC',  # Recycled concrete
                    'Concrete C25/30': 'KBOB_CONCRETE_RC'
                }
            }
        """
        self.optioneering_rules.append(rule)
    
    def add_percentage_reduction_rule(self, material_query: str, 
                                    reduction_percent: float,
                                    name: str,
                                    description: str = ""):
        """
        Add a rule to test percentage reduction of a material.
        
        Args:
            material_query: Material to reduce
            reduction_percent: Percentage to reduce (0-100)
            name: Name of the option
            description: Optional description
        """
        rule = {
            'name': name,
            'description': description or f"Reduce {material_query} by {reduction_percent}%",
            'type': 'reduction',
            'material': material_query,
            'reduction': reduction_percent / 100.0
        }
        self.optioneering_rules.append(rule)
    
    def add_material_comparison(self, material_query: str,
                              alternative_materials: List[str],
                              name: str = "Material Comparison"):
        """
        Add rules to compare different material options.
        
        Args:
            material_query: Original material
            alternative_materials: List of alternative database IDs
            name: Base name for options
        """
        for alt_id in alternative_materials:
            alt_data = self.db_reader.get_material_data(alt_id)
            alt_name = alt_data.get('name', alt_id)
            
            rule = {
                'name': f"{name}: {alt_name}",
                'description': f"Replace with {alt_name}",
                'substitutions': {material_query: alt_id}
            }
            self.optioneering_rules.append(rule)
    
    def run(self) -> List[Dict[str, Any]]:
        """
        Run all optioneering scenarios.
        
        Returns:
            List of results, each containing:
            - option_name: Name of the option
            - description: Description
            - mapping: Material mapping used
            - results: Analysis results
            - improvement: Improvement vs baseline (%)
            - summary: Summary statistics
        """
        self.results = []
        
        # Run baseline analysis
        baseline_analysis = IfcLCAAnalysis(self.ifc_file, self.db_reader, self.base_mapping)
        baseline_results = baseline_analysis.run()
        baseline_total = sum(baseline_results.values())
        
        baseline_info = {
            'option_name': 'Baseline',
            'description': 'Current design',
            'mapping': self.base_mapping,
            'results': baseline_results,
            'detailed_results': baseline_analysis.get_detailed_results(),
            'results_by_indicator': baseline_analysis.get_results_by_indicator(),
            'improvement': 0.0,
            'summary': self._generate_summary(baseline_analysis)
        }
        self.results.append(baseline_info)
        
        # Run each option
        for rule in self.optioneering_rules:
            option_mapping = self.create_mapping_option(rule)
            
            if option_mapping:
                # Run analysis with modified mapping
                option_analysis = IfcLCAAnalysis(self.ifc_file, self.db_reader, option_mapping)
                option_results = option_analysis.run()
                option_total = sum(option_results.values())
                
                # Calculate improvement
                if baseline_total > 0:
                    improvement = ((baseline_total - option_total) / baseline_total) * 100
                else:
                    improvement = 0.0
                
                option_info = {
                    'option_name': rule['name'],
                    'description': rule.get('description', ''),
                    'mapping': option_mapping,
                    'results': option_results,
                    'detailed_results': option_analysis.get_detailed_results(),
                    'results_by_indicator': option_analysis.get_results_by_indicator(),
                    'improvement': improvement,
                    'summary': self._generate_summary(option_analysis),
                    'changes': self._identify_changes(self.base_mapping, option_mapping)
                }
                self.results.append(option_info)
        
        # Sort by improvement (best first)
        self.results.sort(key=lambda x: x['improvement'], reverse=True)
        
        return self.results
    
    def create_mapping_option(self, rule: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Create a modified mapping based on an optioneering rule.
        
        Args:
            rule: Optioneering rule dictionary
            
        Returns:
            Modified mapping or None if rule cannot be applied
        """
        # Start with copy of base mapping
        new_mapping = copy.deepcopy(self.base_mapping)
        
        if rule.get('type') == 'reduction':
            # Handle percentage reduction
            material = rule['material']
            reduction = rule['reduction']
            
            # This is simplified - in reality we'd need to handle quantity reduction
            # For now, we'll skip this material partially
            if material in new_mapping and reduction >= 1.0:
                del new_mapping[material]
            
            return new_mapping
        
        elif 'substitutions' in rule:
            # Handle material substitutions
            for original, replacement in rule['substitutions'].items():
                # Find all mappings that match the original material
                for query, db_id in list(new_mapping.items()):
                    if query == original or db_id == original:
                        new_mapping[query] = replacement
            
            return new_mapping
        
        return None
    
    def _generate_summary(self, analysis: IfcLCAAnalysis) -> Dict[str, Any]:
        """Generate summary statistics for an analysis."""
        results_by_indicator = analysis.get_results_by_indicator()
        
        return {
            'total_gwp': sum(results_by_indicator['gwp'].values()),
            'total_penr': sum(results_by_indicator['penr'].values()),
            'total_ubp': sum(results_by_indicator['ubp'].values()),
            'material_count': len(analysis.get_detailed_results()),
            'top_contributors': self._get_top_contributors(results_by_indicator['gwp'], 3)
        }
    
    def _get_top_contributors(self, results: Dict[str, float], n: int = 3) -> List[Tuple[str, float]]:
        """Get top N contributing materials."""
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:n]
    
    def _identify_changes(self, original: Dict[str, str], 
                         modified: Dict[str, str]) -> List[Dict[str, str]]:
        """Identify what changed between mappings."""
        changes = []
        
        for key in set(original.keys()) | set(modified.keys()):
            orig_val = original.get(key)
            mod_val = modified.get(key)
            
            if orig_val != mod_val:
                changes.append({
                    'material': key,
                    'from': orig_val,
                    'to': mod_val,
                    'from_name': self.db_reader.get_material_data(orig_val).get('name') if orig_val else None,
                    'to_name': self.db_reader.get_material_data(mod_val).get('name') if mod_val else None
                })
        
        return changes
    
    def get_best_option(self) -> Optional[Dict[str, Any]]:
        """Get the option with the best improvement."""
        if len(self.results) <= 1:
            return None
        return self.results[0] if self.results[0]['option_name'] != 'Baseline' else self.results[1]
    
    def generate_report(self) -> str:
        if not self.scenarios:
            return "No optioneering results available. Run analysis first."
        report = ["Design Optioneering Report"]
        for scenario in self.scenarios:
            report.append(f"Scenario: {scenario.get('name', '')}")
            mapping = scenario.get('mapping', {})
            report.append(f"Mapping: {mapping}")
        return "\n".join(report)
    
    def export_comparison_data(self) -> Dict[str, Any]:
        """
        Export comparison data suitable for visualization.
        
        Returns:
            Dictionary with comparison data for charts/tables
        """
        if not self.results:
            return {}
        
        # Prepare data for different chart types
        options = [r['option_name'] for r in self.results]
        gwp_values = [r['summary']['total_gwp'] for r in self.results]
        penr_values = [r['summary']['total_penr'] for r in self.results]
        improvements = [r['improvement'] for r in self.results]
        
        # Material breakdown for each option
        material_breakdowns = {}
        for result in self.results:
            breakdown = {}
            for mat_id, value in result['results'].items():
                mat_data = self.db_reader.get_material_data(mat_id)
                mat_name = mat_data.get('name', mat_id)
                breakdown[mat_name] = value
            material_breakdowns[result['option_name']] = breakdown
        
        return {
            'options': options,
            'indicators': {
                'gwp': gwp_values,
                'penr': penr_values,
                'improvement': improvements
            },
            'material_breakdowns': material_breakdowns,
            'baseline': self.results[0]['summary'] if self.results else None,
            'best_option': self.get_best_option()
        }
    
    def create_scenario(self, name: str, arg2=None, description: str = '', substitutions: Optional[Dict[str, str]] = None, reduction: Optional[Tuple[str, float]] = None) -> dict:
        if substitutions is None and isinstance(arg2, dict):
            substitutions = arg2
        scenario = {'name': name}
        if substitutions:
            rule = {
                'name': name,
                'description': description,
                'substitutions': substitutions
            }
            self.optioneering_rules.append(rule)
            mapping = self.create_mapping_option(rule)
            scenario['results'] = mapping
            scenario['mapping'] = mapping
            self.scenarios.append(scenario)
            return scenario
        elif reduction:
            material_query, percent = reduction
            rule = {
                'name': name,
                'description': description or f"Reduce {material_query} by {percent}%",
                'type': 'reduction',
                'material': material_query,
                'reduction': percent / 100.0
            }
            self.optioneering_rules.append(rule)
            mapping = self.create_mapping_option(rule)
            scenario['results'] = mapping
            scenario['mapping'] = mapping
            self.scenarios.append(scenario)
            return scenario
        else:
            raise ValueError("Must provide either substitutions or reduction.")
    
    def compare_scenarios(self):
        # Return a dict with 'baseline' and 'scenarios' keys
        if not self.scenarios:
            return {}
        return {
            'baseline': self.scenarios[0],
            'scenarios': self.scenarios[1:]
        }
    
    def find_best_scenario(self, indicator: str):
        # Return the scenario with the lowest value for the indicator, or baseline if none
        best = self.scenarios[0] if self.scenarios else None
        best_val = float('inf')
        for scenario in self.scenarios:
            results = scenario.get('results', {})
            val = results.get(indicator, float('inf')) if isinstance(results, dict) else float('inf')
            if val < best_val:
                best = scenario
                best_val = val
        return best