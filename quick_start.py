#!/usr/bin/env python3
"""
Quick Start - Interactive wizard for first-time setup
"""

import sys
import os
from pathlib import Path


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        🧙‍♂️  DATING WIZARD - QUICK START  🧙‍♂️              ║
║                                                          ║
║        AI-Powered Dating Profile Classifier              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n📦 Checking dependencies...")

    missing = []

    try:
        import cv2
        print("  ✅ OpenCV")
    except ImportError:
        missing.append("opencv-python")
        print("  ❌ OpenCV")

    try:
        import PIL
        print("  ✅ Pillow")
    except ImportError:
        missing.append("Pillow")
        print("  ❌ Pillow")

    try:
        import pytesseract
        print("  ✅ Pytesseract")
    except ImportError:
        missing.append("pytesseract")
        print("  ❌ Pytesseract")

    try:
        import torch
        print("  ✅ PyTorch")
    except ImportError:
        missing.append("torch torchvision")
        print("  ❌ PyTorch")

    try:
        import selenium
        print("  ✅ Selenium")
    except ImportError:
        missing.append("selenium")
        print("  ❌ Selenium")

    # Check Tesseract binary
    import subprocess
    try:
        subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
        print("  ✅ Tesseract OCR")
    except:
        print("  ❌ Tesseract OCR (binary not found)")
        print("     Install: brew install tesseract  # macOS")

    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  python -m pip install {' '.join(missing)}")
        return False

    print("\n✅ All dependencies installed!\n")
    return True


def setup_directories():
    """Create necessary directories"""
    print("📁 Setting up directories...")

    dirs = [
        "config/liked_profiles",
        "config/disliked_profiles",
        "config/reference_images",
        "data/screenshots",
        "data/test_profiles/matches",
        "data/test_profiles/non_matches",
        "data/instagram_screenshots",
        "data/instagram_results",
        "data/classification_results",
        "logs"
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {dir_path}")

    print("\n✅ Directories created!\n")


def check_preferences():
    """Check if preferences are configured"""
    prefs_path = Path("config/preferences.json")

    if not prefs_path.exists():
        print("⚠️  No preferences found")
        return False

    import json
    with open(prefs_path, 'r') as f:
        prefs = json.load(f)

    # Check if reference images exist
    ref_images = prefs.get('partner_preferences', {}).get('physical', {}).get('reference_images', [])

    print("📊 Current Preferences:")
    print(f"  Reference images: {len(ref_images)}")

    weights = prefs.get('partner_preferences', {})
    if weights:
        phys = weights.get('physical', {}).get('importance_weight', 0.6)
        pers = weights.get('personality', {}).get('importance_weight', 0.3)
        inte = weights.get('interests', {}).get('importance_weight', 0.1)

        print(f"  Weights: Physical {phys:.0%}, Personality {pers:.0%}, Interests {inte:.0%}")

    min_score = prefs.get('matching_criteria', {}).get('minimum_score', 0.6)
    print(f"  Min match score: {min_score:.0%}")

    age_range = prefs.get('age_range', {})
    print(f"  Age range: {age_range.get('min', 18)}-{age_range.get('max', 99)}")

    return len(ref_images) > 0


def interactive_menu():
    """Show interactive menu"""
    while True:
        print("\n╔══════════════════════════════════════════════════════════╗")
        print("║  What would you like to do?                              ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print("\n  1. 🎯 Set up preferences (first time)")
        print("  2. 📸 Add reference images")
        print("  3. 🧪 Test classifier on a screenshot")
        print("  4. 📊 Evaluate classifier accuracy")
        print("  5. 🔍 Run Instagram pipeline")
        print("  6. 📚 View documentation")
        print("  7. ℹ️  Show classifier info")
        print("  8. 🚪 Exit")

        choice = input("\n👉 Enter choice (1-8): ").strip()

        if choice == '1':
            print("\n🎯 Starting preference setup...\n")
            os.system("python preference_cli.py")

        elif choice == '2':
            print("\n📸 Add reference images")
            print("Place images in config/reference_images/ or use the preference CLI")
            input("Press Enter when ready...")

        elif choice == '3':
            screenshot = input("\n📸 Enter path to screenshot: ").strip()
            if os.path.exists(screenshot):
                os.system(f'python demo_classifier.py --mode single --screenshot "{screenshot}"')
            else:
                print(f"❌ File not found: {screenshot}")

        elif choice == '4':
            print("\n📊 Evaluation requires labeled test data")
            print("Place screenshots in:")
            print("  - data/test_profiles/matches/")
            print("  - data/test_profiles/non_matches/")
            print()
            proceed = input("Proceed with evaluation? (y/n): ").lower()
            if proceed == 'y':
                os.system("python evaluate_classifier.py --error-analysis")

        elif choice == '5':
            query = input("\n🔍 Enter Instagram search query: ").strip()
            if query:
                limit = input("Max profiles to analyze (default 20): ").strip() or "20"
                os.system(f'python instagram_classifier_pipeline.py --query "{query}" --limit {limit}')

        elif choice == '6':
            print("\n📚 Opening documentation...")
            if Path("PROTOTYPE_GUIDE.md").exists():
                os.system("cat PROTOTYPE_GUIDE.md | less")
            else:
                print("❌ PROTOTYPE_GUIDE.md not found")

        elif choice == '7':
            os.system("python demo_classifier.py --mode info")

        elif choice == '8':
            print("\n👋 Goodbye!\n")
            break

        else:
            print("\n❌ Invalid choice. Please enter 1-8.")


def main():
    print_banner()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return 1

    # Setup directories
    setup_directories()

    # Check preferences
    has_prefs = check_preferences()

    if not has_prefs:
        print("\n⚠️  You haven't set up your preferences yet!")
        print("This is required for the classifier to work.")
        print()
        setup = input("Set up preferences now? (y/n): ").lower()

        if setup == 'y':
            os.system("python preference_cli.py")
        else:
            print("\n💡 Run 'python preference_cli.py' when ready")

    # Show interactive menu
    interactive_menu()

    return 0


if __name__ == "__main__":
    sys.exit(main())
