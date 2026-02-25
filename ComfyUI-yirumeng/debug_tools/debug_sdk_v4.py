import volcenginesdkarkruntime

print("Inspecting Ark Client attributes...")
try:
    client = volcenginesdkarkruntime.Ark(api_key="test")
    
    if hasattr(client, 'content_generation'):
        print("\nclient.content_generation:")
        print([m for m in dir(client.content_generation) if not m.startswith('_')])
        
    if hasattr(client, 'images'):
        print("\nclient.images:")
        print([m for m in dir(client.images) if not m.startswith('_')])

except Exception as e:
    print(f"Error: {e}")
