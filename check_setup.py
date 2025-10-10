#!/usr/bin/env python3
"""
Setup Validation Script - Check if all dependencies are installed
"""

import sys
import subprocess


def check_package(package_name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def main():
    print("🔍 Checking Dating Wizard Setup\n")
    print("="*60)

    # Core dependencies
    packages = [
        ("opencv-python", "cv2"),
        ("Pillow", "PIL"),
        ("pytesseract", "pytesseract"),
        ("numpy", "numpy"),
        ("torch", "torch"),
        ("torchvision", "torchvision"),
        ("scikit-learn", "sklearn"),
        ("selenium", "selenium"),
        ("webdriver-manager", "webdriver_manager"),
        ("beautifulsoup4", "bs4"),
        ("requests", "requests"),
        ("loguru", "loguru"),
        ("python-dotenv", "dotenv"),
    ]

    missing = []
    installed = []

    print("📦 Python Packages:\n")
    for package, import_name in packages:
        if check_package(package, import_name):
            print(f"  ✅ {package}")
            installed.append(package)
        else:
            print(f"  ❌ {package}")
            missing.append(package)

    # Check Tesseract binary
    print("\n🔧 System Tools:\n")
    try:
        result = subprocess.run(['tesseract', '--version'],
                              capture_output=True, check=True, text=True)
        print(f"  ✅ Tesseract OCR")
        tesseract_version = result.stdout.split('\n')[0]
        print(f"     {tesseract_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  ❌ Tesseract OCR")
        print(f"     Install: brew install tesseract  # macOS")

    # Check conda environment
    print("\n🐍 Python Environment:\n")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Path: {sys.executable}")

    # Conda check
    try:
        result = subprocess.run(['conda', 'info', '--envs'],
                              capture_output=True, text=True)
        if 'wizard' in result.stdout:
            print(f"  ✅ Conda env 'wizard' exists")
        else:
            print(f"  ℹ️  No conda env named 'wizard'")
    except FileNotFoundError:
        print(f"  ℹ️  Conda not installed")

    # Summary
    print("\n" + "="*60)
    print("📊 Summary:\n")
    print(f"  Installed: {len(installed)}/{len(packages)} packages")
    print(f"  Missing: {len(missing)} packages")

    if missing:
        print(f"\n⚠️  Missing packages detected!")
        print(f"\nTo install missing packages, run:")
        print(f"\n  python3 -m pip install {' '.join(missing)}")

        # Or using conda
        print(f"\nOr with conda:")
        print(f"  conda activate wizard")
        print(f"  python -m pip install {' '.join(missing)}")

        return 1
    else:
        print(f"\n✅ All dependencies installed!")
        print(f"\nℹ️  Note: Some packages may need to be installed in your conda env")
        print(f"   Run: conda activate wizard")
        print(f"   Then: python -m pip install -r requirements.txt")

    print("\n" + "="*60)
    print("\n🚀 Next Steps:")
    print("  1. python quick_start.py           - Interactive setup")
    print("  2. python preference_cli.py        - Configure preferences")
    print("  3. python demo_classifier.py       - Test classifier")
    print("\n📚 Full documentation: PROTOTYPE_GUIDE.md")
    print("="*60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
