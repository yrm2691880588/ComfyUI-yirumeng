import inspect

try:
    import volcenginesdkarkruntime
    print("Inspect volcenginesdkarkruntime:")
    print(dir(volcenginesdkarkruntime))
    if hasattr(volcenginesdkarkruntime, 'Ark'):
        print("\nArk Client methods:")
        client = volcenginesdkarkruntime.Ark(api_key="test")
        print([m for m in dir(client) if not m.startswith('_')])
        
        if hasattr(client, 'video'):
            print("\nArk.video methods:")
            print(dir(client.video))
            
except ImportError as e:
    print(f"volcenginesdkarkruntime import error: {e}")

print("-" * 50)

try:
    import volcenginesdkcv20240606
    print("Inspect volcenginesdkcv20240606:")
    # usually has an ApiClient or similar
    print(dir(volcenginesdkcv20240606))
    
except ImportError as e:
    print(f"volcenginesdkcv20240606 import error: {e}")
