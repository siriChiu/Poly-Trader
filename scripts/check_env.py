#!/usr/bin/env python3
import sys
print(f"Python: {sys.executable}")
try:
    import pandas; print(f"pandas: {pandas.__version__}")
except: print("pandas: MISSING")
try:
    import numpy; print(f"numpy: {numpy.__version__}")
except: print("numpy: MISSING")
try:
    import scipy; print(f"scipy: {scipy.__version__}")
except: print("scipy: MISSING")
