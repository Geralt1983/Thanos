
import os
import sys

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")

try:
    import litellm
    print("litellm is installed.")
    print(f"litellm version: {litellm.__version__ if hasattr(litellm, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"litellm is NOT installed or failed to import: {e}")

try:
    import dotenv
    print("python-dotenv is installed.")
    dotenv.load_dotenv("c:\\Projects\\Thanos\\.env")
    print("Loaded .env file manually.")
except ImportError:
    print("python-dotenv is NOT installed.")

try:
    import anthropic
    print("anthropic is installed.")
except ImportError:
    print("anthropic is NOT installed.")

try:
    import openai
    print("openai is installed.")
except ImportError:
    print("openai is NOT installed.")

print("\nEnvironment Variables:")
print(f"ANTHROPIC_API_KEY set: {'ANTHROPIC_API_KEY' in os.environ}")
print(f"OPENAI_API_KEY set: {'OPENAI_API_KEY' in os.environ}")
print(f"GEMINI_API_KEY set: {'GEMINI_API_KEY' in os.environ}")
