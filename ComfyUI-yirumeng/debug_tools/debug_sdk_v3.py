import volcenginesdkarkruntime

print("Ark Client methods:")
try:
    client = volcenginesdkarkruntime.Ark(api_key="test")
    methods = [m for m in dir(client) if not m.startswith('_')]
    print(methods)
    
    # Check for likely candidates
    candidates = ['video', 'videos', 'content', 'generation', 'cv']
    for c in candidates:
        if hasattr(client, c):
            print(f"\nFound attribute '{c}':")
            attr = getattr(client, c)
            print(dir(attr))
            
except Exception as e:
    print(f"Error: {e}")
