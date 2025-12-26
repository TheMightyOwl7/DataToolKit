"""Data Aggregation Tool for combining and grouping data."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Optional, Any
from pathlib import Path
from base_tool import BaseTool


class DataAggregator(BaseTool):
    """
    Data Aggregation Tool for combining multiple CSV files and grouping data.
    
    Features:
    - Load multiple CSV files
    - Validate schema compatibility
    - Combine files with UNION ALL
    - Group by selected columns
    - Sum numeric columns
    - Display grand totals
    - Export aggregated results
    """
    
    def __init__(self, parent: tk.Widget, controller=None, on_back=None):
        """Initialize the Data Aggregation Tool."""
        super().__init__(parent, controller, on_back)
        
        # File list state
        self.file_list: List[str] = []
        self.file_tables: List[str] = []  # Table names for each file
        self.combined_table = "combined_data"
        self.aggregated_table = "aggregated_results"
        self.columns: List[str] = []
        
        # Aggregation settings
        self.primary_group_var = tk.StringVar()
        self.sum_col_var = tk.StringVar()
        self.additional_group_vars: Dict[str, tk.BooleanVar] = {}
        self.sort_by_var = tk.StringVar(value="total")
        
        # UI references
        self.file_listbox: Optional[tk.Listbox] = None
        self.status_label: Optional[ttk.Label] = None
        self.combined_preview_tree: Optional[ttk.Treeview] = None
        self.results_tree: Optional[ttk.Treeview] = None
        self.additional_checkboxes_frame: Optional[ttk.Frame] = None
        self.grand_total_var = tk.StringVar(value="--")
        self.record_count_var = tk.StringVar(value="--")
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with back button
        self.create_header("Data Aggregation Tool")
        
        # Top section: File list and Combined preview side by side
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left: Input files section
        self._create_file_list_section(top_frame)
        
        # Right: Combined preview
        self._create_combined_preview_section(top_frame)
        
        # Middle section: Aggregation settings
        self._create_aggregation_settings(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
        
        # Bottom section: Results
        self._create_results_section(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
    
    def _create_file_list_section(self, parent: tk.Widget):
        """Create the input files list section."""
        files_frame = ttk.LabelFrame(parent, text="Input Files", padding="10")
        files_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.file_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # File buttons
        btn_frame = ttk.Frame(files_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(btn_frame, text="Add File", command=self._add_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self._remove_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear All", command=self._clear_files).pack(side=tk.LEFT, padx=2)
        
        # Status label
        self.files_status_label = ttk.Label(files_frame, text="No files loaded", font=("", 8))
        self.files_status_label.pack(pady=(5, 0))
    
    def _create_combined_preview_section(self, parent: tk.Widget):
        """Create the combined data preview section."""
        preview_frame = ttk.LabelFrame(parent, text="Combined Preview", padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.combined_preview_tree = ttk.Treeview(tree_frame, show="headings", height=6)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.combined_preview_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.combined_preview_tree.xview)
        self.combined_preview_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.combined_preview_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind right-click for context menu
        self.combined_preview_tree.bind("<Button-3>", 
            lambda e: self._show_context_menu(e, self.combined_preview_tree))
        
        # Total rows label
        self.total_rows_label = ttk.Label(preview_frame, text="Total Rows: 0", font=("", 8))
        self.total_rows_label.pack(pady=(5, 0))
    
    def _create_aggregation_settings(self, parent: tk.Widget):
        """Create the aggregation settings section."""
        settings_frame = ttk.LabelFrame(parent, text="Aggregation Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=10)
        
        # Primary group by
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="Primary Group By:").pack(side=tk.LEFT)
        self.primary_group_combo = ttk.Combobox(
            row1, 
            textvariable=self.primary_group_var, 
            width=20,
            state="readonly"
        )
        self.primary_group_combo.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(row1, text="Sum Column:").pack(side=tk.LEFT, padx=(20, 0))
        self.sum_col_combo = ttk.Combobox(
            row1,
            textvariable=self.sum_col_var,
            width=20,
            state="readonly"
        )
        self.sum_col_combo.pack(side=tk.LEFT, padx=10)
        
        # Additional grouping checkboxes
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X, pady=5)
        
        ttk.Label(row2, text="Additional Grouping:").pack(side=tk.LEFT)
        self.additional_checkboxes_frame = ttk.Frame(row2)
        self.additional_checkboxes_frame.pack(side=tk.LEFT, padx=10)
        
        # Sort options
        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="Sort By:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            row3, text="Total (Desc)", variable=self.sort_by_var, value="total"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            row3, text="Group Name (Asc)", variable=self.sort_by_var, value="group"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            row3, text="Count (Desc)", variable=self.sort_by_var, value="count"
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_action_buttons(self, parent: tk.Widget):
        """Create action buttons."""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            btn_frame, 
            text="📊 Aggregate Data", 
            command=self._aggregate_data
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="📥 Export Results", 
            command=self._export_results
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_results_section(self, parent: tk.Widget):
        """Create the aggregated results section."""
        results_frame = ttk.LabelFrame(parent, text="Aggregated Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_tree = ttk.Treeview(tree_frame, show="headings", height=8)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind right-click for context menu
        self.results_tree.bind("<Button-3>", 
            lambda e: self._show_context_menu(e, self.results_tree))
        
        # Grand total row
        totals_frame = ttk.Frame(results_frame)
        totals_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(totals_frame, text="Grand Total:", font=("", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(totals_frame, textvariable=self.grand_total_var, font=("", 9, "bold"), foreground="blue").pack(side=tk.LEFT, padx=10)
        ttk.Label(totals_frame, text="Records:", font=("", 9)).pack(side=tk.LEFT, padx=(20, 0))
        ttk.Label(totals_frame, textvariable=self.record_count_var, font=("", 9)).pack(side=tk.LEFT, padx=5)
    
    # =========================================================================
    # File Management
    # =========================================================================
    
    def _add_file(self):
        """Add a file to the list."""
        paths = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        for path in paths:
            if path not in self.file_list:
                self.file_list.append(path)
                filename = Path(path).name
                self.file_listbox.insert(tk.END, filename)
        
        if paths:
            self._validate_and_combine_files()
    
    def _remove_file(self):
        """Remove selected file from the list."""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            self.file_listbox.delete(index)
            del self.file_list[index]
            
            if self.file_list:
                self._validate_and_combine_files()
            else:
                self._clear_combined_preview()
    
    def _clear_files(self):
        """Clear all files from the list."""
        self.file_listbox.delete(0, tk.END)
        self.file_list = []
        self._clear_combined_preview()
    
    def _clear_combined_preview(self):
        """Clear the combined preview and reset state."""
        self.combined_preview_tree.delete(*self.combined_preview_tree.get_children())
        self.combined_preview_tree["columns"] = []
        self.columns = []
        self.primary_group_combo['values'] = []
        self.sum_col_combo['values'] = []
        self.files_status_label.config(text="No files loaded")
        self.total_rows_label.config(text="Total Rows: 0")
        
        # Clear additional checkboxes
        for widget in self.additional_checkboxes_frame.winfo_children():
            widget.destroy()
        self.additional_group_vars = {}
    
    def _validate_and_combine_files(self):
        """Validate file schemas and combine if compatible."""
        if not self.file_list:
            return
        
        self._show_status("Validating files...")
        
        try:
            # Load each file into a temporary table
            self.file_tables = []
            reference_cols = None
            
            for i, path in enumerate(self.file_list):
                table_name = f"input_file_{i}"
                cols = self.engine.load_csv(path, table_name)
                self.file_tables.append(table_name)
                
                if reference_cols is None:
                    reference_cols = set(cols)
                    self.columns = cols
                else:
                    current_cols = set(cols)
                    if current_cols != reference_cols:
                        missing = reference_cols - current_cols
                        extra = current_cols - reference_cols
                        raise ValueError(
                            f"Schema mismatch in {Path(path).name}:\n"
                            f"Missing columns: {missing}\n"
                            f"Extra columns: {extra}"
                        )
            
            # Combine files
            self.engine.union_tables(self.file_tables, self.combined_table)
            
            # Update UI
            total_rows = self.engine.get_row_count(self.combined_table)
            self.files_status_label.config(
                text=f"✓ All files compatible ({len(self.columns)} columns)", 
                foreground="green"
            )
            self.total_rows_label.config(text=f"Total Rows: {total_rows:,}")
            
            # Update preview
            self.update_preview(
                self.combined_preview_tree,
                self.combined_table,
                self.columns,
                limit=5
            )
            
            # Update aggregation dropdowns
            self._update_aggregation_options()
            
            self._show_status(f"Loaded {len(self.file_list)} files, {total_rows:,} total rows")
            
        except Exception as e:
            self.files_status_label.config(text=f"✗ {str(e)[:50]}", foreground="red")
            messagebox.showerror("Validation Error", str(e))
    
    def _update_aggregation_options(self):
        """Update aggregation dropdown options based on loaded columns."""
        # Primary group by - all columns
        self.primary_group_combo['values'] = self.columns
        if self.columns:
            self.primary_group_var.set(self.columns[0])
        
        # Sum column - prefer detected amount columns
        amount_col = self.detect_amount_column(self.combined_table)
        self.sum_col_combo['values'] = self.columns
        if amount_col:
            self.sum_col_var.set(amount_col)
        elif self.columns:
            self.sum_col_var.set(self.columns[0])
        
        # Additional grouping checkboxes
        for widget in self.additional_checkboxes_frame.winfo_children():
            widget.destroy()
        self.additional_group_vars = {}
        
        for col in self.columns:
            var = tk.BooleanVar(value=False)
            self.additional_group_vars[col] = var
            cb = ttk.Checkbutton(
                self.additional_checkboxes_frame,
                text=col,
                variable=var
            )
            cb.pack(side=tk.LEFT, padx=5)
    
    # =========================================================================
    # Aggregation
    # =========================================================================
    
    def _aggregate_data(self):
        """Run aggregation on combined data."""
        if not self.columns:
            messagebox.showwarning("No Data", "Please add files first")
            return
        
        primary_group = self.primary_group_var.get()
        sum_col = self.sum_col_var.get()
        
        if not primary_group or not sum_col:
            messagebox.showwarning("Missing Settings", "Please select Group By and Sum columns")
            return
        
        self.run_threaded(
            self._run_aggregation,
            on_complete=self._on_aggregation_complete,
            progress_message="Aggregating data..."
        )
    
    def _run_aggregation(self) -> Dict[str, Any]:
        """Run the aggregation query."""
        primary_group = self.primary_group_var.get()
        sum_col = self.sum_col_var.get()
        
        # Build group columns list
        group_cols = [primary_group]
        for col, var in self.additional_group_vars.items():
            if var.get() and col != primary_group:
                group_cols.append(col)
        
        # Determine sort order
        sort_by = self.sort_by_var.get()
        if sort_by == "total":
            order_by = "total_amount DESC"
        elif sort_by == "count":
            order_by = "record_count DESC"
        else:
            order_by = f'"{primary_group}" ASC'
        
        # Run aggregation
        result = self.engine.aggregate_data(
            self.combined_table,
            group_cols,
            sum_col,
            self.aggregated_table,
            order_by
        )
        
        return result
    
    def _on_aggregation_complete(self, result: Dict[str, Any]):
        """Handle aggregation completion."""
        # Get result columns
        result_columns = self.engine.get_columns(self.aggregated_table)
        
        # Update results tree
        self.results_tree.delete(*self.results_tree.get_children())
        self.results_tree["columns"] = result_columns
        
        for col in result_columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120, minwidth=80)
        
        # Insert data
        rows = self.engine.get_results(self.aggregated_table, limit=500)
        for row in rows:
            self.results_tree.insert("", tk.END, values=row)
        
        # Update grand totals
        grand_total = result.get('grand_total', 0)
        total_records = result.get('total_records', 0)
        
        if grand_total is not None:
            self.grand_total_var.set(f"{grand_total:,.2f}")
        else:
            self.grand_total_var.set("--")
        self.record_count_var.set(f"{total_records:,}")
        
        self._show_status(f"Aggregated: {result['row_count']} groups, {total_records:,} total records")
    
    def _export_results(self):
        """Export aggregated results to CSV."""
        try:
            # Check if aggregated table exists
            self.engine.get_row_count(self.aggregated_table)
        except:
            messagebox.showwarning("No Results", "Please run aggregation first")
            return
        
        # Prompt for output file
        output_path = filedialog.asksaveasfilename(
            title="Save Aggregated Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            row_count = self.engine.export_table(self.aggregated_table, output_path)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {row_count:,} rows to:\n{output_path}"
            )
            self._show_status(f"Exported: {output_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
