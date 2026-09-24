"""
main.py — titik masuk aplikasi Import IA.
"""
import tkinter as tk
from tkinter import messagebox

try:
    from ui_app import AutoImportApp
except Exception as e:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("Import IA — Error Startup", str(e))
    raise SystemExit(1)

if __name__ == "__main__":
    app = AutoImportApp()
    app.mainloop()