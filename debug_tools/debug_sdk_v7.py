import volcenginesdkarkruntime
import inspect

try:
    client = volcenginesdkarkruntime.Ark(api_key="test")
    sig = inspect.signature(client.content_generation.tasks.create)
    print(f"Signature: {sig}")
except Exception as e:
    print(f"Error: {e}")
