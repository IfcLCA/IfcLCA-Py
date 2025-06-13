"""
IFC LCA Core Module

Provides high-level utilities for LCA workflows including material mapping,
quantity extraction, and analysis coordination.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import Dict, List, Tuple, Any, Optional, Set, Union
from .db_reader import IfcLCADBReader, KBOBReader
from .analysis import IfcLCAAnalysis
from .utils import selector


class IfcLCA:
    """
    High-level interface for IFC Life Cycle Assessment.
    
    This class provides utilities for:
    - Automatic material discovery and mapping
    - Quantity extraction and validation
    - Coordinating analysis workflows
    """
    
    def __init__(self, ifc_file: Union[str, ifcopenshell.file], 
                 db_reader: Optional[IfcLCADBReader] = None,
                 database_type: str = 'KBOB',
                 database_path: Optional[str] = None):
        """
        Initialize IfcLCA interface.
        
        Args:
            ifc_file: IFC file path or ifcopenshell file object
            db_reader: Environmental database reader (optional)
            database_type: Type of database if db_reader not provided
            database_path: Path to database file if db_reader not provided
        """
        # Handle file path or file object
        if isinstance(ifc_file, str):
            self.ifc_file = ifcopenshell.open(ifc_file)
        else:
            self.ifc_file = ifc_file
            
        # Handle database reader
        if db_reader is None:
            if database_type.upper() == 'KBOB' and database_path:
                from .db_reader import KBOBReader
                self.db_reader = KBOBReader(database_path)
            else:
                from .db_reader import get_database_reader
                self.db_reader = get_database_reader(database_type, database_path)
        else:
            self.db_reader = db_reader
            
        self._material_cache = None
        self._element_cache = {}
        self.material_mapping = {}
        self.analysis = None
        self.element_filter = None
    
    def discover_materials(self) -> List[Dict[str, Any]]:
        """
        Discover all materials in the IFC model.
        
        Returns:
            List of material information dictionaries with keys:
            - name: Material name
            - elements: Number of elements using this material
            - categories: List of IFC element types using this material
        """
        materials = self.get_all_materials()
        result = []
        
        # Get more detailed info for each material
        summary = self.get_material_summary()
        
        for mat_name, count, mat_type in materials:
            mat_info = summary.get(mat_name, {})
            result.append({
                'name': mat_name,
                'elements': count,
                'categories': mat_info.get('element_types', []),
                'type': mat_type,
                'volume': mat_info.get('total_volume', 0)
            })
        
        return result
    
    def map_material(self, material_name: str, database_id: str) -> None:
        """
        Map a single material to a database entry.
        
        Args:
            material_name: Name of material in IFC
            database_id: ID in environmental database
        """
        # Validate database ID exists
        if self.db_reader.get_material_data(database_id):
            self.material_mapping[material_name] = database_id
    
    def map_materials(self, mapping: Union[Dict[str, str], str, None] = None, 
                     database_id: Optional[str] = None) -> None:
        """
        Map materials to database entries.
        
        Args:
            mapping: Either a dictionary {material: db_id} or a material name
            database_id: Database ID (required if mapping is a string)
        """
        if isinstance(mapping, dict):
            # Batch mapping
            for mat_name, db_id in mapping.items():
                self.map_material(mat_name, db_id)
        elif isinstance(mapping, str) and database_id:
            # Single material mapping
            self.map_material(mapping, database_id)
        else:
            raise ValueError("Invalid arguments for map_materials")
    
    def auto_map_materials(self, confidence_threshold: float = 0.6) -> Tuple[List[str], List[str]]:
        """
        Attempt to automatically map IFC materials to database entries.
        
        Args:
            confidence_threshold: Minimum confidence for auto-mapping (0-1)
            
        Returns:
            Tuple of (mapped_materials, unmapped_materials)
        """
        materials = self.discover_materials()
        mapped = []
        unmapped = []
        
        for mat_info in materials:
            mat_name = mat_info['name']
            
            # Get suggestions
            suggestions = self.get_mapping_suggestions(mat_name)
            
            if suggestions:
                # Use best match if it meets threshold
                best_match = suggestions[0]
                if best_match['confidence'] >= confidence_threshold:
                    self.material_mapping[mat_name] = best_match['id']
                    mapped.append(mat_name)
                    print(f"Auto-mapped '{mat_name}' to '{best_match['name']}' (confidence: {best_match['confidence']:.2f})")
                else:
                    # Try to find a partial match
                    for suggestion in suggestions:
                        if suggestion['confidence'] >= confidence_threshold * 0.8:  # Lower threshold for partial matches
                            self.material_mapping[mat_name] = suggestion['id']
                            mapped.append(mat_name)
                            print(f"Auto-mapped '{mat_name}' to '{suggestion['name']}' (confidence: {suggestion['confidence']:.2f})")
                            break
                    else:
                        unmapped.append(mat_name)
            else:
                unmapped.append(mat_name)
        
        return mapped, unmapped
    
    def get_mapping_suggestions(self, material_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get database suggestions for a material name.
        
        Args:
            material_name: Material name to find suggestions for
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestions with confidence scores
        """
        # Synonym dictionary for common mappings
        synonyms = {
            'steel reinforcement': 'reinforcing steel (92% recycled)',
            'reinforcement steel': 'reinforcing steel (92% recycled)',
            'reinforcing steel': 'reinforcing steel (92% recycled)',
        }
        suggestions = []
        # Synonym direct match
        material_lower = material_name.lower()
        if material_lower in synonyms:
            # Try to find the synonym in the database
            matches = self.db_reader.search_materials(synonyms[material_lower])
            for match in matches[:limit]:
                suggestions.append({
                    'id': match['id'],
                    'name': match['name'],
                    'category': match['category'],
                    'confidence': 1.0
                })
            if suggestions:
                return suggestions
        
        # Direct search
        matches = self.db_reader.search_materials(material_name)
        
        # Calculate confidence scores
        material_words = set(material_lower.split())
        
        for match in matches[:limit]:
            match_name_lower = match['name'].lower()
            match_words = set(match_name_lower.split())
            
            # Calculate confidence score using multiple factors
            confidence = 0.0
            
            # Exact match
            if material_lower == match_name_lower:
                confidence = 1.0
            else:
                # Word overlap
                common_words = material_words.intersection(match_words)
                word_overlap = len(common_words) / max(len(material_words), len(match_words))
                
                # Jaccard similarity
                jaccard = len(common_words) / len(material_words.union(match_words)) if material_words.union(match_words) else 0
                
                # Substring match
                if material_lower in match_name_lower or match_name_lower in material_lower:
                    substring_score = 0.8
                else:
                    # Check for partial word matches
                    partial_matches = sum(1 for w1 in material_words for w2 in match_words if w1 in w2 or w2 in w1)
                    substring_score = min(0.6, partial_matches / max(len(material_words), len(match_words)))
                
                # Category match bonus
                category_bonus = 0.0
                if match.get('category'):
                    category_words = set(match['category'].lower().split())
                    category_overlap = len(material_words.intersection(category_words)) / max(len(material_words), len(category_words))
                    category_bonus = category_overlap * 0.2
                
                # Boost for high Jaccard similarity
                jaccard_bonus = 0.0
                if jaccard > 0.5:
                    jaccard_bonus = 0.3 * jaccard
                
                # Combine scores with weights
                confidence = (word_overlap * 0.4) + (substring_score * 0.2) + category_bonus + jaccard_bonus
            
            suggestions.append({
                'id': match['id'],
                'name': match['name'],
                'category': match['category'],
                'confidence': confidence
            })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return suggestions
    
    def validate_mapping(self) -> Tuple[bool, List[str]]:
        """
        Validate that all materials in the model are mapped.
        
        Returns:
            Tuple of (is_valid, missing_materials)
        """
        materials = self.discover_materials()
        missing = []
        
        for mat_info in materials:
            if mat_info['name'] not in self.material_mapping:
                missing.append(mat_info['name'])
        
        return len(missing) == 0, missing
    
    def run_analysis(self, mapping: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Run LCA analysis.
        
        Args:
            mapping: Optional mapping to use (uses self.material_mapping if not provided)
            
        Returns:
            Dictionary with total impacts by database material ID
        """
        if mapping is None:
            mapping = self.material_mapping
        
        # Validate mapping
        valid, missing = self.validate_mapping()
        if not valid and not mapping:
            raise ValueError(f"Material mapping not complete. Missing: {missing}")
        
        # Apply element filter if set
        if self.element_filter:
            # Create a filtered mapping based on element filter
            filtered_mapping = {}
            filter_class = self.element_filter.get('ifc_class')
            
            if filter_class:
                # Only include materials used by the filtered class
                elements = self.ifc_file.by_type(filter_class)
                for element in elements:
                    mats = selector.get_element_materials(element)
                    for mat_info in mats:
                        mat_name = mat_info['name']
                        if mat_name in mapping:
                            filtered_mapping[mat_name] = mapping[mat_name]
                mapping = filtered_mapping
        
        # Run analysis
        self.analysis = IfcLCAAnalysis(self.ifc_file, self.db_reader, mapping)
        return self.analysis.run()
    
    def get_summary(self) -> str:
        """
        Get a text summary of the analysis results.
        
        Returns:
            Formatted text summary
        """
        if not self.analysis:
            return "No analysis has been run yet."
        
        return self.analysis.generate_summary()
    
    def get_detailed_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed analysis results.
        
        Returns:
            Detailed results by material
        """
        if not self.analysis:
            return {}
        
        return self.analysis.get_detailed_results()
    
    def get_results_by_indicator(self) -> Dict[str, Dict[str, float]]:
        """
        Get results organized by environmental indicator.
        
        Returns:
            Results by indicator (gwp, penr, ubp)
        """
        if not self.analysis:
            return {}
        
        return self.analysis.get_results_by_indicator()
    
    # Keep original methods for backward compatibility
    def get_all_materials(self) -> List[Tuple[str, int, str]]:
        """
        Get all unique materials in the IFC model.
        
        Returns:
            List of tuples: (material_name, element_count, material_type)
            where material_type is 'Material', 'Layer', 'Constituent', etc.
        """
        if self._material_cache is not None:
            return self._material_cache
        
        materials_info = {}
        
        # Process all elements
        for element in self.ifc_file.by_type('IfcElement'):
            element_materials = selector.get_element_materials(element)
            
            for mat_info in element_materials:
                mat_name = mat_info['name']
                if mat_name not in materials_info:
                    materials_info[mat_name] = {
                        'count': 0,
                        'type': self._get_material_type(mat_info)
                    }
                materials_info[mat_name]['count'] += 1
        
        # Convert to list format
        result = [
            (name, info['count'], info['type'])
            for name, info in materials_info.items()
        ]
        
        # Sort by count (descending) then name
        result.sort(key=lambda x: (-x[1], x[0]))
        
        self._material_cache = result
        return result
    
    def _get_material_type(self, mat_info: Dict[str, Any]) -> str:
        """Determine the type of material assignment."""
        if mat_info.get('layer_thickness') is not None:
            return 'Layer'
        elif mat_info.get('fraction') is not None:
            return 'Constituent'
        else:
            return 'Material'
    
    def get_quantity(self, element: ifcopenshell.entity_instance, 
                    quantity_name: str = 'GrossVolume') -> Optional[float]:
        """
        Get a specific quantity for an element.
        
        Args:
            element: IFC element
            quantity_name: Name of quantity (default: GrossVolume)
            
        Returns:
            Quantity value or None if not found
        """
        # Try to get from quantity sets
        quantities = ifcopenshell.util.element.get_psets(element, qtos_only=True)
        
        for qset_name, qset_values in quantities.items():
            if quantity_name in qset_values:
                value = qset_values[quantity_name]
                if isinstance(value, (int, float)):
                    return float(value)
        
        return None
    
    def get_elements_missing_quantities(self) -> List[ifcopenshell.entity_instance]:
        """
        Find elements that don't have volume quantities.
        
        Returns:
            List of elements missing GrossVolume or NetVolume
        """
        missing = []
        
        for element in self.ifc_file.by_type('IfcElement'):
            volume = self.get_quantity(element, 'GrossVolume')
            if volume is None:
                volume = self.get_quantity(element, 'NetVolume')
            
            if volume is None or volume <= 0:
                missing.append(element)
        
        return missing
    
    def validate_model_for_lca(self) -> Dict[str, Any]:
        """
        Validate that the IFC model is suitable for LCA.
        
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'total_elements': int,
                'elements_with_materials': int,
                'elements_with_quantities': int,
                'missing_materials': List[element],
                'missing_quantities': List[element],
                'warnings': List[str]
            }
        """
        all_elements = list(self.ifc_file.by_type('IfcElement'))
        elements_with_materials = []
        elements_with_quantities = []
        missing_materials = []
        missing_quantities = []
        warnings = []
        
        for element in all_elements:
            # Check materials
            materials = selector.get_element_materials(element)
            if materials:
                elements_with_materials.append(element)
            else:
                missing_materials.append(element)
            
            # Check quantities
            volume = self.get_quantity(element, 'GrossVolume')
            if volume is None:
                volume = self.get_quantity(element, 'NetVolume')
            
            if volume and volume > 0:
                elements_with_quantities.append(element)
            else:
                missing_quantities.append(element)
        
        # Generate warnings
        material_coverage = len(elements_with_materials) / len(all_elements) if all_elements else 0
        quantity_coverage = len(elements_with_quantities) / len(all_elements) if all_elements else 0
        
        if material_coverage < 0.8:
            warnings.append(f"Only {material_coverage:.0%} of elements have material assignments")
        
        if quantity_coverage < 0.8:
            warnings.append(f"Only {quantity_coverage:.0%} of elements have volume quantities")
        
        # Check units
        units = self.ifc_file.by_type("IfcUnitAssignment")
        if not units:
            warnings.append("No unit assignments found in IFC file")
        
        return {
            'valid': material_coverage > 0.5 and quantity_coverage > 0.5,
            'total_elements': len(all_elements),
            'elements_with_materials': len(elements_with_materials),
            'elements_with_quantities': len(elements_with_quantities),
            'missing_materials': missing_materials,
            'missing_quantities': missing_quantities,
            'material_coverage': material_coverage,
            'quantity_coverage': quantity_coverage,
            'warnings': warnings
        }
    
    def get_material_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a summary of materials and their usage in the model.
        
        Returns:
            Dictionary with material statistics:
            {
                material_name: {
                    'elements': int,
                    'total_volume': float,
                    'element_types': Set[str],
                    'layers': List[Dict]  # If material is used in layers
                }
            }
        """
        summary = {}
        
        for element in self.ifc_file.by_type('IfcElement'):
            element_type = element.is_a()
            materials = selector.get_element_materials(element)
            volume = self.get_quantity(element, 'GrossVolume') or 0
            
            for mat_info in materials:
                mat_name = mat_info['name']
                
                if mat_name not in summary:
                    summary[mat_name] = {
                        'elements': 0,
                        'total_volume': 0,
                        'element_types': set(),
                        'layers': []
                    }
                
                summary[mat_name]['elements'] += 1
                summary[mat_name]['element_types'].add(element_type)
                
                # Calculate material volume based on fraction or layer thickness
                if mat_info.get('fraction'):
                    mat_volume = volume * mat_info['fraction']
                elif mat_info.get('layer_thickness') and volume > 0:
                    # Approximate layer volume (assumes uniform thickness)
                    # This is simplified - real calculation would need surface area
                    mat_volume = volume * 0.1  # Placeholder
                else:
                    mat_volume = volume
                
                summary[mat_name]['total_volume'] += mat_volume
                
                # Store layer info if applicable
                if mat_info.get('layer_thickness'):
                    summary[mat_name]['layers'].append({
                        'thickness': mat_info['layer_thickness'],
                        'element': element.GlobalId
                    })
        
        # Convert sets to lists for serialization
        for mat_data in summary.values():
            mat_data['element_types'] = list(mat_data['element_types'])
        
        return summary