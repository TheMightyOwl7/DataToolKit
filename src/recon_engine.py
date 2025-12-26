"""DuckDB-based reconciliation engine."""

import duckdb
from pathlib import Path
from typing import List, Optional
from models import ReconConfig, ReconResult, ReconSummary


class ReconEngine:
    """Reconciliation engine using DuckDB for large dataset processing."""
    
    def __init__(self):
        """Initialize with in-memory DuckDB connection."""
        self.conn = duckdb.connect(":memory:")
        self._source_a_loaded = False
        self._source_b_loaded = False
    
    def load_csv(self, path: str, table_name: str) -> List[str]:
        """
        Load a CSV file into a DuckDB table.
        
        Args:
            path: Path to the CSV file
            table_name: Name for the table in DuckDB
            
        Returns:
            List of column names from the CSV
        """
        # Use DuckDB's native CSV reader with auto-detection
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM read_csv_auto('{path}')
        """)
        
        # Get column names
        result = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        columns = [row[0] for row in result]
        
        if table_name == "source_a":
            self._source_a_loaded = True
        elif table_name == "source_b":
            self._source_b_loaded = True
            
        return columns
    
    def get_columns(self, table_name: str) -> List[str]:
        """Get column names for a loaded table."""
        result = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        return [row[0] for row in result]
    
    def get_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    
    def detect_column(self, table_name: str, patterns: List[str]) -> Optional[str]:
        """
        Find first column matching any pattern (case-insensitive).
        
        Args:
            table_name: Name of the table to search
            patterns: List of patterns to match (substring match)
            
        Returns:
            Column name if found, None otherwise
        """
        columns = self.get_columns(table_name)
        for col in columns:
            col_lower = col.lower()
            for pattern in patterns:
                if pattern.lower() in col_lower:
                    return col
        return None
    
    def clean_amount_column(self, table_name: str, column_name: str) -> int:
        """
        Clean amount column: remove currency symbols, separators, convert to numeric.
        
        Handles:
        - Currency symbols: $, €, £, R, ¥, etc.
        - Thousand separators: commas, spaces
        - European format: 1.234,56 -> 1234.56
        - Parentheses for negatives: (100) -> -100
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to clean
            
        Returns:
            Number of rows affected
        """
        # First, check if it's already numeric
        col_type = self.conn.execute(f"""
            SELECT typeof({column_name}) FROM {table_name} LIMIT 1
        """).fetchone()
        
        if col_type and col_type[0] in ('DOUBLE', 'BIGINT', 'INTEGER', 'FLOAT'):
            return 0  # Already numeric, no cleaning needed
        
        # Create cleaned column, then replace original
        self.conn.execute(f"""
            ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _cleaned_amount DOUBLE
        """)
        
        # Clean the data using SQL transformations
        # Step 1: Remove all non-numeric chars except . , -
        # Step 2: Remove commas (thousand separators)
        # Step 3: Cast to double
        self.conn.execute(f"""
            UPDATE {table_name} SET _cleaned_amount = 
            CASE 
                -- Handle parentheses for negative numbers: (100) -> -100
                WHEN TRIM({column_name}) LIKE '(%)'
                THEN -1 * TRY_CAST(
                    REPLACE(
                        regexp_replace(
                            TRIM(BOTH '()' FROM TRIM({column_name})),
                            '[^0-9.,-]', '', 'g'
                        ),
                        ',', ''
                    ) AS DOUBLE
                )
                ELSE TRY_CAST(
                    REPLACE(
                        regexp_replace(
                            CAST({column_name} AS VARCHAR),
                            '[^0-9.,-]', '', 'g'
                        ),
                        ',', ''
                    ) AS DOUBLE
                )
            END
        """)
        
        # Drop original and rename cleaned
        self.conn.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
        self.conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN _cleaned_amount TO {column_name}")
        
        return self.get_row_count(table_name)
    
    def clean_date_column(self, table_name: str, column_name: str) -> int:
        """
        Clean date column: normalize various date formats to YYYY-MM-DD string.
        
        Handles:
        - YYYY-MM-DD (ISO format, already standard)
        - DD/MM/YYYY (European format) - default for ambiguous dates
        - MM/DD/YYYY (US format)
        - D/M/YYYY or M/D/YYYY (single digit variants)
        
        Detection logic for slash-separated dates:
        - If first part > 12, it must be DD/MM/YYYY (day first)
        - If second part > 12, it must be MM/DD/YYYY (month first)
        - If ambiguous (both <= 12), defaults to DD/MM/YYYY (European format)
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to clean
            
        Returns:
            Number of rows affected
        """
        # Create cleaned column
        self.conn.execute(f"""
            ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _cleaned_date VARCHAR
        """)
        
        # Convert dates to consistent YYYY-MM-DD string format
        # Intelligently detect DD/MM/YYYY vs MM/DD/YYYY
        # Default to European format (DD/MM/YYYY) for ambiguous dates
        self.conn.execute(f"""
            UPDATE {table_name} SET _cleaned_date = 
            CASE
                -- Already in YYYY-MM-DD format (starts with 4 digits and hyphen)
                WHEN CAST({column_name} AS VARCHAR) LIKE '____-__-__'
                THEN CAST({column_name} AS VARCHAR)
                
                -- Slash-separated format (need to detect DD/MM vs MM/DD)
                WHEN CAST({column_name} AS VARCHAR) LIKE '%/%/%'
                THEN (
                    SELECT 
                        CASE
                            -- If first part > 12, it must be the day (DD/MM/YYYY - European)
                            WHEN TRY_CAST(part1 AS INTEGER) > 12 
                            THEN part3 || '-' || LPAD(part2, 2, '0') || '-' || LPAD(part1, 2, '0')
                            
                            -- If second part > 12, it must be the day (MM/DD/YYYY - US)
                            WHEN TRY_CAST(part2 AS INTEGER) > 12
                            THEN part3 || '-' || LPAD(part1, 2, '0') || '-' || LPAD(part2, 2, '0')
                            
                            -- Ambiguous (both <= 12), default to DD/MM/YYYY (European format)
                            ELSE part3 || '-' || LPAD(part2, 2, '0') || '-' || LPAD(part1, 2, '0')
                        END
                    FROM (
                        SELECT 
                            SPLIT_PART(CAST({column_name} AS VARCHAR), '/', 1) as part1,
                            SPLIT_PART(CAST({column_name} AS VARCHAR), '/', 2) as part2,
                            SPLIT_PART(CAST({column_name} AS VARCHAR), '/', 3) as part3
                    )
                )
                
                -- Fallback: keep as-is
                ELSE CAST({column_name} AS VARCHAR)
            END
        """)
        
        # Drop original and rename cleaned
        self.conn.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
        self.conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN _cleaned_date TO {column_name}")
        
        return self.get_row_count(table_name)
    
    def get_column_sum(self, table_name: str, column_name: str) -> Optional[float]:
        """
        Get the sum of a numeric column.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            
        Returns:
            Sum of the column, or None if not numeric
        """
        try:
            result = self.conn.execute(f"""
                SELECT SUM(TRY_CAST({column_name} AS DOUBLE)) FROM {table_name}
            """).fetchone()
            return result[0] if result else None
        except Exception:
            return None
    
    def reconcile(self, config: ReconConfig) -> ReconResult:
        """
        Run reconciliation between source_a and source_b.
        
        Args:
            config: Reconciliation configuration
            
        Returns:
            ReconResult containing summary and table references
        """
        if not self._source_a_loaded or not self._source_b_loaded:
            raise ValueError("Both source files must be loaded before reconciliation")
        
        match_key = config.match_key
        tolerance = config.amount_tolerance
        
        # Get column mappings from config
        date_a = config.date_col_a
        date_b = config.date_col_b
        amount_a = config.amount_col_a
        amount_b = config.amount_col_b
        desc_a = config.description_col_a
        desc_b = config.description_col_b
        
        # Build description select clause (optional columns)
        desc_select_a = f"a.{desc_a} as description_a" if desc_a else "NULL as description_a"
        desc_select_b = f"b.{desc_b} as description_b" if desc_b else "NULL as description_b"
        
        # 1. Exact matches (key match, amount within tolerance, dates match)
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE exact_matches AS
            SELECT 
                a.{match_key} as match_key,
                a.{date_a} as date_a,
                b.{date_b} as date_b,
                a.{amount_a} as amount_a,
                b.{amount_b} as amount_b,
                {desc_select_a},
                {desc_select_b}
            FROM source_a a
            INNER JOIN source_b b ON a.{match_key} = b.{match_key}
            WHERE a.{date_a} = b.{date_b} 
              AND ABS(a.{amount_a} - b.{amount_b}) <= {tolerance}
        """)
        
        # 2. Matches with date note (key match, amount within tolerance, dates differ)
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE matches_with_date_note AS
            SELECT 
                a.{match_key} as match_key,
                a.{date_a} as date_a,
                b.{date_b} as date_b,
                a.{amount_a} as amount_a,
                b.{amount_b} as amount_b,
                {desc_select_a},
                {desc_select_b},
                'Date mismatch' as note
            FROM source_a a
            INNER JOIN source_b b ON a.{match_key} = b.{match_key}
            WHERE a.{date_a} != b.{date_b} 
              AND ABS(a.{amount_a} - b.{amount_b}) <= {tolerance}
        """)
        
        # 3. Amount variances (key match, amount outside tolerance)
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE amount_variances AS
            SELECT 
                a.{match_key} as match_key,
                a.{date_a} as date_a,
                b.{date_b} as date_b,
                a.{amount_a} as amount_a,
                b.{amount_b} as amount_b,
                ABS(a.{amount_a} - b.{amount_b}) as variance,
                {desc_select_a},
                {desc_select_b}
            FROM source_a a
            INNER JOIN source_b b ON a.{match_key} = b.{match_key}
            WHERE ABS(a.{amount_a} - b.{amount_b}) > {tolerance}
        """)
        
        # 4. Missing in B (in A but not in B)
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE missing_in_b AS
            SELECT a.*
            FROM source_a a
            LEFT JOIN source_b b ON a.{match_key} = b.{match_key}
            WHERE b.{match_key} IS NULL
        """)
        
        # 5. Missing in A (in B but not in A)
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE missing_in_a AS
            SELECT b.*
            FROM source_b b
            LEFT JOIN source_a a ON b.{match_key} = a.{match_key}
            WHERE a.{match_key} IS NULL
        """)
        
        # Get counts for summary
        summary = ReconSummary(
            exact_matches=self.get_row_count("exact_matches"),
            matches_with_date_note=self.get_row_count("matches_with_date_note"),
            amount_variances=self.get_row_count("amount_variances"),
            missing_in_b=self.get_row_count("missing_in_b"),
            missing_in_a=self.get_row_count("missing_in_a")
        )
        
        return ReconResult(config=config, summary=summary)
    
    def get_results(self, table_name: str, limit: int = 1000) -> List[tuple]:
        """
        Get results from a result table.
        
        Args:
            table_name: Name of the result table
            limit: Maximum rows to return (for GUI display)
            
        Returns:
            List of tuples containing row data
        """
        result = self.conn.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchall()
        return result
    
    def get_result_columns(self, table_name: str) -> List[str]:
        """Get column names for a result table."""
        return self.get_columns(table_name)
    
    def export_table(self, table_name: str, output_path: str) -> int:
        """
        Export a table to CSV.
        
        Args:
            table_name: Name of the table to export
            output_path: Path for the output CSV file
            
        Returns:
            Number of rows exported
        """
        count = self.get_row_count(table_name)
        self.conn.execute(f"""
            COPY {table_name} TO '{output_path}' (HEADER, DELIMITER ',')
        """)
        return count
    
    # =========================================================================
    # Multi-Tool Support Methods
    # =========================================================================
    
    def union_tables(
        self, 
        table_names: List[str], 
        output_table: str, 
        validate: bool = True
    ) -> bool:
        """
        Combine multiple tables with same schema using UNION ALL.
        
        Args:
            table_names: List of table names to combine
            output_table: Name for the combined output table
            validate: If True, validate schemas match before union
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If schemas don't match (when validate=True)
        """
        if not table_names:
            raise ValueError("No tables provided for union")
        
        if validate and len(table_names) > 1:
            # Get schema of first table as reference
            reference_cols = set(self.get_columns(table_names[0]))
            
            for table in table_names[1:]:
                current_cols = set(self.get_columns(table))
                if current_cols != reference_cols:
                    missing = reference_cols - current_cols
                    extra = current_cols - reference_cols
                    raise ValueError(
                        f"Schema mismatch in {table}: "
                        f"missing={missing}, extra={extra}"
                    )
        
        # Build UNION ALL query
        union_parts = [f"SELECT * FROM {table}" for table in table_names]
        union_query = " UNION ALL ".join(union_parts)
        
        self.conn.execute(f"CREATE OR REPLACE TABLE {output_table} AS {union_query}")
        return True
    
    def filter_data(
        self, 
        table_name: str, 
        conditions: List[dict],
        output_table: str,
        combine_mode: str = "OR"
    ) -> int:
        """
        Filter data based on multiple range conditions.
        
        Args:
            table_name: Source table to filter
            conditions: List of filter conditions, each with:
                - column: Column name
                - operator: 'between', 'equals', 'contains', 'gt', 'lt', 'gte', 'lte'
                - value: Single value or [min, max] for 'between'
            output_table: Name for filtered output table
            combine_mode: 'OR' or 'AND' to combine conditions
            
        Returns:
            Number of rows in filtered result
        """
        if not conditions:
            # No conditions = copy all data
            self.conn.execute(f"CREATE OR REPLACE TABLE {output_table} AS SELECT * FROM {table_name}")
            return self.get_row_count(output_table)
        
        where_parts = []
        params = []
        
        for cond in conditions:
            column = cond['column']
            operator = cond.get('operator', 'equals')
            value = cond['value']
            
            if operator == 'between':
                where_parts.append(f'"{column}" BETWEEN ? AND ?')
                params.extend(value)
            elif operator == 'equals':
                where_parts.append(f'"{column}" = ?')
                params.append(value)
            elif operator == 'contains':
                where_parts.append(f'"{column}" LIKE ?')
                params.append(f'%{value}%')
            elif operator == 'gt':
                where_parts.append(f'"{column}" > ?')
                params.append(value)
            elif operator == 'lt':
                where_parts.append(f'"{column}" < ?')
                params.append(value)
            elif operator == 'gte':
                where_parts.append(f'"{column}" >= ?')
                params.append(value)
            elif operator == 'lte':
                where_parts.append(f'"{column}" <= ?')
                params.append(value)
        
        separator = f" {combine_mode} "
        where_clause = separator.join(where_parts)
        
        query = f"CREATE OR REPLACE TABLE {output_table} AS SELECT * FROM {table_name} WHERE {where_clause}"
        self.conn.execute(query, params)
        
        return self.get_row_count(output_table)
    
    def aggregate_data(
        self, 
        table_name: str, 
        group_cols: List[str], 
        sum_col: str,
        output_table: str = "aggregated",
        order_by: str = "total_amount DESC"
    ) -> dict:
        """
        GROUP BY aggregation with SUM and COUNT.
        
        Args:
            table_name: Source table
            group_cols: Columns to group by
            sum_col: Column to sum
            output_table: Name for output table
            order_by: ORDER BY clause (default: total_amount DESC)
            
        Returns:
            Dict with 'row_count' and 'grand_total'
        """
        group_clause = ", ".join([f'"{col}"' for col in group_cols])
        select_cols = ", ".join([f'"{col}"' for col in group_cols])
        
        query = f"""
            CREATE OR REPLACE TABLE {output_table} AS
            SELECT 
                {select_cols},
                COUNT(*) as record_count,
                SUM("{sum_col}") as total_amount
            FROM {table_name}
            GROUP BY {group_clause}
            ORDER BY {order_by}
        """
        
        self.conn.execute(query)
        
        # Calculate grand total
        grand_total = self.conn.execute(
            f'SELECT COUNT(*), SUM("{sum_col}") FROM {table_name}'
        ).fetchone()
        
        return {
            'row_count': self.get_row_count(output_table),
            'grand_total': grand_total[1] if grand_total else 0,
            'total_records': grand_total[0] if grand_total else 0
        }
    
    def transform_column(
        self, 
        table_name: str, 
        column: str, 
        target_type: str, 
        format_str: Optional[str] = None
    ) -> int:
        """
        Generic column type transformation.
        
        Args:
            table_name: Table to modify
            column: Column to transform
            target_type: Target type: 'text', 'number', 'date', 'boolean'
            format_str: Optional format string for output
            
        Returns:
            Number of rows affected
        """
        if target_type == 'number':
            return self.clean_amount_column(table_name, column)
        elif target_type == 'date':
            return self.clean_date_column(table_name, column)
        elif target_type == 'boolean':
            return self.clean_boolean_column(table_name, column)
        elif target_type == 'text':
            # Convert to text
            self.conn.execute(f"""
                ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _temp_text VARCHAR
            """)
            self.conn.execute(f"""
                UPDATE {table_name} SET _temp_text = CAST("{column}" AS VARCHAR)
            """)
            self.conn.execute(f'ALTER TABLE {table_name} DROP COLUMN "{column}"')
            self.conn.execute(f'ALTER TABLE {table_name} RENAME COLUMN _temp_text TO "{column}"')
            return self.get_row_count(table_name)
        
        return 0
    
    def select_columns(
        self, 
        table_name: str, 
        columns: List[str], 
        output_table: str
    ) -> int:
        """
        Create new table with only selected columns.
        
        Args:
            table_name: Source table
            columns: List of column names to include
            output_table: Name for output table
            
        Returns:
            Number of rows in output table
        """
        cols_str = ", ".join([f'"{col}"' for col in columns])
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE {output_table} AS
            SELECT {cols_str} FROM {table_name}
        """)
        return self.get_row_count(output_table)
    
    def get_schema_info(self, table_name: str) -> List[dict]:
        """
        Get detailed column info (name, type, nullable).
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dicts with column information
        """
        result = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        schema = []
        for row in result:
            schema.append({
                'name': row[0],
                'type': row[1],
                'nullable': row[2] if len(row) > 2 else True
            })
        return schema
    
    def clean_boolean_column(self, table_name: str, column_name: str) -> int:
        """
        Convert variations (Yes/No, 1/0, True/False, Y/N) to boolean.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to clean
            
        Returns:
            Number of rows affected
        """
        self.conn.execute(f"""
            ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _cleaned_bool BOOLEAN
        """)
        
        self.conn.execute(f"""
            UPDATE {table_name} SET _cleaned_bool = 
            CASE 
                WHEN LOWER(TRIM(CAST("{column_name}" AS VARCHAR))) IN ('true', 'yes', 'y', '1', 't')
                THEN TRUE
                WHEN LOWER(TRIM(CAST("{column_name}" AS VARCHAR))) IN ('false', 'no', 'n', '0', 'f')
                THEN FALSE
                ELSE NULL
            END
        """)
        
        self.conn.execute(f'ALTER TABLE {table_name} DROP COLUMN "{column_name}"')
        self.conn.execute(f'ALTER TABLE {table_name} RENAME COLUMN _cleaned_bool TO "{column_name}"')
        
        return self.get_row_count(table_name)
    
    def format_date_output(
        self, 
        table_name: str, 
        column_name: str, 
        format_str: str = "YYYY-MM-DD"
    ) -> int:
        """
        Format date column to specific output format.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to format
            format_str: Output format (YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MMM-YYYY)
            
        Returns:
            Number of rows affected
        """
        # Map format strings to strftime patterns
        format_map = {
            "YYYY-MM-DD": "%Y-%m-%d",
            "DD/MM/YYYY": "%d/%m/%Y", 
            "MM/DD/YYYY": "%m/%d/%Y",
            "DD-MMM-YYYY": "%d-%b-%Y"
        }
        
        strftime_format = format_map.get(format_str, "%Y-%m-%d")
        
        self.conn.execute(f"""
            ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _formatted_date VARCHAR
        """)
        
        self.conn.execute(f"""
            UPDATE {table_name} SET _formatted_date = 
            strftime(TRY_CAST("{column_name}" AS DATE), '{strftime_format}')
        """)
        
        self.conn.execute(f'ALTER TABLE {table_name} DROP COLUMN "{column_name}"')
        self.conn.execute(f'ALTER TABLE {table_name} RENAME COLUMN _formatted_date TO "{column_name}"')
        
        return self.get_row_count(table_name)
    
    def format_number_output(
        self, 
        table_name: str, 
        column_name: str, 
        precision: int = 2
    ) -> int:
        """
        Format number column to specific decimal precision.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to format
            precision: Number of decimal places
            
        Returns:
            Number of rows affected
        """
        self.conn.execute(f"""
            ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _formatted_num DOUBLE
        """)
        
        self.conn.execute(f"""
            UPDATE {table_name} SET _formatted_num = 
            ROUND(CAST("{column_name}" AS DOUBLE), {precision})
        """)
        
        self.conn.execute(f'ALTER TABLE {table_name} DROP COLUMN "{column_name}"')
        self.conn.execute(f'ALTER TABLE {table_name} RENAME COLUMN _formatted_num TO "{column_name}"')
        
        return self.get_row_count(table_name)
    
    def get_statistics(self, table_name: str, column_name: str) -> dict:
        """
        Get statistics for a numeric column.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            
        Returns:
            Dict with count, sum, avg, min, max
        """
        try:
            result = self.conn.execute(f"""
                SELECT 
                    COUNT(*) as count,
                    SUM("{column_name}") as total,
                    AVG("{column_name}") as average,
                    MIN("{column_name}") as minimum,
                    MAX("{column_name}") as maximum
                FROM {table_name}
            """).fetchone()
            
            return {
                'count': result[0],
                'total': result[1],
                'average': result[2],
                'min': result[3],
                'max': result[4]
            }
        except Exception:
            return {}
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
