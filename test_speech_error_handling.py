#!/usr/bin/env python3
"""
Test script for speech-to-text error handling
Verifies that proper error messages are shown when ffmpeg is not available
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.speech_to_text import (
    check_ffmpeg_available,
    get_ffmpeg_install_instructions,
    SpeechToTextService,
    FFmpegNotFoundError
)

def test_ffmpeg_check():
    """Test ffmpeg availability checking"""
    print("=" * 70)
    print("Testing FFmpeg availability check...")
    print("=" * 70)
    
    available = check_ffmpeg_available()
    print(f"\nFFmpeg available: {available}")
    
    if available:
        print("✓ FFmpeg is installed and available")
    else:
        print("✗ FFmpeg is NOT available")
        print("\nInstallation instructions would be shown:")
        print(get_ffmpeg_install_instructions())
    
    return available

def test_service_initialization():
    """Test SpeechToTextService initialization"""
    print("\n" + "=" * 70)
    print("Testing SpeechToTextService initialization...")
    print("=" * 70)
    
    try:
        service = SpeechToTextService(model_size="base")
        print("✓ Service initialized successfully")
        print(f"  Model size: {service.model_size}")
        print(f"  Model loaded: {service.model is not None}")
        return True
    except FFmpegNotFoundError as e:
        print("✗ Service initialization failed: FFmpeg not found")
        print(f"\nError message:\n{str(e)}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {str(e)}")
        return False

def test_error_message_quality():
    """Test that error messages are informative"""
    print("\n" + "=" * 70)
    print("Testing error message quality...")
    print("=" * 70)
    
    instructions = get_ffmpeg_install_instructions()
    
    # Check that instructions contain key information
    checks = [
        ("Windows instructions", "Windows" in instructions),
        ("macOS instructions", "macOS" in instructions),
        ("Linux instructions", "Linux" in instructions),
        ("Chocolatey", "choco install ffmpeg" in instructions),
        ("Homebrew", "brew install ffmpeg" in instructions),
        ("apt", "apt install ffmpeg" in instructions),
        ("Verification command", "ffmpeg -version" in instructions),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}: {'present' if passed else 'missing'}")
        if not passed:
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("SPEECH-TO-TEXT ERROR HANDLING TEST")
    print("=" * 70)
    
    results = []
    
    # Test 1: FFmpeg check
    results.append(("FFmpeg check", test_ffmpeg_check()))
    
    # Test 2: Service initialization
    results.append(("Service initialization", test_service_initialization()))
    
    # Test 3: Error message quality
    results.append(("Error messages", test_error_message_quality()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
