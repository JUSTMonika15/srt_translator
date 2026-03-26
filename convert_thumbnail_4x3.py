# -*- coding: utf-8 -*-
"""
YouTube Thumbnail to 4:3 Converter
Expands canvas to 4:3 ratio while keeping original image unchanged
"""

import sys
import os
from PIL import Image, ImageFilter

def expand_to_43(input_file):
    """
    Expand image canvas to 4:3 ratio by adding padding
    
    Args:
        input_file: Path to input image (typically 1280x720 YouTube thumbnail)
    
    Returns:
        List of created file paths
    """
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        return []
    
    try:
        img = Image.open(input_file)
        orig_width, orig_height = img.size
        print(f"\n{'='*60}")
        print(f"Original image: {orig_width}x{orig_height}")
        print(f"{'='*60}")
        
        # Calculate 4:3 canvas size (keep width, expand height)
        canvas_width = orig_width
        canvas_height = int(orig_width * 3 / 4)
        
        # Calculate vertical padding
        pad_top = (canvas_height - orig_height) // 2
        pad_bottom = canvas_height - orig_height - pad_top
        
        print(f"New canvas: {canvas_width}x{canvas_height} (4:3 ratio)")
        print(f"Padding: top={pad_top}px, bottom={pad_bottom}px")
        print(f"Original image will be centered (unchanged)")
        print(f"{'='*60}\n")
        
        created_files = []
        
        # Method 1: Black borders
        print("Creating version with black borders...")
        output_black = input_file.replace('.jpg', '_4x3.jpg')
        canvas_black = Image.new('RGB', (canvas_width, canvas_height), (0, 0, 0))
        canvas_black.paste(img, (0, pad_top))
        canvas_black.save(output_black, quality=95)
        print(f"✓ Created: {os.path.basename(output_black)}")
        created_files.append(output_black)
        
        # Method 2: Blurred background (optional)
        print("\n" + "="*60)
        print("Blurred background creates a more aesthetic look")
        print("(The original image remains sharp and centered)")
        print("="*60)
        
        choice = input("\nCreate blurred version? (y/n, default: n): ").strip().lower()
        
        if choice == 'y':
            print("\nCreating version with blurred background...")
            output_blur = input_file.replace('.jpg', '_4x3_blur.jpg')
            
            # Create blurred background by stretching original
            bg = img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
            
            # Paste original sharp image centered
            bg.paste(img, (0, pad_top))
            bg.save(output_blur, quality=95)
            print(f"✓ Created: {os.path.basename(output_blur)}")
            created_files.append(output_blur)
        
        print(f"\n{'='*60}")
        print(f"Conversion complete! Created {len(created_files)} file(s)")
        print(f"{'='*60}")
        
        return created_files
        
    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Main entry point"""
    
    # 如果没有提供参数，自动查找当前目录最新的 jpg 文件
    if len(sys.argv) < 2:
        print("\n" + "="*60)
        print("No filename provided, searching for latest jpg...")
        print("="*60)
        
        import glob
        import time
        
        jpg_files = glob.glob("*.jpg")
        if not jpg_files:
            print("Error: No jpg files found in current directory")
            sys.exit(1)
        
        # 按修改时间排序，取最新的
        jpg_files.sort(key=os.path.getmtime, reverse=True)
        input_file = jpg_files[0]
        print(f"Found latest file: {input_file}\n")
    else:
        input_file = sys.argv[1]
        # Handle quoted paths
        input_file = input_file.strip('"')
    
    print("\n" + "="*60)
    print("YouTube Thumbnail to 4:3 Converter")
    print("="*60)
    print(f"Input: {input_file}")
    
    created = expand_to_43(input_file)
    
    if created:
        print("\nOutput files:")
        for f in created:
            print(f"  - {os.path.basename(f)}")
    else:
        print("\nNo files were created.")
        sys.exit(1)

if __name__ == '__main__':
    main()