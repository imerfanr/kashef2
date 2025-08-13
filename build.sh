#!/bin/bash

# Simple build script for Miner Detector Desktop
# راه اندازی و ایجاد فایل اجرایی نسخه دسکتاپ

echo "==================================="
echo "Miner Detector Desktop Builder"
echo "سازنده نسخه دسکتاپ شناساگر ماینر"
echo "==================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    echo "خطا: پایتون ۳ نصب نیست"
    exit 1
fi

# Run the desktop builder
echo "Starting build process..."
echo "شروع فرآیند ساخت..."

python3 build_desktop.py

echo "Build process completed!"
echo "فرآیند ساخت تکمیل شد!"
echo ""
echo "To install the application, run:"
echo "برای نصب برنامه، اجرا کنید:"
echo "  ./install_desktop.sh"
echo ""
echo "Or on Windows:"
echo "یا در ویندوز:"
echo "  install_desktop.bat"