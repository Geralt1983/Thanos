
import os
import subprocess
import time
import socket
from pathlib import Path
import sys

# Define default paths
PROJECT_ROOT = Path(__file__).parent.parent
MEMORY_DIR = Path.home() / ".claude" / "Memory" / "vectors"
CHROMA_PORT = 8000
START_SCRIPT = PROJECT_ROOT / "Tools" / "scripts" / "start_chroma.sh"

class ServerManager:
    """Manages background server processes for Thanos."""
    
    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """Check if a port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    @staticmethod
    def ensure_chroma_running():
        """Ensure ChromaDB server is running, spawn if not."""
        if ServerManager.is_port_in_use(CHROMA_PORT):
            # Already running
            return True
            
        print(f"[Thanos] Starting Memory Server (ChromaDB) on port {CHROMA_PORT}...")
        
        try:
            # We use the script we created earlier
            # Use subprocess.Popen to run in background
            # stdout/stderr to devnull to avoid cluttering the CLI
            with open(os.devnull, 'w') as devnull:
                subprocess.Popen(
                    [str(START_SCRIPT)], 
                    stdout=devnull, 
                    stderr=devnull,
                    cwd=str(PROJECT_ROOT)
                )
            
            # Wait a moment for startup
            print("[Thanos] Waiting for Memory Server to initialize...")
            for _ in range(10):  # Wait up to 5 seconds
                if ServerManager.is_port_in_use(CHROMA_PORT):
                    print("[Thanos] Memory Server connected.")
                    return True
                time.sleep(0.5)
                
            print("[Thanos] Warning: Memory Server started but port check failed.")
            return False
            
        except Exception as e:
            print(f"[Thanos] Error starting Memory Server: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        if ServerManager.is_port_in_use(CHROMA_PORT):
            print("ChromaDB is running.")
        else:
            print("ChromaDB is NOT running.")
    elif len(sys.argv) > 1 and sys.argv[1] == "start":
        ServerManager.ensure_chroma_running()
