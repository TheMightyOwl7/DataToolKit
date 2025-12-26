"""Home Screen Launcher for the Data Processing Toolkit."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class HomeScreen(ttk.Frame):
    """
    Home screen launcher with tool selection grid.
    
    Displays a grid of tool buttons that launch each data processing tool.
    """
    
    # Tool configuration: (tool_id, icon, title, description, enabled)
    TOOLS = [
        ("reconcile", "🔄", "Reconcile Files", "Compare and match records between two CSV files", True),
        ("clean", "🧹", "Clean Data", "Standardize formats, remove duplicates, fix data types", True),
        ("aggregate", "📊", "Aggregate Data", "Combine files and group by categories", True),
        ("analyze", "🔍", "Analyze Data", "Filter by ranges and calculate statistics", True),
        ("pastel", "📋", "Pastel Import", "Generate Pastel-compatible import files", False),
    ]
    
    VERSION = "2.0.0"
    
    def __init__(self, parent: tk.Widget, controller):
        """
        Initialize the home screen.
        
        Args:
            parent: Parent widget
            controller: Application controller with show_tool method
        """
        super().__init__(parent)
        self.controller = controller
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all home screen widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        self._create_header(main_frame)
        
        # Tool grid
        self._create_tool_grid(main_frame)
        
        # Footer with version info
        self._create_footer(main_frame)
    
    def _create_header(self, parent: tk.Widget):
        """Create the header with title."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="📁 Data Processing Toolkit",
            font=("", 20, "bold")
        )
        title_label.pack()
        
        # Subtitle
        subtitle_label = ttk.Label(
            header_frame,
            text="Select a tool to get started",
            font=("", 10)
        )
        subtitle_label.pack(pady=(5, 0))
    
    def _create_tool_grid(self, parent: tk.Widget):
        """Create the grid of tool buttons."""
        # Grid container - centered
        grid_frame = ttk.Frame(parent)
        grid_frame.pack(expand=True)
        
        # Create tool buttons in a 2-column grid
        row = 0
        col = 0
        
        for tool_id, icon, title, description, enabled in self.TOOLS:
            tool_btn = self._create_tool_button(
                grid_frame,
                icon=icon,
                title=title,
                description=description,
                enabled=enabled,
                command=lambda tid=tool_id: self._on_tool_click(tid)
            )
            tool_btn.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        # Configure grid weights for even spacing
        for i in range(2):
            grid_frame.grid_columnconfigure(i, weight=1)
    
    def _create_tool_button(
        self,
        parent: tk.Widget,
        icon: str,
        title: str,
        description: str,
        enabled: bool,
        command: Callable
    ) -> ttk.Frame:
        """
        Create a large tool button with icon, title, and description.
        
        Args:
            parent: Parent widget
            icon: Emoji icon
            title: Tool title
            description: Tool description
            enabled: Whether the tool is enabled
            command: Callback when clicked
            
        Returns:
            Frame containing the button
        """
        # Container frame for the button
        btn_frame = ttk.Frame(parent, relief="raised", borderwidth=1)
        btn_frame.configure(padding="20")
        
        # Icon (large)
        icon_label = ttk.Label(
            btn_frame,
            text=icon,
            font=("", 32)
        )
        icon_label.pack()
        
        # Title
        title_label = ttk.Label(
            btn_frame,
            text=title,
            font=("", 12, "bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Description
        desc_label = ttk.Label(
            btn_frame,
            text=description,
            font=("", 9),
            wraplength=180,
            justify="center"
        )
        desc_label.pack()
        
        # Coming Soon badge for disabled tools
        if not enabled:
            badge_label = ttk.Label(
                btn_frame,
                text="Coming Soon",
                font=("", 8, "italic"),
                foreground="gray"
            )
            badge_label.pack(pady=(5, 0))
        
        # Make the entire frame clickable
        if enabled:
            # Bind click events to all widgets
            for widget in [btn_frame, icon_label, title_label, desc_label]:
                widget.bind("<Button-1>", lambda e, cmd=command: cmd())
                widget.bind("<Enter>", lambda e, f=btn_frame: self._on_hover_enter(f))
                widget.bind("<Leave>", lambda e, f=btn_frame: self._on_hover_leave(f))
            
            # Cursor change
            btn_frame.configure(cursor="hand2")
            icon_label.configure(cursor="hand2")
            title_label.configure(cursor="hand2")
            desc_label.configure(cursor="hand2")
        else:
            # Dim disabled tools
            icon_label.configure(foreground="gray")
            title_label.configure(foreground="gray")
            desc_label.configure(foreground="gray")
        
        return btn_frame
    
    def _on_hover_enter(self, frame: ttk.Frame):
        """Handle mouse enter on tool button."""
        frame.configure(relief="groove")
    
    def _on_hover_leave(self, frame: ttk.Frame):
        """Handle mouse leave on tool button."""
        frame.configure(relief="raised")
    
    def _on_tool_click(self, tool_id: str):
        """Handle tool button click."""
        if self.controller:
            self.controller.show_tool(tool_id)
    
    def _create_footer(self, parent: tk.Widget):
        """Create the footer with version info."""
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(fill=tk.X, pady=(30, 0))
        
        # Version
        version_label = ttk.Label(
            footer_frame,
            text=f"Version {self.VERSION}",
            font=("", 8),
            foreground="gray"
        )
        version_label.pack(side=tk.LEFT)
        
        # Status
        status_label = ttk.Label(
            footer_frame,
            text="Ready",
            font=("", 8),
            foreground="gray"
        )
        status_label.pack(side=tk.RIGHT)
