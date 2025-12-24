import subprocess
import time
import sys
import os

def run_bot():
    # Get the current python executable path
    python_executable = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), 'bot.py')

    print("🚀 Starting Music Bot with auto-restart enabled...")
    
    while True:
        try:
            # Run the bot process
            process = subprocess.Popen([python_executable, script_path])
            process.wait()  # Wait for the process to finish
            
            # If we get here, the process has exited
            print("⚠️ Bot crashed or stopped. Restarting in 5 seconds...")
            time.sleep(5)
            print("🔄 Restarting bot...")
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            break
        except Exception as e:
            print(f"❌ Critical error in launcher: {e}")
            break

if __name__ == "__main__":
    run_bot()
