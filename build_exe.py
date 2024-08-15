import sys
from cx_Freeze import setup, Executable

def generate_exe_config(script_path, username):
    exe_name = f"decryptor_{username}.exe" if sys.platform == "win32" else f"decryptor_{username}"
    
    exe = Executable(
        script_path,
        base="Win32GUI" if sys.platform == "win32" else None,
        target_name=exe_name
    )
    
    build_exe_options = {
        "packages": ["os", "cryptography", "requests", "geocoder"],
        "excludes": [],
        "include_files": [],
    }
    
    return exe, build_exe_options, exe_name

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python build_exe.py <script_path> <username>")
        sys.exit(1)

    script_path = sys.argv[1]
    username = sys.argv[2]
    
    exe, build_exe_options, exe_name = generate_exe_config(script_path, username)
    
    setup(
        name=f"decryptor_{username}",
        version="0.1",
        description="File Decryptor",
        options={"build_exe": build_exe_options},
        executables=[exe]
    )