import pkg_resources
import os

try:
    dist = pkg_resources.get_distribution("volcengine-python-sdk")
    print(f"Package found: {dist}")
    print(f"Location: {dist.location}")
    
    # List top level modules
    if dist.has_metadata('top_level.txt'):
        print("Top level modules:")
        for line in dist.get_metadata_lines('top_level.txt'):
            print(f"  - {line}")
            
except Exception as e:
    print(f"Error: {e}")
