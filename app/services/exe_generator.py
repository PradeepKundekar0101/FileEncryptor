import subprocess
import os
import shutil

def generate_exe(key: bytes, zip_path: str, username: str):
    decryptor_script = f"""
        todo :)
    """
    
    with open("decryptor.py", "w") as f:
        f.write(decryptor_script)
    
    subprocess.run(["pyinstaller", "--onefile", "decryptor.py"])
    
    os.remove("decryptor.py")
    shutil.rmtree("build")
    os.remove("decryptor.spec")
    
    return "dist/decryptor.exe"