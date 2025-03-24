import os
import platform
import subprocess
import sys
from pathlib import Path

def check_rust_installed():
    try:
        subprocess.run(["rustc", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_cargo_installed():
    try:
        subprocess.run(["cargo", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_rust():
    print("Rust is not installed. Installing Rust...")
    if platform.system() == "Windows":
        print("Please install Rust manually from https://rustup.rs/")
        print("After installation, run this script again.")
        sys.exit(1)
    else:
        try:
            subprocess.run(
                ["curl", "--proto", "=https", "--tlsv1.2", "-sSf", "https://sh.rustup.rs", "-o", "rustup-init.sh"],
                check=True
            )
            subprocess.run(["sh", "rustup-init.sh", "-y"], check=True)
            os.remove("rustup-init.sh")
            os.environ["PATH"] = f"{os.environ['HOME']}/.cargo/bin:{os.environ['PATH']}"
            print("Rust installed successfully.")
            return True
        except subprocess.CalledProcessError:
            print("Failed to install Rust. Please install it manually from https://rustup.rs/")
            sys.exit(1)

def build_rust_extension():
    print("Building Rust extension...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            check=True
        )
        print("Rust extension built successfully.")
        return True
    except subprocess.CalledProcessError:
        print("Failed to build Rust extension.")
        return False

def install_python_dependencies():
    print("Installing Python dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            check=True
        )
        print("Python dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install Python dependencies.")
        return False

def main():
    print("Starting Git Metrics build...")

    if not check_rust_installed() or not check_cargo_installed():
        install_rust()

    install_python_dependencies()

    build_rust_extension()

    print("Build completed successfully.")

if __name__ == "__main__":
    main()
