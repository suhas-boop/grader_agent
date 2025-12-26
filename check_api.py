
import os
import sys

sys.path.append(os.getcwd())

from src.utils.llm_client import LLMClient

try:
    print("Initializing LLM Client...")
    # This will print models if key is valid for listing
    client = LLMClient()
    
    print("\nAttempting generation...")
    response = client.generate("Say 'API Key is working!' if you can hear me.")
    
    if response:
        print(f"\nSUCCESS: Received response:\n{response}")
    else:
        print("\nFAILURE: No response received (check logs/key).")

except Exception as e:
    print(f"\nERROR: {e}")
