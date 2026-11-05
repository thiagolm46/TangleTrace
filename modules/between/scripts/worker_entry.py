"""PyInstaller entry point that preserves relative imports within app."""
from app.worker import main
from multiprocessing import freeze_support

if __name__ == '__main__':
    freeze_support()
    main()
