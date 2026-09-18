import os
import subprocess
import getpass
import sys

def publish_to_pypi():
    print("--- PyPI Publishing Wizard for ContextFlow ---")
    print("The production assets (sdist and wheel) are already built and validated in the dist/ folder.")
    print("To publish to PyPI, you must provide your PyPI API Token.")
    
    token = getpass.getpass(prompt="Enter your PyPI API Token (starts with pypi-): ")
    
    if not token.startswith("pypi-"):
        print("[ERROR] Invalid token format. PyPI tokens must start with 'pypi-'.")
        sys.exit(1)
        
    print("\nUploading to PyPI...")
    
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token
    
    try:
        # Use twine to upload all files in the dist directory
        result = subprocess.run(
            ["twine", "upload", "dist/*"],
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        print("[SUCCESS] ContextFlow has been mapped and uploaded to PyPI!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[ERROR] PyPI upload failed.")
        print(e.stderr)
        sys.exit(1)

if __name__ == '__main__':
    publish_to_pypi()
