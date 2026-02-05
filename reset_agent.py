"""
Reset tool for Autonomous Agent.
Clears all learning, memory, logs, and state to start fresh.
Does NOT affect .env configuration.
"""
import sys
import shutil
import argparse
from pathlib import Path
from config import Config

def reset_agent(force: bool = False):
    """
    Reset the agent's state by clearing data directories.
    
    Args:
        force: If True, skip confirmation prompt.
    """
    print("\n⚠️  WARNING: AGENT RESET ⚠️")
    print("This will PERMANENTLY DELETE all:")
    print(" - Learned memories and embeddings")
    print(" - Execution logs and audit trails")
    print(" - Saved plans and state")
    print(" - Session summaries")
    print("\nThis action cannot be undone.")
    print(f"Target directory: {Config.DATA_DIR}\n")
    
    if not force:
        response = input("Are you sure you want to proceed? (y/N): ").lower().strip()
        if response != 'y':
            print("Reset cancelled.")
            return

    print("\nResetting agent state...")
    
    # List of directories to clean
    dirs_to_clean = [
        Config.LOGS_DIR,
        Config.STATE_DIR,
        Config.PLANS_DIR,
        Config.MEMORY_DIR,
        Config.VECTOR_DB_DIR,
        Config.SUMMARIES_DIR,
    ]
    
    success = True
    for directory in dirs_to_clean:
        if directory.exists():
            try:
                # Remove all contents but keep directory
                for item in directory.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                print(f"✓ Cleared {directory.relative_to(Config.BASE_DIR)}")
            except Exception as e:
                print(f"✗ Failed to clear {directory}: {e}")
                success = False
        else:
            print(f"○ Skipped {directory.relative_to(Config.BASE_DIR)} (not found)")
            
    # Re-create empty directories to be safe
    try:
        Config.ensure_directories()
        print("✓ Re-initialized directory structure")
    except Exception as e:
        print(f"✗ Failed to re-init directories: {e}")
        success = False

    if success:
        print("\n✨ Agent reset successfully! You can now start a fresh session.")
    else:
        print("\n⚠️  Reset finished with errors.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset Autonomous Agent state.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    reset_agent(force=args.force)
