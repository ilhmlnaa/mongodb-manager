import os
import subprocess

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def run_command(command: str, logger=None) -> bool:
    """
    Run a shell command and return True if successful, False otherwise.
    If logger is provided, it will be called with (line_str) for each output line.
    """
    try:
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            # Safely strip \n and send to logger or print
            clean_line = line.rstrip('\n')
            if logger:
                logger(clean_line)
            else:
                print(clean_line)

        process.wait()
        
        if process.returncode != 0:
            if logger:
                logger(f"❌ Failed to run command with exit code {process.returncode}")
            return False
            
        return True
    except Exception as e:
        if logger:
            logger(f"❌ Failed to run: {command}\n   Error: {e}")
        else:
            print(f"\n❌ Failed to run: {command}")
            print(f"   Error: {e}")
        return False
