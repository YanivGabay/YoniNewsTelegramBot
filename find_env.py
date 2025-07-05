import os
from dotenv import load_dotenv, find_dotenv

print("🔍 Finding .env file location...")

# Find the .env file that python-dotenv would load
env_path = find_dotenv()
if env_path:
    print(f"📄 Found .env file at: {env_path}")
    print(f"📁 Absolute path: {os.path.abspath(env_path)}")
    
    # Read the file content
    try:
        with open(env_path, 'r') as f:
            content = f.read()
        print(f"\n📝 Contents of {env_path}:")
        print("=" * 50)
        print(content)
        print("=" * 50)
        
        # Check specifically for TELEGRAM_CHAT_IDS
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'TELEGRAM_CHAT_IDS' in line:
                print(f"🎯 Line {i}: {line}")
                
    except Exception as e:
        print(f"❌ Error reading file: {e}")
else:
    print("❌ No .env file found!")

print(f"\n📁 Current working directory: {os.getcwd()}")

# Also check if there's a .env in current directory
local_env = ".env"
if os.path.exists(local_env):
    print(f"\n📄 Also found .env in current directory:")
    try:
        with open(local_env, 'r') as f:
            content = f.read()
        print("=" * 30)
        print(content)
        print("=" * 30)
    except Exception as e:
        print(f"❌ Error reading local .env: {e}")
else:
    print(f"\n❌ No .env file in current directory: {os.getcwd()}") 