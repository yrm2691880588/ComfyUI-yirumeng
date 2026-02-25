import volcenginesdkarkruntime

print("Inspecting Ark Client Content Generation Tasks...")
try:
    client = volcenginesdkarkruntime.Ark(api_key="test")
    
    print("\nclient.content_generation.tasks:")
    print([m for m in dir(client.content_generation.tasks) if not m.startswith('_')])
    
    # Also check if there are sub-resources
    if hasattr(client.content_generation.tasks, 'create_task'):
        print("Found create_task")
    if hasattr(client.content_generation.tasks, 'create'):
        print("Found create")

except Exception as e:
    print(f"Error: {e}")
