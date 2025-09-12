# GameForge AI Dependency Installer
import subprocess
import sys
import time

def install_package_group(group_name, packages):
    """Install a group of packages with error handling"""
    print(f"\nInstalling {group_name}...")
    print("=" * 40)

    for package in packages:
        try:
            print(f"Installing {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"SUCCESS: {package} installed successfully")
            else:
                print(f"ERROR: Failed to install {package}: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: Installing {package}")
        except Exception as e:
            print(f"EXCEPTION: Error installing {package}: {e}")

        time.sleep(1)  # Brief pause between installations

# Installation groups
groups = {
    "Core Dependencies": [
        "pip>=23.0.0", "setuptools>=65.0.0", "wheel>=0.38.0"
    ],
    "Web Framework": [
        "fastapi>=0.104.1", "uvicorn[standard]>=0.24.0", 
        "pydantic>=2.5.0", "python-multipart>=0.0.6"
    ],
    "AI/ML Pipeline": [
        "torch>=2.1.0", "torchvision>=0.16.0", "diffusers>=0.24.0",
        "transformers>=4.36.0", "pillow>=10.1.0", "numpy>=1.24.0"
    ],
    "Database & Storage": [
        "psycopg2-binary>=2.9.7", "asyncpg>=0.29.0", 
        "redis>=5.0.1", "sqlalchemy>=2.0.23"
    ],
    "Authentication": [
        "python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4",
        "bcrypt>=4.0.1", "cryptography>=41.0.7"
    ],
    "Utilities": [
        "python-dotenv>=1.0.0", "click>=8.1.7", "rich>=13.7.0",
        "requests>=2.31.0", "httpx>=0.25.0"
    ]
}

if __name__ == "__main__":
    print("GameForge AI Dependency Installation")
    print("=" * 50)

    for group_name, packages in groups.items():
        install_package_group(group_name, packages)

    print("\nInstallation process complete!")
