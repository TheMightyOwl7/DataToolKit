"""Tkinter GUI for the Reconciliation App."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path

from models import ReconConfig, ReconResult
from recon_engine import ReconEngine
from exporter import Exporter


class ReconApp:
    """Main application window for reconciliation tool."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the application."""
        self.root = root
        self.root.title("Reconciliation Tool")
        self.root.geometry("900x900")
        self.root.minsize(800, 700)
        
        # Engine and state
        self.engine: ReconEngine = None
        self.result: ReconResult = None
        self.columns_a = []
        self.columns_b = []
        
        # Variables
        self.source_a_var = tk.StringVar()
        self.source_b_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.match_key_var = tk.StringVar()
        self.tolerance_var = tk.StringVar(value="0.00")
        self.status_var = tk.StringVar(value="Ready")
        
        # Column mapping variables
        self.date_col_a_var = tk.StringVar()
        self.date_col_b_var = tk.StringVar()
        self.amount_col_a_var = tk.StringVar()
        self.amount_col_b_var = tk.StringVar()
        self.desc_col_a_var = tk.StringVar()
        self.desc_col_b_var = tk.StringVar()
        
        # Auto-clean and totals
        self.auto_clean_var = tk.BooleanVar(value=True)  # Enabled by default
        self.total_a_var = tk.StringVar(value="--")
        self.total_b_var = tk.StringVar(value="--")
        self.temp_engine = None  # Keep engine alive for totals calculation
        
        # Auto-detection patterns
        self.date_patterns = ["date", "dt", "trans_date", "posting"]
        self.amount_patterns = ["amount", "amt", "value", "total", "sum"]
        self.desc_patterns = ["description", "desc", "narration", "memo", "reference"]
        
        # Context menu for copying
        self.context_menu = None
        self.context_tree = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Input Section ===
        input_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Source A
        ttk.Label(input_frame, text="Source A:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(input_frame, textvariable=self.source_a_var, width=60).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(input_frame, text="Browse", command=self._browse_source_a).grid(row=0, column=2, pady=2)
        
        # Source B
        ttk.Label(input_frame, text="Source B:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(input_frame, textvariable=self.source_b_var, width=60).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(input_frame, text="Browse", command=self._browse_source_b).grid(row=1, column=2, pady=2)
        
        # === File Preview Section ===
        preview_frame = ttk.LabelFrame(input_frame, text="File Preview (First 3 Rows)", padding="5")
        preview_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Source A Preview
        ttk.Label(preview_frame, text="Source A:", font=("", 8, "bold")).grid(row=0, column=0, sticky="w")
        self.preview_a_frame = ttk.Frame(preview_frame)
        self.preview_a_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        self.preview_a_tree = ttk.Treeview(self.preview_a_frame, show="headings", height=3)
        self.preview_a_tree.pack(fill=tk.X, expand=True)
        self.preview_a_tree.bind("<Button-3>", lambda e: self._show_context_menu(e, self.preview_a_tree))
        
        # Source B Preview
        ttk.Label(preview_frame, text="Source B:", font=("", 8, "bold")).grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.preview_b_frame = ttk.Frame(preview_frame)
        self.preview_b_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=2)
        self.preview_b_tree = ttk.Treeview(self.preview_b_frame, show="headings", height=3)
        self.preview_b_tree.pack(fill=tk.X, expand=True)
        self.preview_b_tree.bind("<Button-3>", lambda e: self._show_context_menu(e, self.preview_b_tree))
        
        preview_frame.grid_columnconfigure(0, weight=1)
        
        # === Column Mapping Section ===
        col_frame = ttk.LabelFrame(input_frame, text="Column Mapping", padding="5")
        col_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Headers
        ttk.Label(col_frame, text="").grid(row=0, column=0)
        ttk.Label(col_frame, text="Source A", font=("", 9, "bold")).grid(row=0, column=1, padx=10)
        ttk.Label(col_frame, text="Source B", font=("", 9, "bold")).grid(row=0, column=2, padx=10)
        
        # Date columns
        ttk.Label(col_frame, text="Date Column:").grid(row=1, column=0, sticky="w", pady=2)
        self.date_col_a_combo = ttk.Combobox(col_frame, textvariable=self.date_col_a_var, width=18, state="readonly")
        self.date_col_a_combo.grid(row=1, column=1, padx=5, pady=2)
        self.date_col_b_combo = ttk.Combobox(col_frame, textvariable=self.date_col_b_var, width=18, state="readonly")
        self.date_col_b_combo.grid(row=1, column=2, padx=5, pady=2)
        
        # Amount columns
        ttk.Label(col_frame, text="Amount Column:").grid(row=2, column=0, sticky="w", pady=2)
        self.amount_col_a_combo = ttk.Combobox(col_frame, textvariable=self.amount_col_a_var, width=18, state="readonly")
        self.amount_col_a_combo.grid(row=2, column=1, padx=5, pady=2)
        self.amount_col_b_combo = ttk.Combobox(col_frame, textvariable=self.amount_col_b_var, width=18, state="readonly")
        self.amount_col_b_combo.grid(row=2, column=2, padx=5, pady=2)
        
        # Bind amount column changes to update totals
        self.amount_col_a_combo.bind("<<ComboboxSelected>>", self._update_totals)
        self.amount_col_b_combo.bind("<<ComboboxSelected>>", self._update_totals)
        
        # Amount totals row
        ttk.Label(col_frame, text="Total:", font=("", 8)).grid(row=3, column=0, sticky="w", pady=1)
        ttk.Label(col_frame, textvariable=self.total_a_var, font=("", 8, "bold"), foreground="blue").grid(row=3, column=1, padx=5)
        ttk.Label(col_frame, textvariable=self.total_b_var, font=("", 8, "bold"), foreground="blue").grid(row=3, column=2, padx=5)
        
        # Description columns (optional)
        ttk.Label(col_frame, text="Description (opt):").grid(row=4, column=0, sticky="w", pady=2)
        self.desc_col_a_combo = ttk.Combobox(col_frame, textvariable=self.desc_col_a_var, width=18, state="readonly")
        self.desc_col_a_combo.grid(row=4, column=1, padx=5, pady=2)
        self.desc_col_b_combo = ttk.Combobox(col_frame, textvariable=self.desc_col_b_var, width=18, state="readonly")
        self.desc_col_b_combo.grid(row=4, column=2, padx=5, pady=2)
        
        # Auto-clean checkbox
        ttk.Checkbutton(col_frame, text="Auto-clean amounts (remove $, commas, etc.)", 
                        variable=self.auto_clean_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=5)
        
        # Match Key and Tolerance (same row)
        options_frame = ttk.Frame(input_frame)
        options_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=5)
        
        ttk.Label(options_frame, text="Match Key:").pack(side=tk.LEFT)
        self.match_key_combo = ttk.Combobox(options_frame, textvariable=self.match_key_var, width=20, state="readonly")
        self.match_key_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(options_frame, text="Amount Tolerance:").pack(side=tk.LEFT)
        ttk.Entry(options_frame, textvariable=self.tolerance_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # === Run Button + Results Summary (same row) ===
        action_summary_frame = ttk.Frame(main_frame)
        action_summary_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Run Button on the left
        self.run_btn = ttk.Button(action_summary_frame, text="▶ Run Reconciliation", command=self._run_reconciliation)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Results Summary on the right
        self.summary_frame = ttk.LabelFrame(action_summary_frame, text="Results Summary", padding="5")
        self.summary_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.summary_labels = {}
        summary_items = [
            ("exact_matches", "✓ Matches:"),
            ("date_note", "📅 Date Note:"),
            ("amount_var", "≈ Variance:"),
            ("missing_b", "⚠ Missing B:"),
            ("missing_a", "⚠ Missing A:")
        ]
        
        for i, (key, text) in enumerate(summary_items):
            ttk.Label(self.summary_frame, text=text, font=("", 8)).grid(row=0, column=i * 2, sticky="w", padx=2)
            label = ttk.Label(self.summary_frame, text="--", font=("", 8, "bold"))
            label.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 10))
            self.summary_labels[key] = label
        
        # === Status + Export Buttons (above results) ===
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(controls_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Button(controls_frame, text="Export Current Tab", command=self._export_current).pack(side=tk.RIGHT, padx=5)
        ttk.Button(controls_frame, text="Export All", command=self._export_all).pack(side=tk.RIGHT, padx=5)
        
        # === Results Tabs (at bottom, final element) ===
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.tab_trees = {}
        tab_configs = [
            ("exact_matches", "Exact Matches"),
            ("matches_with_date_note", "Date Notes"),
            ("amount_variances", "Amount Variances"),
            ("missing_in_b", "Missing in B"),
            ("missing_in_a", "Missing in A")
        ]
        
        for table_name, tab_title in tab_configs:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_title)
            
            # Treeview with scrollbars
            tree_frame = ttk.Frame(frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            tree = ttk.Treeview(tree_frame, show="headings")
            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            # Right-click to copy
            tree.bind("<Button-3>", lambda e, t=tree: self._show_context_menu(e, t))
            
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            
            self.tab_trees[table_name] = tree
        
        # Create context menu (not a visual element)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self._copy_cell_value)
    
    def _browse_source_a(self):
        """Browse for Source A file."""
        path = filedialog.askopenfilename(
            title="Select Source A CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.source_a_var.set(path)
            self._load_columns()
    
    def _browse_source_b(self):
        """Browse for Source B file."""
        path = filedialog.askopenfilename(
            title="Select Source B CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.source_b_var.set(path)
            self._load_columns()
    
    def _show_context_menu(self, event, tree):
        """Show context menu for copying cell value."""
        # Select the row under cursor
        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        
        if item and column:
            tree.selection_set(item)
            tree.focus(item)
            self.context_tree = tree
            self.context_column = column
            self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _copy_cell_value(self):
        """Copy the selected cell value to clipboard."""
        if not self.context_tree:
            return
        
        selection = self.context_tree.selection()
        if not selection:
            return
        
        # Get column index (format is "#1", "#2", etc.)
        col_index = int(self.context_column.replace('#', '')) - 1
        
        # Get the row values
        item = selection[0]
        values = self.context_tree.item(item, 'values')
        
        if values and 0 <= col_index < len(values):
            value = str(values[col_index])
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.status_var.set(f"Copied: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir_var.set(path)
    
    def _load_columns(self):
        """Load column names from CSV files and auto-detect column mappings."""
        if self.source_a_var.get() and self.source_b_var.get():
            try:
                # Close previous engine if exists
                if self.temp_engine:
                    self.temp_engine.close()
                
                # Create engine to read headers (keep alive for totals)
                self.temp_engine = ReconEngine()
                self.columns_a = self.temp_engine.load_csv(self.source_a_var.get(), "temp_a")
                self.columns_b = self.temp_engine.load_csv(self.source_b_var.get(), "temp_b")
                
                # Populate all dropdowns
                self.date_col_a_combo['values'] = self.columns_a
                self.date_col_b_combo['values'] = self.columns_b
                self.amount_col_a_combo['values'] = self.columns_a
                self.amount_col_b_combo['values'] = self.columns_b
                self.desc_col_a_combo['values'] = ["(None)"] + self.columns_a
                self.desc_col_b_combo['values'] = ["(None)"] + self.columns_b
                
                # Auto-detect columns using patterns
                detected_date_a = self.temp_engine.detect_column("temp_a", self.date_patterns)
                detected_date_b = self.temp_engine.detect_column("temp_b", self.date_patterns)
                detected_amount_a = self.temp_engine.detect_column("temp_a", self.amount_patterns)
                detected_amount_b = self.temp_engine.detect_column("temp_b", self.amount_patterns)
                detected_desc_a = self.temp_engine.detect_column("temp_a", self.desc_patterns)
                detected_desc_b = self.temp_engine.detect_column("temp_b", self.desc_patterns)
                
                # Set detected values (or first column as fallback)
                self.date_col_a_var.set(detected_date_a or (self.columns_a[0] if self.columns_a else ""))
                self.date_col_b_var.set(detected_date_b or (self.columns_b[0] if self.columns_b else ""))
                self.amount_col_a_var.set(detected_amount_a or (self.columns_a[1] if len(self.columns_a) > 1 else ""))
                self.amount_col_b_var.set(detected_amount_b or (self.columns_b[1] if len(self.columns_b) > 1 else ""))
                self.desc_col_a_var.set(detected_desc_a or "(None)")
                self.desc_col_b_var.set(detected_desc_b or "(None)")
                
                # Auto-clean amount columns if enabled
                if self.auto_clean_var.get():
                    amount_a = self.amount_col_a_var.get()
                    amount_b = self.amount_col_b_var.get()
                    if amount_a:
                        self.temp_engine.clean_amount_column("temp_a", amount_a)
                    if amount_b:
                        self.temp_engine.clean_amount_column("temp_b", amount_b)
                
                # Calculate initial totals
                self._update_totals()
                
                # Match key - common columns only
                common = [c for c in self.columns_a if c in self.columns_b]
                self.match_key_combo['values'] = common
                
                if common:
                    self.match_key_var.set(common[0])
                
                # Update previews
                self._update_preview()
                    
                self.status_var.set(f"Loaded: {len(self.columns_a)} cols from A, {len(self.columns_b)} cols from B (auto-detected)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read CSV headers: {e}")
    
    def _update_preview(self):
        """Update file preview tables with first 3 rows."""
        if not self.temp_engine:
            return
        
        try:
            # Preview Source A
            if self.columns_a:
                self.preview_a_tree.delete(*self.preview_a_tree.get_children())
                self.preview_a_tree["columns"] = self.columns_a
                for col in self.columns_a:
                    self.preview_a_tree.heading(col, text=col)
                    self.preview_a_tree.column(col, width=100, minwidth=50)
                
                # Select columns explicitly in order to match header order
                cols_a_str = ", ".join([f'"{c}"' for c in self.columns_a])
                rows_a = self.temp_engine.conn.execute(f"SELECT {cols_a_str} FROM temp_a LIMIT 3").fetchall()
                for row in rows_a:
                    self.preview_a_tree.insert("", tk.END, values=row)
            
            # Preview Source B
            if self.columns_b:
                self.preview_b_tree.delete(*self.preview_b_tree.get_children())
                self.preview_b_tree["columns"] = self.columns_b
                for col in self.columns_b:
                    self.preview_b_tree.heading(col, text=col)
                    self.preview_b_tree.column(col, width=100, minwidth=50)
                
                # Select columns explicitly in order to match header order
                cols_b_str = ", ".join([f'"{c}"' for c in self.columns_b])
                rows_b = self.temp_engine.conn.execute(f"SELECT {cols_b_str} FROM temp_b LIMIT 3").fetchall()
                for row in rows_b:
                    self.preview_b_tree.insert("", tk.END, values=row)
        except Exception as e:
            print(f"Preview error: {e}")
    
    def _update_totals(self, event=None):
        """Update the amount column totals display."""
        if not self.temp_engine:
            return
        
        try:
            amount_a = self.amount_col_a_var.get()
            amount_b = self.amount_col_b_var.get()
            
            # Get totals (auto-clean first if enabled and column changed)
            if amount_a:
                if self.auto_clean_var.get() and event:
                    # Re-load and clean if column changed
                    pass  # Cleaning already done on initial load
                total_a = self.temp_engine.get_column_sum("temp_a", amount_a)
                if total_a is not None:
                    self.total_a_var.set(f"{total_a:,.2f}")
                else:
                    self.total_a_var.set("N/A")
            else:
                self.total_a_var.set("--")
            
            if amount_b:
                total_b = self.temp_engine.get_column_sum("temp_b", amount_b)
                if total_b is not None:
                    self.total_b_var.set(f"{total_b:,.2f}")
                else:
                    self.total_b_var.set("N/A")
            else:
                self.total_b_var.set("--")
        except Exception as e:
            self.total_a_var.set("Error")
            self.total_b_var.set("Error")
    
    def _run_reconciliation(self):
        """Run the reconciliation process."""
        # Validate inputs
        if not self.source_a_var.get():
            messagebox.showwarning("Missing Input", "Please select Source A file")
            return
        if not self.source_b_var.get():
            messagebox.showwarning("Missing Input", "Please select Source B file")
            return
        if not self.match_key_var.get():
            messagebox.showwarning("Missing Input", "Please select a match key")
            return
        
        try:
            tolerance = float(self.tolerance_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Input", "Amount tolerance must be a number")
            return
        
        # Disable button during processing
        self.run_btn.configure(state="disabled")
        self.status_var.set("Processing...")
        
        # Run in background thread
        def process():
            try:
                # Initialize engine
                self.engine = ReconEngine()
                
                # Load files
                self.status_var.set("Loading Source A...")
                self.engine.load_csv(self.source_a_var.get(), "source_a")
                
                self.status_var.set("Loading Source B...")
                self.engine.load_csv(self.source_b_var.get(), "source_b")
                
                # Clean amount columns to ensure they are numeric (fixes VARCHAR - DOUBLE type mismatch)
                if self.auto_clean_var.get():
                    self.status_var.set("Cleaning amount columns...")
                    amount_a = self.amount_col_a_var.get()
                    amount_b = self.amount_col_b_var.get()
                    if amount_a:
                        self.engine.clean_amount_column("source_a", amount_a)
                    if amount_b:
                        self.engine.clean_amount_column("source_b", amount_b)
                    
                    # Clean date columns to normalize formats (MM/DD/YYYY -> YYYY-MM-DD)
                    self.status_var.set("Normalizing date formats...")
                    date_a = self.date_col_a_var.get()
                    date_b = self.date_col_b_var.get()
                    if date_a:
                        self.engine.clean_date_column("source_a", date_a)
                    if date_b:
                        self.engine.clean_date_column("source_b", date_b)
                
                # Run reconciliation
                self.status_var.set("Running reconciliation...")
                
                # Get column mappings (convert "(None)" to Python None)
                desc_a = self.desc_col_a_var.get()
                desc_b = self.desc_col_b_var.get()
                
                config = ReconConfig(
                    source_a_path=self.source_a_var.get(),
                    source_b_path=self.source_b_var.get(),
                    output_dir=self.output_dir_var.get(),
                    match_key=self.match_key_var.get(),
                    amount_tolerance=tolerance,
                    date_col_a=self.date_col_a_var.get(),
                    date_col_b=self.date_col_b_var.get(),
                    amount_col_a=self.amount_col_a_var.get(),
                    amount_col_b=self.amount_col_b_var.get(),
                    description_col_a=desc_a if desc_a != "(None)" else None,
                    description_col_b=desc_b if desc_b != "(None)" else None
                )
                self.result = self.engine.reconcile(config)
                
                # Update UI in main thread
                self.root.after(0, self._update_results)
                
            except Exception as e:
                error_msg = str(e)  # Capture before lambda (Python 3.13 scoping fix)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            finally:
                self.root.after(0, lambda: self.run_btn.configure(state="normal"))
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
    
    def _update_results(self):
        """Update the UI with reconciliation results."""
        if not self.result:
            return
        
        summary = self.result.summary
        
        # Update summary labels
        self.summary_labels["exact_matches"].configure(text=f"{summary.exact_matches:,}")
        self.summary_labels["date_note"].configure(text=f"{summary.matches_with_date_note:,}")
        self.summary_labels["amount_var"].configure(text=f"{summary.amount_variances:,}")
        self.summary_labels["missing_b"].configure(text=f"{summary.missing_in_b:,}")
        self.summary_labels["missing_a"].configure(text=f"{summary.missing_in_a:,}")
        
        # Update each tab with data
        tables = [
            "exact_matches",
            "matches_with_date_note", 
            "amount_variances",
            "missing_in_b",
            "missing_in_a"
        ]
        
        for table_name in tables:
            tree = self.tab_trees[table_name]
            
            # Clear existing
            tree.delete(*tree.get_children())
            
            # Get columns and data
            try:
                columns = self.engine.get_result_columns(table_name)
                data = self.engine.get_results(table_name, limit=1000)
                
                # Configure columns
                tree["columns"] = columns
                for col in columns:
                    tree.heading(col, text=col)
                    tree.column(col, width=100, minwidth=50)
                
                # Insert data
                for row in data:
                    tree.insert("", tk.END, values=row)
                    
            except Exception as e:
                print(f"Error loading {table_name}: {e}")
        
        total_matched = summary.total_matched
        total_issues = summary.total_unmatched
        self.status_var.set(f"Complete: {total_matched:,} matched, {total_issues:,} issues found")
    
    def _export_all(self):
        """Export all result tables to CSV."""
        if not self.result or not self.engine:
            messagebox.showwarning("No Results", "Run reconciliation first")
            return
        
        # Prompt for output directory if not set
        output_dir = self.output_dir_var.get()
        if not output_dir:
            output_dir = filedialog.askdirectory(title="Select Output Directory for Export")
            if not output_dir:
                return  # User cancelled
            self.output_dir_var.set(output_dir)
            self.result.config.output_dir = output_dir
        
        try:
            exporter = Exporter(self.engine)
            exported = exporter.export_all(self.result)
            messagebox.showinfo("Export Complete", f"Exported {len(exported)} files to:\n{output_dir}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def _export_current(self):
        """Export the current tab's results to CSV."""
        if not self.result or not self.engine:
            messagebox.showwarning("No Results", "Run reconciliation first")
            return
        
        # Prompt for output directory if not set
        output_dir = self.output_dir_var.get()
        if not output_dir:
            output_dir = filedialog.askdirectory(title="Select Output Directory for Export")
            if not output_dir:
                return  # User cancelled
            self.output_dir_var.set(output_dir)
            self.result.config.output_dir = output_dir
        
        # Get current tab
        tab_index = self.notebook.index(self.notebook.select())
        table_names = ["exact_matches", "matches_with_date_note", "amount_variances", "missing_in_b", "missing_in_a"]
        table_name = table_names[tab_index]
        
        try:
            exporter = Exporter(self.engine)
            path = exporter.export_table(table_name, output_dir)
            messagebox.showinfo("Export Complete", f"Exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


def main():
    """Launch the application."""
    root = tk.Tk()
    app = ReconApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
