import inspect
import volcenginesdk
from volcenginesdk.rest import ApiException

print("Volcengine SDK installed.")
print(f"Version: {volcenginesdk.__version__}")

# Try to find video generation related modules
print("\nSearching for 'video' in volcenginesdk modules...")
for name, obj in inspect.getmembers(volcenginesdk):
    if "video" in name.lower() or "cv" in name.lower() or "ark" in name.lower():
        print(f"Found module/class: {name}")

# Try to import specific CV or Video modules if they exist
try:
    from volcenginesdkcv20240606 import Cv20240606Api
    print("\nFound Cv20240606Api")
except ImportError:
    print("\nCv20240606Api not found")

try:
    from volcenginesdkark import ArkApi
    print("\nFound ArkApi")
except ImportError:
    print("\nArkApi not found")
