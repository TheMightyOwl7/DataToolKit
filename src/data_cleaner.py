"""Data Cleaning Tool for standardizing data formats and types."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Optional, Any
from base_tool import BaseTool


class DataCleaner(BaseTool):
    """
    Data Cleaning Tool for standardizing CSV data.
    
    Features:
    - Load and preview CSV files
    - Configure column data types (Text, Number, Date, Boolean)
    - Specify output formats for each type
    - Include/exclude columns from output
    - Preview cleaned data before export
    - Export cleaned data to CSV
    """
    
    # Supported data types with their format options
    DATA_TYPES = {
        "Text": [],
        "Number": ["0.00", "0", "0.000", "0.0000"],
        "Date": ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY", "DD-MMM-YYYY"],
        "Boolean": []
    }
    
    def __init__(self, parent: tk.Widget, controller=None, on_back=None):
        """Initialize the Data Cleaning Tool."""
        super().__init__(parent, controller, on_back)
        
        # File and data state
        self.input_file_var = tk.StringVar()
        self.input_table = "input_data"
        self.cleaned_table = "cleaned_output"
        self.columns: List[str] = []
        
        # Column configuration storage
        # List of dicts: {name, type, format, include}
        self.column_configs: List[Dict[str, Any]] = []
        
        # UI references
        self.input_preview_tree: Optional[ttk.Treeview] = None
        self.output_preview_tree: Optional[ttk.Treeview] = None
        self.config_frame: Optional[ttk.Frame] = None
        self.config_widgets: List[Dict[str, tk.Widget]] = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # Main scrollable container
        main_canvas = tk.Canvas(self, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_canvas.yview)
        self.main_frame = ttk.Frame(main_canvas, padding="10")
        
        self.main_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        main_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Header with back button
        self.create_header("Data Cleaning Tool")
        
        # File selector
        file_frame = self.create_file_selector(
            self.main_frame,
            "Input File:",
            self.input_file_var
        )
        file_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Input preview
        self.input_preview_tree = self.create_preview_table(
            self.main_frame,
            "File Preview (First 5 Rows)",
            height=5
        )
        
        # Column configuration section
        self._create_column_config_section()
        
        # Action buttons
        self._create_action_buttons()
        
        # Output preview
        self.output_preview_tree = self.create_preview_table(
            self.main_frame,
            "Cleaned Data Preview",
            height=5
        )
        
        # Status bar
        self.create_status_bar(self.main_frame)
    
    def _create_column_config_section(self):
        """Create the column configuration section."""
        # Container
        config_container = ttk.LabelFrame(
            self.main_frame, 
            text="Column Configuration", 
            padding="10"
        )
        config_container.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Header row
        header_frame = ttk.Frame(config_container)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Include", width=8, anchor="center").pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Column Name", width=20, anchor="w").pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Data Type", width=12, anchor="center").pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Format", width=15, anchor="center").pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(config_container, orient="horizontal").pack(fill=tk.X, pady=2)
        
        # Scrollable frame for column rows
        config_canvas = tk.Canvas(config_container, height=200, highlightthickness=0)
        config_scrollbar = ttk.Scrollbar(config_container, orient="vertical", command=config_canvas.yview)
        self.config_frame = ttk.Frame(config_canvas)
        
        self.config_frame.bind(
            "<Configure>",
            lambda e: config_canvas.configure(scrollregion=config_canvas.bbox("all"))
        )
        
        config_canvas.create_window((0, 0), window=self.config_frame, anchor="nw")
        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        
        config_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        config_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_action_buttons(self):
        """Create action buttons."""
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="🔄 Auto-Detect Types", 
            command=self._auto_detect_types
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="👁 Preview Cleaned", 
            command=self._preview_cleaned
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="📥 Export to CSV", 
            command=self._export_cleaned
        ).pack(side=tk.LEFT, padx=5)
        
        # Select/Deselect All
        ttk.Button(
            btn_frame,
            text="☑ Select All",
            command=lambda: self._set_all_includes(True)
        ).pack(side=tk.RIGHT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="☐ Deselect All", 
            command=lambda: self._set_all_includes(False)
        ).pack(side=tk.RIGHT, padx=2)
    
    def _on_file_selected(self, path: str):
        """Handle file selection - load and preview."""
        try:
            self._show_status("Loading file...")
            
            # Load file into engine
            self.columns = self.engine.load_csv(path, self.input_table)
            
            # Update input preview
            self.update_preview(
                self.input_preview_tree, 
                self.input_table, 
                self.columns,
                limit=5
            )
            
            # Build column configuration
            self._build_column_configs()
            
            row_count = self.engine.get_row_count(self.input_table)
            self._show_status(f"Loaded: {row_count:,} rows, {len(self.columns)} columns")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def _build_column_configs(self):
        """Build column configuration widgets based on loaded columns."""
        # Clear existing config widgets
        for widget in self.config_frame.winfo_children():
            widget.destroy()
        self.config_widgets = []
        self.column_configs = []
        
        # Get schema info for type hints
        schema = self.engine.get_schema_info(self.input_table)
        
        for i, col_info in enumerate(schema):
            col_name = col_info['name']
            col_type = col_info['type']
            
            # Create row frame
            row_frame = ttk.Frame(self.config_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # Include checkbox
            include_var = tk.BooleanVar(value=True)
            include_cb = ttk.Checkbutton(row_frame, variable=include_var)
            include_cb.pack(side=tk.LEFT, padx=(0, 10))
            
            # Column name
            name_label = ttk.Label(row_frame, text=col_name, width=20, anchor="w")
            name_label.pack(side=tk.LEFT, padx=2)
            
            # Data type dropdown
            type_var = tk.StringVar(value=self._guess_type(col_name, col_type))
            type_combo = ttk.Combobox(
                row_frame, 
                textvariable=type_var, 
                values=list(self.DATA_TYPES.keys()),
                width=10,
                state="readonly"
            )
            type_combo.pack(side=tk.LEFT, padx=2)
            
            # Format dropdown (updates based on type)
            format_var = tk.StringVar()
            format_combo = ttk.Combobox(
                row_frame,
                textvariable=format_var,
                width=13,
                state="readonly"
            )
            format_combo.pack(side=tk.LEFT, padx=2)
            
            # Update format options when type changes
            def update_formats(event, type_v=type_var, format_c=format_combo, format_v=format_var):
                selected_type = type_v.get()
                formats = self.DATA_TYPES.get(selected_type, [])
                format_c['values'] = formats
                if formats:
                    format_v.set(formats[0])
                else:
                    format_v.set("")
            
            type_combo.bind("<<ComboboxSelected>>", update_formats)
            
            # Initialize format options
            initial_type = type_var.get()
            formats = self.DATA_TYPES.get(initial_type, [])
            format_combo['values'] = formats
            if formats:
                format_var.set(formats[0])
            
            # Store config
            config = {
                'name': col_name,
                'include_var': include_var,
                'type_var': type_var,
                'format_var': format_var
            }
            self.column_configs.append(config)
            self.config_widgets.append({
                'frame': row_frame,
                'include': include_cb,
                'type': type_combo,
                'format': format_combo
            })
    
    def _guess_type(self, col_name: str, db_type: str) -> str:
        """Guess the appropriate type based on column name and DB type."""
        col_lower = col_name.lower()
        
        # Check for date patterns
        for pattern in self.date_patterns:
            if pattern in col_lower:
                return "Date"
        
        # Check for amount patterns
        for pattern in self.amount_patterns:
            if pattern in col_lower:
                return "Number"
        
        # Check DB type
        if db_type in ['DOUBLE', 'FLOAT', 'INTEGER', 'BIGINT', 'DECIMAL']:
            return "Number"
        elif db_type == 'BOOLEAN':
            return "Boolean"
        elif db_type in ['DATE', 'TIMESTAMP']:
            return "Date"
        
        return "Text"
    
    def _auto_detect_types(self):
        """Auto-detect column types based on data patterns."""
        if not self.column_configs:
            messagebox.showwarning("No Data", "Please load a file first")
            return
        
        for config in self.column_configs:
            col_name = config['name']
            
            # Try to detect based on column name patterns
            detected_type = "Text"
            
            # Check date patterns
            if self.detect_column(self.input_table, [col_name.lower()]) and \
               any(p in col_name.lower() for p in self.date_patterns):
                detected_type = "Date"
            # Check amount patterns
            elif any(p in col_name.lower() for p in self.amount_patterns):
                detected_type = "Number"
            
            config['type_var'].set(detected_type)
            
            # Update format options
            formats = self.DATA_TYPES.get(detected_type, [])
            if formats:
                config['format_var'].set(formats[0])
        
        self._show_status("Auto-detected column types")
    
    def _set_all_includes(self, value: bool):
        """Set all include checkboxes to the given value."""
        for config in self.column_configs:
            config['include_var'].set(value)
    
    def _get_current_configs(self) -> List[Dict[str, Any]]:
        """Get current column configurations as list of dicts."""
        configs = []
        for config in self.column_configs:
            configs.append({
                'name': config['name'],
                'include': config['include_var'].get(),
                'type': config['type_var'].get(),
                'format': config['format_var'].get()
            })
        return configs
    
    def _preview_cleaned(self):
        """Preview the cleaned data."""
        if not self.columns:
            messagebox.showwarning("No Data", "Please load a file first")
            return
        
        self.run_threaded(
            self._clean_data,
            on_complete=self._on_clean_complete,
            progress_message="Cleaning data..."
        )
    
    def _clean_data(self) -> int:
        """
        Clean the data based on column configurations.
        
        Returns:
            Number of rows in cleaned output
        """
        configs = self._get_current_configs()
        
        # Validate at least one column is included
        included_cols = [c for c in configs if c['include']]
        if not included_cols:
            raise ValueError("At least one column must be included")
        
        # Create a working copy
        working_table = "cleaning_workspace"
        self.engine.conn.execute(f"""
            CREATE OR REPLACE TABLE {working_table} AS 
            SELECT * FROM {self.input_table}
        """)
        
        # Apply transformations
        for col_config in configs:
            if not col_config['include']:
                continue
            
            col_name = col_config['name']
            data_type = col_config['type']
            format_str = col_config['format']
            
            try:
                if data_type == 'Number':
                    self.engine.clean_amount_column(working_table, col_name)
                    if format_str:
                        precision = len(format_str.split('.')[-1]) if '.' in format_str else 0
                        self.engine.format_number_output(working_table, col_name, precision)
                        
                elif data_type == 'Date':
                    self.engine.clean_date_column(working_table, col_name)
                    if format_str:
                        self.engine.format_date_output(working_table, col_name, format_str)
                        
                elif data_type == 'Boolean':
                    self.engine.clean_boolean_column(working_table, col_name)
                    
                # Text requires no transformation
                
            except Exception as e:
                print(f"Warning: Could not clean column {col_name}: {e}")
        
        # Select only included columns
        included_names = [c['name'] for c in configs if c['include']]
        self.engine.select_columns(working_table, included_names, self.cleaned_table)
        
        return self.engine.get_row_count(self.cleaned_table)
    
    def _on_clean_complete(self, row_count: int):
        """Handle cleaning completion."""
        # Update output preview
        included_cols = [c['name'] for c in self._get_current_configs() if c['include']]
        self.update_preview(
            self.output_preview_tree,
            self.cleaned_table,
            included_cols,
            limit=5
        )
        
        self._show_status(f"Cleaned: {row_count:,} rows, {len(included_cols)} columns")
    
    def _export_cleaned(self):
        """Export cleaned data to CSV."""
        if not self.columns:
            messagebox.showwarning("No Data", "Please load a file first")
            return
        
        # First clean the data
        try:
            self._clean_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clean data: {e}")
            return
        
        # Prompt for output file
        output_path = filedialog.asksaveasfilename(
            title="Save Cleaned Data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            row_count = self.engine.export_table(self.cleaned_table, output_path)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {row_count:,} rows to:\n{output_path}"
            )
            self._show_status(f"Exported: {output_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
