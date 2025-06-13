# IfcLCA-Py: Life Cycle Assessment for IFC building models
"""
IfcLCA-Py provides tools for performing Life Cycle Assessment (LCA) on building models
using Industry Foundation Classes (IFC) files and environmental impact databases.
"""

__version__ = '0.1.0a1'
__author__ = 'Louis Trümpler'
__license__ = 'AGPL-3.0'

# Import main classes for easier access
from .analysis import IfcLCAAnalysis
from .db_reader import IfcLCADBReader, KBOBReader, OkobaudatReader, get_database_reader
from .lca import IfcLCA
from .optioneering import IfcLCAOptioneering
from .reporter import IfcLCAReporter

# Define what's available when using "from IfcLCA import *"
__all__ = [
    'IfcLCAAnalysis',
    'IfcLCADBReader',
    'KBOBReader', 
    'OkobaudatReader',
    'get_database_reader',
    'IfcLCA',
    'IfcLCAOptioneering',
    'IfcLCAReporter'
]