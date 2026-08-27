#!/usr/bin/env python3
"""Render HTML dashboard previews as high-quality PNG screenshots using Chrome."""
from html2image import Html2Image
from pathlib import Path
import sys

def main():
    base = Path(__file__).parent.parent
    screenshots_dir = base / "docs" / "screenshots"
    
    # HTML files to render
    html_files = [
        ("canvas-preview.html", "canvas-preview.png", (1200, 675)),
        ("threads-preview.html", "threads-preview.png", (1200, 675)),
        ("user-inputs-preview.html", "user-inputs-preview.png", (1200, 675)),
    ]
    
    # Try to find Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\Vannon\AppData\Local\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    
    chrome_path = None
    for p in chrome_paths:
        if Path(p).exists():
            chrome_path = p
            break
    
    if not chrome_path:
        print("Chrome/Edge not found. Using default html2image path.")
    
    # Create Html2Image instance
    kwargs = {
        "custom_flags": [
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
        ],
        "size": (1200, 675),
    }
    
    if chrome_path:
        kwargs["browser_executable"] = chrome_path
    
    hti = Html2Image(output_path=str(screenshots_dir), **kwargs)
    
    for html_file, png_file, size in html_files:
        html_path = screenshots_dir / html_file
        print(f"Rendering: {html_file} -> {png_file}")
        
        # Read HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Render with custom size
        hti.size = size
        hti.screenshot(html_str=html_content, save_as=png_file)
        
        output = screenshots_dir / png_file
        if output.exists():
            size_kb = output.stat().st_size / 1024
            print(f"  Saved: {output} ({size_kb:.1f} KB)")
        else:
            print(f"  FAILED: {output} not created")
    
    print("\nDone!")

if __name__ == "__main__":
    main()
