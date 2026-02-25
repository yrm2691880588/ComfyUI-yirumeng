import volcenginesdkarkruntime

print("Help on create:")
try:
    client = volcenginesdkarkruntime.Ark(api_key="test")
    print(client.content_generation.tasks.create.__doc__)
except Exception as e:
    print(f"Error: {e}")
