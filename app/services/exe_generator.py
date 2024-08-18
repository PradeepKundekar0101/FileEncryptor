import os
import logging
import base64
from fastapi import HTTPException
import zipfile
import subprocess

logging.basicConfig(level=logging.DEBUG)

def generate_exe(key: bytes, encrypted_file_paths: list, file_extensions: dict, username: str, group_name: str):
    encoded_key = base64.b64encode(key).decode('utf-8')
    if len(encoded_key) % 4 != 0:
        encoded_key += '=' * (4 - len(encoded_key) % 4)

    extensions_str = str(file_extensions)

    script_dir = 'temp'
    if not os.path.exists(script_dir):
        os.makedirs(script_dir)
    script_path = os.path.join(script_dir, "decryptor.py")
    
    decryptor_script = f"""
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
from datetime import datetime
import signal
import threading
import time
from contextlib import ExitStack
import subprocess
import atexit
import win32gui
import win32con
import win32api
import ctypes
import json

logging.basicConfig(level=logging.DEBUG, filename='decryptor_log.txt', filemode='w')

key = base64.b64decode("{encoded_key}")
fernet = Fernet(key)

# Convert the string representation back to a dictionary
file_extensions = {extensions_str}

decrypted_files = []

def is_connected():
    try:
        requests.get("http://www.google.com", timeout=3)
        return True
    except requests.ConnectionError:
        return False


def periodic_location_sender():
    while True:
        send_group_info()
        time.sleep(3600) 

def block_screenshots():
    try:
        # Create an invisible overlay window
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = lambda hwnd, msg, wparam, lparam: None
        wc.lpszClassName = "ScreenCaptureBlocker"
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        
        # Create the window
        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW,
            class_atom,
            "Screen Capture Blocker",
            0,
            0, 0,
            win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN),
            None, None, wc.hInstance, None
        )
        
        # Set the window to be transparent
        win32gui.SetLayeredWindowAttributes(hwnd, 0, 1, win32con.LWA_ALPHA)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        
        logging.info("Screenshot blocking enabled on Windows")
    except Exception as e:
        logging.error(f"Failed to block screenshots on Windows: {{str(e)}}")
    

def unblock_screenshots():
    try:
        # Find and close the blocking window
        hwnd = win32gui.FindWindow("ScreenCaptureBlocker", None)
        if hwnd:
            win32gui.DestroyWindow(hwnd)
        logging.info("Screenshot blocking disabled on Windows")
    except Exception as e:
        logging.error(f"Failed to unblock screenshots on Windows: {{str(e)}}")
    

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
                'http://20.197.15.160:8000/sendLocation', 
                json=data,
                headers=headers
            )
            if response.status_code == 200:
                print("Group information sent successfully")
            else:
                print(f"Failed to send group information. Status code: {{response.status_code}}")
        except Exception as e:
            print(f"Error sending group information: {{str(e)}}")


# Global variables to track file states
original_files = []
decrypted_files = []

def decrypt_files():
    global original_files, decrypted_files
    try:
        block_screenshots()
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        logging.debug(f"Current directory: {{current_dir}}")
        
        for filename in os.listdir(current_dir):
            if filename.endswith("_encrypted"):
                try:
                    file_path = os.path.join(current_dir, filename)
                    logging.debug(f"Attempting to decrypt: {{filename}}")
                    with open(file_path, "rb") as encrypted_file:
                        encrypted_data = encrypted_file.read()
                    decrypted_data = fernet.decrypt(encrypted_data)
                    original_extension = file_extensions.get(filename.split('_encrypted')[0], "")
                    decrypted_filename = filename[:-10] + original_extension
                    decrypted_path = os.path.join(current_dir, decrypted_filename)
                    with open(decrypted_path, "wb") as decrypted_file:
                        decrypted_file.write(decrypted_data)
                    
                    original_files.append(file_path)
                    decrypted_files.append(decrypted_path)
                    
                    logging.debug(f"Successfully decrypted: {{filename}} to {{decrypted_filename}}")
                except Exception as e:
                    logging.error(f"Error decrypting {{filename}}: {{str(e)}}")
        
        # Save the file lists to a JSON file
        with open('file_states.json', 'w') as f:
            
            json.dump({{'original': original_files, 'decrypted': decrypted_files}}, f)
        logging.info("Decryption process completed.")
    except Exception as e:
        logging.error(f"Error in decrypt_files: {{str(e)}}")

def reencrypt_files():
    global original_files, decrypted_files
    try:
        unblock_screenshots()
        
        # Load the file lists from the JSON file
        try:
            with open('file_states.json', 'r') as f:
                file_states = json.load(f)
                original_files = file_states['original']
                decrypted_files = file_states['decrypted']
        except FileNotFoundError:
            logging.error("File states not found. Re-encryption may be incomplete.")
        
        for original, decrypted in zip(original_files, decrypted_files):
            try:
                if os.path.exists(decrypted):
                    logging.debug(f"Re-encrypting file: {{decrypted}}")
                    with open(decrypted, "rb") as f:
                        data = f.read()
                    encrypted_data = fernet.encrypt(data)
                    with open(original, "wb") as encrypted_file:
                        encrypted_file.write(encrypted_data)
                    os.remove(decrypted)
                    logging.debug(f"Successfully re-encrypted: {{decrypted}} to {{original}}")
                else:
                    logging.warning(f"Decrypted file not found: {{decrypted}}")
            except Exception as e:
                logging.error(f"Error re-encrypting {{decrypted}}: {{str(e)}}")
        
        # Clean up the file states JSON
        if os.path.exists('file_states.json'):
            os.remove('file_states.json')
        
        logging.info("Re-encryption process completed.")
    except Exception as e:
        logging.error(f"Error in reencrypt_files: {{str(e)}}")

def main():
    try:
        if not is_connected():
            print("Internet connection is required. No decryption or location sending will occur.")
            return

        atexit.register(reencrypt_files)

        print("Starting periodic location sender...")
        location_thread = threading.Thread(target=periodic_location_sender, daemon=True)
        location_thread.start()

        print("Sending initial group information...")
        send_group_info()

        print("Blocking screenshots...")
        block_screenshots()

        print("Decrypting files...")
        decrypt_files()

        print("Files decrypted. Press Enter to re-encrypt and exit...")
        input()
    except Exception as e:
        logging.error(f"Unhandled exception: {{str(e)}}")
        print(f"An error occurred. Please check the decryptor_log.txt file for details.")
    finally:
        print("Re-encrypting files...")
        reencrypt_files()
        print("Unblocking screenshots...")
        unblock_screenshots()

if __name__ == "__main__":
    main()
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
            "--hidden-import=ctypes",
            "--hidden-import=win32gui",
            "--hidden-import=win32con",
            "--hidden-import=win32api",
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