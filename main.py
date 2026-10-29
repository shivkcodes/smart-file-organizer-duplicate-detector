"""Launch the Smart File Organizer desktop application."""
from tkinter import Tk

from gui.main_window import MainWindow


def main() -> None:
    root = Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
