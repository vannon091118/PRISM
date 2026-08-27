#!/usr/bin/env python3
"""Take screenshots of HTML files using Windows API."""
import ctypes
import ctypes.wintypes
import time
import sys
import os
import subprocess
from pathlib import Path

def take_screenshot(hwnd, output_path):
    """Capture a window and save as PNG."""
    try:
        from PIL import Image
    except ImportError:
        print("Installing Pillow...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "-q"])
        from PIL import Image
    
    # Get window rect
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    
    if width <= 0 or height <= 0:
        print(f"Invalid window size: {width}x{height}")
        return False
    
    # Create device context
    hdc = ctypes.windll.user32.GetDC(hwnd)
    hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc)
    hbitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc, width, height)
    ctypes.windll.gdi32.SelectObject(hdc_mem, hbitmap)
    
    # Copy
    ctypes.windll.user32.PrintWindow(hwnd, hdc_mem, 3)  # PW_RENDERFULLCONTENT
    
    # Convert to PIL
    bmp_info = ctypes.wintypes.BITMAPINFOHEADER()
    bmp_info.biSize = ctypes.sizeof(ctypes.wintypes.BITMAPINFOHEADER)
    bmp_info.biWidth = width
    bmp_info.biHeight = -height  # Top-down
    bmp_info.biPlanes = 1
    bmp_info.biBitCount = 32
    bmp_info.biCompression = 0
    
    buffer = ctypes.create_string_buffer(width * height * 4)
    ctypes.windll.gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, buffer, ctypes.byref(bmp_info), 0)
    
    img = Image.frombuffer('RGBA', (width, height), buffer, 'raw', 'BGRA', 0, 1)
    img = img.convert('RGB')
    img.save(output_path, 'PNG')
    
    # Cleanup
    ctypes.windll.gdi32.DeleteObject(hbitmap)
    ctypes.windll.gdi32.DeleteDC(hdc_mem)
    ctypes.windll.user32.ReleaseDC(hwnd, hdc)
    
    print(f"Saved: {output_path} ({width}x{height})")
    return True

def find_browser_window(title_contains):
    """Find a browser window by title."""
    import re
    
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    
    result = []
    
    def callback(hwnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                if title_contains.lower() in buff.value.lower():
                    result.append((hwnd, buff.value))
        return True
    
    EnumWindows(EnumWindowsProc(callback), 0)
    return result

if __name__ == "__main__":
    # HTML files to screenshot
    screenshots = [
        ("docs/screenshots/canvas-preview.html", "docs/screenshots/canvas-preview.png"),
        ("docs/screenshots/threads-preview.html", "docs/screenshots/threads-preview.png"),
        ("docs/screenshots/user-inputs-preview.html", "docs/screenshots/user-inputs-preview.png"),
    ]
    
    # Start HTTP server
    server_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots")
    print(f"Starting server in {server_dir}...")
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8765"],
        cwd=server_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    
    print("Server started on http://localhost:8765")
    print("Please open each URL in your browser and press Enter after each screenshot:")
    
    for html_file, png_file in screenshots:
        url = f"http://localhost:8765/{os.path.basename(html_file)}"
        print(f"\n1. Open: {url}")
        print(f"2. Wait for page to load")
        print(f"3. Press Enter to capture...")
        input()
        
        # Find Edge/Chrome window
        windows = find_browser_window("localhost:8765")
        if not windows:
            windows = find_browser_window("127.0.0.1:8765")
        
        if windows:
            hwnd = windows[0][0]
            output = os.path.join(os.path.dirname(__file__), "..", png_file)
            take_screenshot(hwnd, output)
        else:
            print("Could not find browser window. Please take screenshot manually.")
    
    # Stop server
    server.terminate()
    print("\nDone!")
