import sys
from pathlib import Path

# Модули приложения лежат в app/, тесты — в app/tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
