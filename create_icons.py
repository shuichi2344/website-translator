#!/usr/bin/env python3
"""
Create simple icon files for the browser extension
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create icons directory
    import os
    os.makedirs('browser-extension/icons', exist_ok=True)
    
    # Define sizes
    sizes = [16, 48, 128]
    
    for size in sizes:
        # Create image with gradient-like purple background
        img = Image.new('RGB', (size, size), color='#667eea')
        draw = ImageDraw.Draw(img)
        
        # Add a simple document icon shape
        margin = size // 8
        draw.rectangle(
            [margin, margin, size - margin, size - margin],
            fill='white',
            outline='#764ba2',
            width=max(1, size // 32)
        )
        
        # Add lines to represent text
        if size >= 48:
            line_margin = size // 4
            line_spacing = size // 8
            for i in range(3):
                y = line_margin + (i * line_spacing)
                draw.line(
                    [line_margin, y, size - line_margin, y],
                    fill='#667eea',
                    width=max(1, size // 32)
                )
        
        # Save
        img.save(f'browser-extension/icons/icon{size}.png')
        print(f'✓ Created icon{size}.png')
    
    print('\n✅ All icons created successfully!')
    
except ImportError:
    print('⚠️  Pillow not installed. Creating placeholder icons...')
    print('Run: pip install Pillow')
    print('\nAlternatively, use any 16x16, 48x48, and 128x128 PNG images')
    print('and save them as icon16.png, icon48.png, icon128.png')
