"""Export utilities for reconciliation results."""

import os
from pathlib import Path
from typing import Dict
from recon_engine import ReconEngine
from models import ReconResult


class Exporter:
    """Handles exporting reconciliation results to CSV files."""
    
    # Mapping of table names to friendly file names
    TABLE_FILE_NAMES = {
        "exact_matches": "exact_matches.csv",
        "matches_with_date_note": "matches_with_date_note.csv",
        "amount_variances": "amount_variances.csv",
        "missing_in_b": "missing_in_source_b.csv",
        "missing_in_a": "missing_in_source_a.csv"
    }
    
    def __init__(self, engine: ReconEngine):
        """
        Initialize exporter with a reconciliation engine.
        
        Args:
            engine: ReconEngine instance with reconciliation results
        """
        self.engine = engine
    
    def export_table(self, table_name: str, output_dir: str) -> str:
        """
        Export a single result table to CSV.
        
        Args:
            table_name: Name of the table to export
            output_dir: Directory to save the CSV file
            
        Returns:
            Path to the exported file
        """
        os.makedirs(output_dir, exist_ok=True)
        file_name = self.TABLE_FILE_NAMES.get(table_name, f"{table_name}.csv")
        output_path = os.path.join(output_dir, file_name)
        
        self.engine.export_table(table_name, output_path)
        return output_path
    
    def export_all(self, result: ReconResult) -> Dict[str, str]:
        """
        Export all result tables to CSV files.
        
        Args:
            result: ReconResult containing config with output directory
            
        Returns:
            Dictionary mapping table names to exported file paths
        """
        output_dir = result.config.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        exported = {}
        
        tables = [
            result.exact_matches_table,
            result.date_note_table,
            result.amount_variance_table,
            result.missing_in_b_table,
            result.missing_in_a_table
        ]
        
        for table_name in tables:
            try:
                path = self.export_table(table_name, output_dir)
                exported[table_name] = path
            except Exception as e:
                print(f"Error exporting {table_name}: {e}")
        
        return exported
