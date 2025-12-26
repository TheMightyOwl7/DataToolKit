"""Data Analysis Tool for filtering and analyzing data with range conditions."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from base_tool import BaseTool


@dataclass
class FilterRange:
    """Represents a filter range condition."""
    filter_type: str  # 'amount', 'date', 'text'
    column: str
    min_val: Any
    max_val: Any = None
    
    def to_condition(self) -> Dict[str, Any]:
        """Convert to engine condition dict."""
        if self.filter_type == 'text':
            return {
                'column': self.column,
                'operator': 'contains',
                'value': self.min_val
            }
        else:
            return {
                'column': self.column,
                'operator': 'between',
                'value': [self.min_val, self.max_val]
            }
    
    def __str__(self) -> str:
        """Display in filter list."""
        if self.filter_type == 'text':
            return f"{self.column}: contains '{self.min_val}'"
        return f"{self.column}: {self.min_val} - {self.max_val}"


class FilterManager:
    """Manages multiple filter conditions."""
    
    def __init__(self):
        self.filters: List[FilterRange] = []
        self.combine_mode: str = "OR"  # 'OR' or 'AND'
    
    def add_filter(self, filter_range: FilterRange):
        """Add a filter to the list."""
        self.filters.append(filter_range)
    
    def remove_filter(self, index: int):
        """Remove a filter by index."""
        if 0 <= index < len(self.filters):
            del self.filters[index]
    
    def clear(self):
        """Clear all filters."""
        self.filters = []
    
    def get_conditions(self) -> List[Dict[str, Any]]:
        """Get all filters as condition dicts for engine."""
        return [f.to_condition() for f in self.filters]


class DataAnalyzer(BaseTool):
    """
    Data Analysis Tool for filtering and analyzing CSV data.
    
    Features:
    - Load and preview CSV files
    - Add multiple range filters (amount, date, text)
    - Combine filters with OR/AND logic
    - Real-time statistics calculation
    - Preview filtered results
    - Export filtered data
    """
    
    def __init__(self, parent: tk.Widget, controller=None, on_back=None):
        """Initialize the Data Analysis Tool."""
        super().__init__(parent, controller, on_back)
        
        # Data state
        self.input_file_var = tk.StringVar()
        self.input_table = "input_data"
        self.filtered_table = "filtered_data"
        self.columns: List[str] = []
        
        # Filter state
        self.filter_manager = FilterManager()
        
        # Filter input variables
        self.filter_type_var = tk.StringVar(value="amount")
        self.filter_column_var = tk.StringVar()
        self.filter_from_var = tk.StringVar()
        self.filter_to_var = tk.StringVar()
        self.combine_mode_var = tk.StringVar(value="OR")
        self.amount_col_var = tk.StringVar()
        
        # Statistics display
        self.stats_count_var = tk.StringVar(value="--")
        self.stats_total_var = tk.StringVar(value="--")
        self.stats_avg_var = tk.StringVar(value="--")
        self.stats_min_var = tk.StringVar(value="--")
        self.stats_max_var = tk.StringVar(value="--")
        
        # UI references
        self.input_preview_tree: Optional[ttk.Treeview] = None
        self.filtered_preview_tree: Optional[ttk.Treeview] = None
        self.filter_listbox: Optional[tk.Listbox] = None
        self.column_combo: Optional[ttk.Combobox] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container with scrolling
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
        self.create_header("Data Analysis Tool")
        
        # File selector
        file_frame = self.create_file_selector(
            self.main_frame,
            "Input File:",
            self.input_file_var
        )
        file_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Data preview section
        self.input_preview_tree = self.create_preview_table(
            self.main_frame,
            "Data Preview",
            height=4
        )
        
        # Total records label
        self.total_records_label = ttk.Label(
            self.main_frame, 
            text="Total Records: 0", 
            font=("", 9)
        )
        self.total_records_label.pack(anchor="w")
        
        # Filter configuration section
        self._create_filter_section()
        
        # Statistics section
        self._create_statistics_section()
        
        # Action buttons
        self._create_action_buttons()
        
        # Filtered data preview
        self.filtered_preview_tree = self.create_preview_table(
            self.main_frame,
            "Filtered Data Preview",
            height=5
        )
        
        # Status bar
        self.create_status_bar(self.main_frame)
    
    def _create_filter_section(self):
        """Create the filter configuration section."""
        filter_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Filter Configuration", 
            padding="10"
        )
        filter_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Filter type selection
        type_frame = ttk.Frame(filter_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="Filter Type:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            type_frame, text="Amount", variable=self.filter_type_var, 
            value="amount", command=self._on_filter_type_change
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            type_frame, text="Date", variable=self.filter_type_var, 
            value="date", command=self._on_filter_type_change
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            type_frame, text="Text", variable=self.filter_type_var, 
            value="text", command=self._on_filter_type_change
        ).pack(side=tk.LEFT, padx=10)
        
        # Filter input row
        input_frame = ttk.Frame(filter_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="Column:").pack(side=tk.LEFT)
        self.column_combo = ttk.Combobox(
            input_frame, 
            textvariable=self.filter_column_var,
            width=15,
            state="readonly"
        )
        self.column_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(input_frame, text="From:").pack(side=tk.LEFT, padx=(10, 0))
        self.from_entry = ttk.Entry(input_frame, textvariable=self.filter_from_var, width=15)
        self.from_entry.pack(side=tk.LEFT, padx=5)
        
        self.to_label = ttk.Label(input_frame, text="To:")
        self.to_label.pack(side=tk.LEFT, padx=(10, 0))
        self.to_entry = ttk.Entry(input_frame, textvariable=self.filter_to_var, width=15)
        self.to_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            input_frame, 
            text="Add Range", 
            command=self._add_filter
        ).pack(side=tk.LEFT, padx=10)
        
        # Active filters listbox
        filters_frame = ttk.Frame(filter_frame)
        filters_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(filters_frame, text="Active Filters:").pack(anchor="w")
        
        list_frame = ttk.Frame(filters_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.filter_listbox = tk.Listbox(list_frame, height=4)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.filter_listbox.yview)
        self.filter_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.filter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Filter actions
        filter_btn_frame = ttk.Frame(filters_frame)
        filter_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            filter_btn_frame, 
            text="Remove Selected", 
            command=self._remove_filter
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            filter_btn_frame, 
            text="Clear All", 
            command=self._clear_filters
        ).pack(side=tk.LEFT, padx=2)
        
        # Combine mode
        combine_frame = ttk.Frame(filter_frame)
        combine_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(combine_frame, text="Combine Filters:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            combine_frame, text="OR (Any Match)", 
            variable=self.combine_mode_var, value="OR"
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            combine_frame, text="AND (All Must Match)", 
            variable=self.combine_mode_var, value="AND"
        ).pack(side=tk.LEFT, padx=10)
    
    def _create_statistics_section(self):
        """Create the statistics display section."""
        stats_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Analysis Results", 
            padding="10"
        )
        stats_frame.pack(fill=tk.X, pady=10)
        
        # Amount column selector
        amt_frame = ttk.Frame(stats_frame)
        amt_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(amt_frame, text="Analyze Column:").pack(side=tk.LEFT)
        self.amount_col_combo = ttk.Combobox(
            amt_frame,
            textvariable=self.amount_col_var,
            width=20,
            state="readonly"
        )
        self.amount_col_combo.pack(side=tk.LEFT, padx=10)
        
        # Statistics display grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        stats_items = [
            ("Matched Records:", self.stats_count_var),
            ("Total Sum:", self.stats_total_var),
            ("Average:", self.stats_avg_var),
            ("Min:", self.stats_min_var),
            ("Max:", self.stats_max_var)
        ]
        
        for i, (label_text, var) in enumerate(stats_items):
            ttk.Label(stats_grid, text=label_text, font=("", 9)).grid(
                row=0, column=i*2, sticky="w", padx=5
            )
            ttk.Label(stats_grid, textvariable=var, font=("", 9, "bold")).grid(
                row=0, column=i*2+1, sticky="w", padx=(0, 20)
            )
    
    def _create_action_buttons(self):
        """Create action buttons."""
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="🔍 Apply Filters", 
            command=self._apply_filters
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="📥 Export Filtered Data", 
            command=self._export_filtered
        ).pack(side=tk.LEFT, padx=5)
    
    # =========================================================================
    # File Loading
    # =========================================================================
    
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
            
            # Update column dropdowns
            self.column_combo['values'] = self.columns
            self.amount_col_combo['values'] = self.columns
            
            # Auto-detect amount column
            amount_col = self.detect_amount_column(self.input_table)
            if amount_col:
                self.amount_col_var.set(amount_col)
            elif self.columns:
                self.amount_col_var.set(self.columns[0])
            
            if self.columns:
                self.filter_column_var.set(self.columns[0])
            
            row_count = self.engine.get_row_count(self.input_table)
            self.total_records_label.config(text=f"Total Records: {row_count:,}")
            self._show_status(f"Loaded: {row_count:,} rows, {len(self.columns)} columns")
            
            # Clear previous filters
            self._clear_filters()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
    
    # =========================================================================
    # Filter Management
    # =========================================================================
    
    def _on_filter_type_change(self):
        """Handle filter type change - update UI."""
        filter_type = self.filter_type_var.get()
        
        if filter_type == 'text':
            self.to_label.pack_forget()
            self.to_entry.pack_forget()
        else:
            self.to_label.pack(side=tk.LEFT, padx=(10, 0))
            self.to_entry.pack(side=tk.LEFT, padx=5)
    
    def _add_filter(self):
        """Add a new filter to the list."""
        if not self.columns:
            messagebox.showwarning("No Data", "Please load a file first")
            return
        
        filter_type = self.filter_type_var.get()
        column = self.filter_column_var.get()
        from_val = self.filter_from_var.get().strip()
        to_val = self.filter_to_var.get().strip()
        
        if not column:
            messagebox.showwarning("Missing Input", "Please select a column")
            return
        
        if not from_val:
            messagebox.showwarning("Missing Input", "Please enter a 'From' value")
            return
        
        if filter_type != 'text' and not to_val:
            messagebox.showwarning("Missing Input", "Please enter a 'To' value")
            return
        
        # Parse values based on type
        try:
            if filter_type == 'amount':
                from_val = float(from_val)
                to_val = float(to_val)
            # Date and text remain as strings
        except ValueError:
            messagebox.showwarning("Invalid Input", "Amount values must be numbers")
            return
        
        # Create filter
        filter_range = FilterRange(
            filter_type=filter_type,
            column=column,
            min_val=from_val,
            max_val=to_val if filter_type != 'text' else None
        )
        
        self.filter_manager.add_filter(filter_range)
        self.filter_listbox.insert(tk.END, str(filter_range))
        
        # Clear inputs
        self.filter_from_var.set("")
        self.filter_to_var.set("")
        
        self._show_status(f"Added filter: {filter_range}")
    
    def _remove_filter(self):
        """Remove selected filter."""
        selection = self.filter_listbox.curselection()
        if selection:
            index = selection[0]
            self.filter_manager.remove_filter(index)
            self.filter_listbox.delete(index)
            self._show_status("Filter removed")
    
    def _clear_filters(self):
        """Clear all filters."""
        self.filter_manager.clear()
        self.filter_listbox.delete(0, tk.END)
        self._clear_statistics()
        self._show_status("Filters cleared")
    
    def _clear_statistics(self):
        """Clear statistics display."""
        self.stats_count_var.set("--")
        self.stats_total_var.set("--")
        self.stats_avg_var.set("--")
        self.stats_min_var.set("--")
        self.stats_max_var.set("--")
    
    # =========================================================================
    # Filter Application
    # =========================================================================
    
    def _apply_filters(self):
        """Apply filters and calculate statistics."""
        if not self.columns:
            messagebox.showwarning("No Data", "Please load a file first")
            return
        
        self.run_threaded(
            self._run_filter,
            on_complete=self._on_filter_complete,
            progress_message="Applying filters..."
        )
    
    def _run_filter(self) -> Dict[str, Any]:
        """Run the filter and calculate statistics."""
        conditions = self.filter_manager.get_conditions()
        combine_mode = self.combine_mode_var.get()
        
        # Apply filter
        self.filter_manager.combine_mode = combine_mode
        row_count = self.engine.filter_data(
            self.input_table,
            conditions,
            self.filtered_table,
            combine_mode
        )
        
        # Calculate statistics on amount column
        amount_col = self.amount_col_var.get()
        stats = {}
        if amount_col:
            stats = self.engine.get_statistics(self.filtered_table, amount_col)
        
        return {
            'row_count': row_count,
            'stats': stats
        }
    
    def _on_filter_complete(self, result: Dict[str, Any]):
        """Handle filter completion."""
        # Update filtered preview
        self.update_preview(
            self.filtered_preview_tree,
            self.filtered_table,
            self.columns,
            limit=10
        )
        
        # Update statistics
        stats = result.get('stats', {})
        row_count = result.get('row_count', 0)
        
        self.stats_count_var.set(f"{row_count:,}")
        
        if stats:
            total = stats.get('total')
            avg = stats.get('average')
            min_val = stats.get('min')
            max_val = stats.get('max')
            
            self.stats_total_var.set(f"${total:,.2f}" if total is not None else "--")
            self.stats_avg_var.set(f"${avg:,.2f}" if avg is not None else "--")
            self.stats_min_var.set(f"${min_val:,.2f}" if min_val is not None else "--")
            self.stats_max_var.set(f"${max_val:,.2f}" if max_val is not None else "--")
        
        filter_count = len(self.filter_manager.filters)
        self._show_status(f"{filter_count} filter(s) | {row_count:,} matches")
    
    def _export_filtered(self):
        """Export filtered data to CSV."""
        if not self.columns:
            messagebox.showwarning("No Data", "Please load a file first")
            return
        
        try:
            # Check if filtered table exists
            self.engine.get_row_count(self.filtered_table)
        except:
            # Run filter first
            self._run_filter()
        
        # Prompt for output file
        output_path = filedialog.asksaveasfilename(
            title="Save Filtered Data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            row_count = self.engine.export_table(self.filtered_table, output_path)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {row_count:,} rows to:\n{output_path}"
            )
            self._show_status(f"Exported: {output_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
