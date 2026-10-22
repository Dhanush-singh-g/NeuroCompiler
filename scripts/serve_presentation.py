"""Launch the live NeuroCompiler decision explorer from the repository root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.presentation.server import main

if __name__ == '__main__':
    main()
