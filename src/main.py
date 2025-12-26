"""Entry point for the Data Processing Toolkit."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from home_screen import HomeScreen
from recon_engine import ReconEngine


class DataToolkitApp:
    """
    Main application controller for the Data Processing Toolkit.
    
    Manages navigation between tools and provides shared resources (engine).
    """
    
    def __init__(self):
        """Initialize the application."""
        self.root = tk.Tk()
        self.root.title("Data Processing Toolkit")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Shared engine instance - managed by controller
        self._engine: Optional[ReconEngine] = None
        
        # Container for switching frames
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.current_frame: Optional[ttk.Frame] = None
        self.show_home()
        
        # Cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    @property
    def engine(self) -> ReconEngine:
        """Lazy-load shared engine instance."""
        if self._engine is None:
            self._engine = ReconEngine()
        return self._engine
    
    def reset_engine(self):
        """Reset engine state (e.g., when switching tools)."""
        if self._engine is not None:
            self._engine.close()
            self._engine = None
    
    def show_home(self):
        """Display home screen."""
        self._clear_frame()
        self.current_frame = HomeScreen(self.container, self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_tool(self, tool_name: str):
        """
        Switch to specific tool.
        
        Args:
            tool_name: Tool identifier ('reconcile', 'clean', 'aggregate', 'analyze', 'pastel')
        """
        self._clear_frame()
        
        # Reset engine when switching tools to free memory
        self.reset_engine()
        
        # Lazy import tools to avoid circular imports
        tool_class = None
        
        if tool_name == 'reconcile':
            from app import ReconApp
            # ReconApp needs special handling - it expects root, not parent frame
            self._show_recon_app()
            return
        elif tool_name == 'clean':
            from data_cleaner import DataCleaner
            tool_class = DataCleaner
        elif tool_name == 'aggregate':
            from data_aggregator import DataAggregator
            tool_class = DataAggregator
        elif tool_name == 'analyze':
            from data_analyzer import DataAnalyzer
            tool_class = DataAnalyzer
        elif tool_name == 'pastel':
            self._show_coming_soon("Pastel Import")
            return
        else:
            messagebox.showerror("Error", f"Unknown tool: {tool_name}")
            self.show_home()
            return
        
        try:
            # Pass controller (self) so tools can access shared engine
            self.current_frame = tool_class(
                self.container, 
                controller=self, 
                on_back=self.show_home
            )
            self.current_frame.pack(fill=tk.BOTH, expand=True)
        except ImportError as e:
            messagebox.showerror("Error", f"Tool not yet implemented: {e}")
            self.show_home()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tool: {e}")
            self.show_home()
    
    def _show_recon_app(self):
        """Special handling for ReconApp which uses the old architecture."""
        from app import ReconApp
        
        # Create a new Toplevel window for ReconApp
        recon_window = tk.Toplevel(self.root)
        recon_window.title("Reconciliation Tool")
        recon_window.geometry("900x900")
        
        # Create the ReconApp in the new window
        app = ReconApp(recon_window)
        
        # Handle window close - return to home
        def on_close():
            # Close the recon window, then restore the main UI (home screen)
            try:
                recon_window.destroy()
            finally:
                # The main window's container was cleared when the tool launched,
                # so we need to recreate the HomeScreen to avoid a blank page.
                try:
                    self.root.deiconify()
                    self.root.lift()
                except Exception:
                    pass
                self.show_home()
        
        recon_window.protocol("WM_DELETE_WINDOW", on_close)
    
    def _show_coming_soon(self, feature_name: str):
        """Show coming soon message for deferred features."""
        messagebox.showinfo(
            "Coming Soon",
            f"{feature_name} will be available in a future update.\n\n"
            "This feature is currently being developed."
        )
        self.show_home()
    
    def _clear_frame(self):
        """Destroy current frame."""
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None
    
    def _on_close(self):
        """Cleanup and close application."""
        self.reset_engine()
        self.root.destroy()
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    """Launch the Data Processing Toolkit."""
    app = DataToolkitApp()
    app.run()


if __name__ == "__main__":
    main()
