"""Base Tool class with common UI patterns for all data processing tools."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional, Callable, List, Any
from abc import ABC, abstractmethod


class BaseTool(ttk.Frame):
    """
    Abstract base class for all data processing tools.
    
    Provides common UI components and utilities:
    - File browser dialogs
    - Preview tables (Treeview)
    - Status bar
    - Context menu (right-click copy)
    - Threading helpers for background processing
    - Column auto-detection
    - Navigation (back to home)
    """
    
    def __init__(self, parent: tk.Widget, controller=None, on_back: Optional[Callable] = None):
        """
        Initialize the base tool.
        
        Args:
            parent: Parent widget
            controller: Application controller with shared engine access
            on_back: Callback function to return to home screen
        """
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.on_back = on_back
        
        # Status variable
        self.status_var = tk.StringVar(value="Ready")
        
        # Context menu for copying
        self._context_menu: Optional[tk.Menu] = None
        self._context_tree: Optional[ttk.Treeview] = None
        self._context_column: str = ""
        
        # Progress indicator
        self._progress_label: Optional[ttk.Label] = None
        self._progress_bar: Optional[ttk.Progressbar] = None
        
        # Threading
        self._update_timer: Optional[str] = None
        
        # Auto-detection patterns
        self.date_patterns = ["date", "dt", "trans_date", "posting", "created", "updated"]
        self.amount_patterns = ["amount", "amt", "value", "total", "sum", "price", "cost"]
        self.desc_patterns = ["description", "desc", "narration", "memo", "reference", "note"]
    
    @property
    def engine(self):
        """Access shared ReconEngine instance from controller."""
        if self.controller:
            return self.controller.engine
        return None
    
    # =========================================================================
    # UI Component Factories
    # =========================================================================
    
    def create_header(self, title: str) -> ttk.Frame:
        """
        Create a header with back button and title.
        
        Args:
            title: Tool title to display
            
        Returns:
            Header frame widget
        """
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        if self.on_back:
            back_btn = ttk.Button(
                header_frame, 
                text="← Back to Home", 
                command=self._back_to_home
            )
            back_btn.pack(side=tk.LEFT)
        
        title_label = ttk.Label(
            header_frame, 
            text=title, 
            font=("", 14, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=20)
        
        return header_frame
    
    def create_file_selector(
        self, 
        parent: tk.Widget, 
        label: str, 
        variable: tk.StringVar,
        browse_command: Optional[Callable] = None,
        filetypes: List[tuple] = None
    ) -> ttk.Frame:
        """
        Create a file selector with label, entry, and browse button.
        
        Args:
            parent: Parent widget
            label: Label text
            variable: StringVar to bind to entry
            browse_command: Custom browse command (uses default if None)
            filetypes: List of (label, pattern) tuples for file dialog
            
        Returns:
            Frame containing the file selector widgets
        """
        frame = ttk.Frame(parent)
        
        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        entry = ttk.Entry(frame, textvariable=variable, width=60)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        if browse_command is None:
            filetypes = filetypes or [("CSV files", "*.csv"), ("All files", "*.*")]
            browse_command = lambda: self._browse_file(variable, filetypes)
        
        ttk.Button(frame, text="Browse", command=browse_command).pack(side=tk.LEFT)
        
        return frame
    
    def create_preview_table(
        self, 
        parent: tk.Widget, 
        label: str = "Preview",
        height: int = 5,
        show_scrollbars: bool = True
    ) -> ttk.Treeview:
        """
        Create a preview table with optional scrollbars.
        
        Args:
            parent: Parent widget
            label: Label for the preview section
            height: Number of visible rows
            show_scrollbars: Whether to add scrollbars
            
        Returns:
            Treeview widget
        """
        # Container with label
        container = ttk.LabelFrame(parent, text=label, padding="5")
        container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Frame for tree and scrollbars
        tree_frame = ttk.Frame(container)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(tree_frame, show="headings", height=height)
        
        if show_scrollbars:
            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
        else:
            tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind right-click for context menu
        tree.bind("<Button-3>", lambda e: self._show_context_menu(e, tree))
        
        return tree
    
    def create_status_bar(self, parent: tk.Widget) -> ttk.Frame:
        """
        Create a status bar at the bottom.
        
        Args:
            parent: Parent widget
            
        Returns:
            Status bar frame
        """
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Progress bar (hidden by default)
        self._progress_bar = ttk.Progressbar(
            status_frame, 
            mode="indeterminate", 
            length=150
        )
        
        return status_frame
    
    # =========================================================================
    # Preview Table Utilities
    # =========================================================================
    
    def update_preview(
        self, 
        tree: ttk.Treeview, 
        table_name: str, 
        columns: List[str],
        limit: int = 5
    ):
        """
        Update preview table with data from DuckDB table.
        
        Args:
            tree: Treeview widget to update
            table_name: Name of the DuckDB table
            columns: List of column names
            limit: Number of rows to show
        """
        if not self.engine or not columns:
            return
        
        try:
            # Clear existing data
            tree.delete(*tree.get_children())
            
            # Configure columns
            tree["columns"] = columns
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100, minwidth=50)
            
            # Fetch and insert data
            cols_str = ", ".join([f'"{c}"' for c in columns])
            rows = self.engine.conn.execute(
                f"SELECT {cols_str} FROM {table_name} LIMIT {limit}"
            ).fetchall()
            
            for row in rows:
                tree.insert("", tk.END, values=row)
                
        except Exception as e:
            print(f"Preview error for {table_name}: {e}")
    
    # =========================================================================
    # Context Menu (Copy)
    # =========================================================================
    
    def _show_context_menu(self, event, tree: ttk.Treeview):
        """Show context menu for copying cell value."""
        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        
        if item and column:
            tree.selection_set(item)
            tree.focus(item)
            self._context_tree = tree
            self._context_column = column
            
            # Create menu if needed
            if self._context_menu is None:
                self._context_menu = tk.Menu(self, tearoff=0)
                self._context_menu.add_command(label="Copy", command=self._copy_cell_value)
            
            self._context_menu.tk_popup(event.x_root, event.y_root)
    
    def _copy_cell_value(self):
        """Copy the selected cell value to clipboard."""
        if not self._context_tree:
            return
        
        selection = self._context_tree.selection()
        if not selection:
            return
        
        # Get column index (format is "#1", "#2", etc.)
        col_index = int(self._context_column.replace('#', '')) - 1
        
        # Get the row values
        item = selection[0]
        values = self._context_tree.item(item, 'values')
        
        if values and 0 <= col_index < len(values):
            value = str(values[col_index])
            self.clipboard_clear()
            self.clipboard_append(value)
            self._show_status(f"Copied: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    # =========================================================================
    # File Browsing
    # =========================================================================
    
    def _browse_file(
        self, 
        variable: tk.StringVar, 
        filetypes: List[tuple],
        title: str = "Select File"
    ):
        """Open file dialog and set variable."""
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            variable.set(path)
            self._on_file_selected(path)
    
    def _browse_directory(
        self, 
        variable: tk.StringVar,
        title: str = "Select Directory"
    ):
        """Open directory dialog and set variable."""
        path = filedialog.askdirectory(title=title)
        if path:
            variable.set(path)
    
    def _on_file_selected(self, path: str):
        """
        Called when a file is selected. Override in subclasses.
        
        Args:
            path: Path to the selected file
        """
        pass
    
    # =========================================================================
    # Column Detection
    # =========================================================================
    
    def detect_column(
        self, 
        table_name: str, 
        patterns: List[str]
    ) -> Optional[str]:
        """
        Find first column matching any pattern (case-insensitive).
        
        Args:
            table_name: Name of the DuckDB table
            patterns: List of substring patterns to match
            
        Returns:
            Column name if found, None otherwise
        """
        if self.engine:
            return self.engine.detect_column(table_name, patterns)
        return None
    
    def detect_date_column(self, table_name: str) -> Optional[str]:
        """Detect date column in table."""
        return self.detect_column(table_name, self.date_patterns)
    
    def detect_amount_column(self, table_name: str) -> Optional[str]:
        """Detect amount column in table."""
        return self.detect_column(table_name, self.amount_patterns)
    
    def detect_description_column(self, table_name: str) -> Optional[str]:
        """Detect description column in table."""
        return self.detect_column(table_name, self.desc_patterns)
    
    # =========================================================================
    # Threading Helpers
    # =========================================================================
    
    def run_threaded(
        self, 
        target_func: Callable,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        progress_message: str = "Processing...",
        *args, 
        **kwargs
    ):
        """
        Run operation in background thread with UI feedback.
        
        Args:
            target_func: Function to run in background
            on_complete: Callback with result when complete
            on_error: Callback with exception on error
            progress_message: Status message during processing
            *args, **kwargs: Arguments passed to target_func
        """
        self._show_progress(progress_message)
        
        def worker():
            try:
                result = target_func(*args, **kwargs)
                self.after(0, lambda: self._on_thread_complete(result, on_complete))
            except Exception as e:
                self.after(0, lambda: self._on_thread_error(e, on_error))
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _on_thread_complete(self, result: Any, on_complete: Optional[Callable]):
        """Handle thread completion, update UI."""
        self._hide_progress()
        if on_complete:
            on_complete(result)
    
    def _on_thread_error(self, error: Exception, on_error: Optional[Callable]):
        """Handle thread error."""
        self._hide_progress()
        if on_error:
            on_error(error)
        else:
            messagebox.showerror("Error", str(error))
    
    def _show_progress(self, message: str):
        """Show progress indicator and update status."""
        self.status_var.set(message)
        if self._progress_bar:
            self._progress_bar.pack(side=tk.RIGHT, padx=5)
            self._progress_bar.start(10)
    
    def _hide_progress(self):
        """Hide progress indicator."""
        if self._progress_bar:
            self._progress_bar.stop()
            self._progress_bar.pack_forget()
    
    def schedule_update(self, callback: Callable, delay_ms: int = 300):
        """
        Schedule a debounced update (cancels previous pending update).
        
        Args:
            callback: Function to call
            delay_ms: Delay in milliseconds
        """
        if self._update_timer:
            self.after_cancel(self._update_timer)
        self._update_timer = self.after(delay_ms, callback)
    
    # =========================================================================
    # Status & Navigation
    # =========================================================================
    
    def _show_status(self, message: str):
        """Update status bar message."""
        self.status_var.set(message)
    
    def _back_to_home(self):
        """Navigate back to home screen."""
        if self.on_back:
            self.on_back()
    
    # =========================================================================
    # Export Utilities
    # =========================================================================
    
    def export_to_csv(
        self, 
        table_name: str, 
        output_dir: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Export a DuckDB table to CSV.
        
        Args:
            table_name: Name of the table to export
            output_dir: Output directory (prompts if None)
            filename: Custom filename (uses table_name if None)
            
        Returns:
            Path to exported file, or None if cancelled
        """
        if not self.engine:
            messagebox.showwarning("No Data", "No data to export")
            return None
        
        if not output_dir:
            output_dir = filedialog.askdirectory(title="Select Output Directory")
            if not output_dir:
                return None
        
        try:
            filename = filename or f"{table_name}.csv"
            output_path = f"{output_dir}/{filename}"
            self.engine.export_table(table_name, output_path)
            self._show_status(f"Exported: {filename}")
            return output_path
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            return None


class ToolError(Exception):
    """Base exception for tool errors."""
    pass


class FileValidationError(ToolError):
    """File validation failed."""
    pass


class DataProcessingError(ToolError):
    """Data processing failed."""
    pass
