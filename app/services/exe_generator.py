import subprocess
import os
import shutil
import logging
import base64
from fastapi import HTTPException

logging.basicConfig(level=logging.DEBUG)

def generate_exe(key: bytes, encrypted_file_paths: list, file_extensions: dict, username: str, group_name: str):
    encoded_key = base64.b64encode(key).decode('utf-8')
    extensions_str = str(file_extensions)

    script_dir = 'temp'
    if not os.path.exists(script_dir):
        os.makedirs(script_dir)
    script_path = os.path.join(script_dir, "decryptor.py")
    
    # ... (keep the existing decryptor_script content)
    decryptor_script=""""""
    with open(script_path, "w") as f:
        f.write(decryptor_script)
    
    try:
        logging.debug("Attempting to create executables with PyInstaller")
        
        executables = []

        # Compile for Linux
        linux_exe_name = f"decryptor_{username}"
        linux_command = [
            "pyinstaller",
            "--onefile",
            "--name", linux_exe_name,
            "--add-data", f"{script_path}:.",
            "--hidden-import=cryptography",
            "--hidden-import=requests",
            "--hidden-import=geocoder",
            script_path
        ]
        
        # Compile for Windows using Wine
        windows_exe_name = f"decryptor_{username}.exe"
        windows_command = [
            "wine", "pyinstaller",
            "--onefile",
            "--name", windows_exe_name,
            "--add-data", f"{script_path};.",
            "--hidden-import=cryptography",
            "--hidden-import=requests",
            "--hidden-import=geocoder",
            script_path
        ]

        for cmd, exe_name in [(linux_command, linux_exe_name), (windows_command, windows_exe_name)]:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logging.error(f"PyInstaller stdout for {exe_name}: {stdout}")
                logging.error(f"PyInstaller stderr for {exe_name}: {stderr}")
                raise subprocess.CalledProcessError(process.returncode, cmd)

            exe_path = os.path.join("dist", exe_name)
            
            if not os.path.exists(exe_path):
                raise FileNotFoundError(f"Executable not found at expected path: {exe_path}")
            
            if not os.access(exe_path, os.X_OK):
                raise PermissionError(f"Generated file is not executable: {exe_path}")
            
            file_size = os.path.getsize(exe_path)
            if file_size < 1000000:  # Assuming a valid exe should be at least 1MB
                raise ValueError(f"Generated executable seems too small: {file_size} bytes")
            
            logging.debug(f"Executable created successfully at {exe_path}")
            executables.append(exe_path)

        return executables

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running pyinstaller: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create executable: {str(e)}")
    except (FileNotFoundError, PermissionError, ValueError) as e:
        logging.error(f"Error verifying executable: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create valid executable: {str(e)}")
    finally:
        # Clean up temporary files
        try:
            os.remove(script_path)
            if os.path.exists("build"):
                shutil.rmtree("build")
            for spec_file in [f"{linux_exe_name}.spec", f"{windows_exe_name}.spec"]:
                if os.path.exists(spec_file):
                    os.remove(spec_file)
        except Exception as cleanup_error:
            logging.error(f"Cleanup error: {str(cleanup_error)}")