#!/usr/bin/env python3
"""Capture screenshots of HTML dashboard files."""
import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def main():
    try:
        import mss
        import mss.tools
        from PIL import Image
    except ImportError:
        print("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "mss", "Pillow", "-q"])
        import mss
        import mss.tools
        from PIL import Image

    # Paths
    base = Path(__file__).parent.parent
    screenshots_dir = base / "docs" / "screenshots"
    
    html_files = [
        ("canvas-preview.html", "canvas-preview.png", 1200, 675),
        ("threads-preview.html", "threads-preview.png", 1200, 675),
        ("user-inputs-preview.html", "user-inputs-preview.png", 1200, 675),
    ]
    
    # Start HTTP server
    print(f"Starting HTTP server on port 8777...")
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8777"],
        cwd=str(screenshots_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    
    print("Server started!")
    print("=" * 50)
    
    for html_file, png_file, w, h in html_files:
        url = f"http://localhost:8777/{html_file}"
        print(f"\nCapturing: {html_file}")
        print(f"URL: {url}")
        
        # Open in browser
        webbrowser.open(url)
        time.sleep(3)  # Wait for page to load
        
        print("Taking screenshot in 2 seconds...")
        time.sleep(2)
        
        # Take screenshot of entire screen
        with mss.mss() as sct:
            # Capture the monitor
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Crop to window size (approximate center of screen)
            # You may need to adjust these coordinates
            screen_w, screen_h = img.size
            left = (screen_w - w) // 2
            top = (screen_h - h) // 2
            right = left + w
            bottom = top + h
            
            cropped = img.crop((left, top, right, bottom))
            
            # Save
            output_path = screenshots_dir / png_file
            cropped.save(output_path, "PNG")
            print(f"Saved: {output_path}")
    
    # Stop server
    server.terminate()
    print("\n" + "=" * 50)
    print("All screenshots captured!")
    print(f"Files saved in: {screenshots_dir}")

if __name__ == "__main__":
    main()
