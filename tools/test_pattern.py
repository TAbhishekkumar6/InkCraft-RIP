#!/usr/bin/env python
"""
InkCraft RIP Test Pattern Generator

This script generates various test patterns for printer testing and calibration.
These patterns are useful for reverse engineering printer commands and 
verifying print quality.
"""

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Pattern Types
PATTERNS = {
    "grid": "Grid Pattern - Lines forming a grid",
    "colorbar": "Color Bars - Horizontal color bars (CMYK)",
    "gradient": "Gradient - Smooth transitions",
    "resolution": "Resolution - Fine line patterns",
    "text": "Text - Font rendering test",
    "alignment": "Alignment - Pattern for print alignment"
}

class TestPatternGenerator:
    """Test pattern generator for printer testing"""
    
    def __init__(self, resolution=(720, 720), size=(2048, 2048)):
        """Initialize the pattern generator"""
        self.resolution = resolution  # DPI (x, y)
        self.size = size  # Image size in pixels
        
    def create_pattern(self, pattern_type, output_file=None, options=None):
        """Create a test pattern image"""
        if pattern_type not in PATTERNS:
            print(f"Error: Unknown pattern type '{pattern_type}'")
            return None
        
        options = options or {}
        
        # Create a new image
        if pattern_type == "colorbar":
            # Color bars are always RGB
            img = Image.new('RGB', self.size, color=(255, 255, 255))
        else:
            # Other patterns can be grayscale
            color_mode = options.get('color_mode', 'L')
            img = Image.new(color_mode, self.size, color=255)
        
        # Generate the selected pattern
        pattern_method = getattr(self, f"_generate_{pattern_type}")
        pattern_method(img, options)
        
        # Save the image if output file is specified
        if output_file:
            img.save(output_file)
            print(f"Pattern saved to {output_file}")
        
        return img
    
    def _generate_grid(self, img, options):
        """Generate a grid pattern"""
        draw = ImageDraw.Draw(img)
        
        # Options
        line_width = options.get('line_width', 2)
        spacing = options.get('spacing', 100)
        color = options.get('color', 0)  # Black for grayscale
        
        # Draw horizontal lines
        for y in range(0, self.size[1], spacing):
            draw.line([(0, y), (self.size[0], y)], fill=color, width=line_width)
        
        # Draw vertical lines
        for x in range(0, self.size[0], spacing):
            draw.line([(x, 0), (x, self.size[1])], fill=color, width=line_width)
        
        # Add grid measurements
        if options.get('show_measurements', True):
            font = self._get_font(16)
            for i, x in enumerate(range(0, self.size[0], spacing)):
                if x + 50 < self.size[0]:
                    draw.text((x + 5, 5), f"{i}", fill=color, font=font)
            
            for i, y in enumerate(range(0, self.size[1], spacing)):
                if y + 20 < self.size[1]:
                    draw.text((5, y + 5), f"{i}", fill=color, font=font)
    
    def _generate_colorbar(self, img, options):
        """Generate color bars"""
        draw = ImageDraw.Draw(img)
        
        # Options
        bar_count = options.get('bar_count', 4)  # CMYK by default
        
        # Calculate bar height
        bar_height = self.size[1] // bar_count
        
        # CMYK colors (represented in RGB)
        colors = [
            (0, 255, 255),    # Cyan
            (255, 0, 255),    # Magenta
            (255, 255, 0),    # Yellow
            (0, 0, 0)         # Black
        ]
        
        # Draw color bars
        for i in range(bar_count):
            y1 = i * bar_height
            y2 = (i + 1) * bar_height
            color_idx = i % len(colors)
            draw.rectangle([0, y1, self.size[0], y2], fill=colors[color_idx])
            
            # Add color name
            font = self._get_font(36)
            color_names = ["CYAN", "MAGENTA", "YELLOW", "BLACK"]
            text_color = (255, 255, 255) if color_idx == 3 else (0, 0, 0)  # White text on black
            
            text_x = self.size[0] // 2
            text_y = y1 + (bar_height // 2) - 18
            draw.text((text_x, text_y), color_names[color_idx], fill=text_color, font=font, anchor="mm")
    
    def _generate_gradient(self, img, options):
        """Generate a gradient pattern"""
        # Options
        direction = options.get('direction', 'horizontal')
        
        # Create gradient array
        if direction == 'horizontal':
            gradient = np.linspace(0, 255, self.size[0], dtype=np.uint8)
            gradient = np.tile(gradient, (self.size[1], 1))
        else:  # vertical
            gradient = np.linspace(0, 255, self.size[1], dtype=np.uint8)
            gradient = np.tile(gradient.reshape(-1, 1), (1, self.size[0]))
        
        # Convert to image
        gradient_img = Image.fromarray(gradient)
        
        # Paste into the image
        if img.mode == 'RGB':
            # For RGB, we'll create a grayscale gradient
            img.paste(gradient_img.convert('RGB'))
        else:
            img.paste(gradient_img)
    
    def _generate_resolution(self, img, options):
        """Generate a resolution test pattern"""
        draw = ImageDraw.Draw(img)
        
        # Options
        min_width = options.get('min_width', 1)
        max_width = options.get('max_width', 20)
        color = options.get('color', 0)  # Black for grayscale
        
        # Calculate pattern parameters
        step = options.get('step', 1)
        line_count = (max_width - min_width) // step + 1
        pattern_height = self.size[1] // line_count
        
        # Draw horizontal lines of increasing width
        for i, width in enumerate(range(min_width, max_width + 1, step)):
            y = i * pattern_height + pattern_height // 2
            draw.line([(0, y), (self.size[0], y)], fill=color, width=width)
            
            # Add width label
            font = self._get_font(16)
            draw.text((10, y - 10), f"{width}px", fill=color, font=font)
    
    def _generate_text(self, img, options):
        """Generate a text pattern"""
        draw = ImageDraw.Draw(img)
        
        # Options
        color = options.get('color', 0)  # Black for grayscale
        
        # Add title
        title_font = self._get_font(36)
        draw.text((self.size[0]//2, 50), "InkCraft RIP Text Test Pattern", 
                 fill=color, font=title_font, anchor="mm")
        
        # Add various font sizes
        sizes = [8, 10, 12, 14, 18, 24, 36, 48, 72]
        y_pos = 120
        
        for size in sizes:
            font = self._get_font(size)
            text = f"ABCDEFGabcdefg12345 - {size}pt"
            draw.text((self.size[0]//2, y_pos), text, fill=color, font=font, anchor="mm")
            y_pos += size * 1.5
        
        # Add paragraph text
        if y_pos + 300 < self.size[1]:
            para_font = self._get_font(12)
            paragraph = (
                "This is a printer test pattern for InkCraft RIP software. "
                "This text is used to test font rendering and character spacing. "
                "The quick brown fox jumps over the lazy dog. "
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789"
            )
            
            # Draw paragraph with wrapping
            self._draw_paragraph(draw, paragraph, (100, y_pos), self.size[0] - 200, 
                               para_font, color)
    
    def _generate_alignment(self, img, options):
        """Generate an alignment pattern"""
        draw = ImageDraw.Draw(img)
        
        # Options
        color = options.get('color', 0)  # Black for grayscale
        
        # Draw crosshairs
        center_x, center_y = self.size[0] // 2, self.size[1] // 2
        line_length = min(self.size) // 3
        
        # Center crosshair
        draw.line([(center_x, center_y - line_length), 
                  (center_x, center_y + line_length)], fill=color, width=2)
        draw.line([(center_x - line_length, center_y), 
                  (center_x + line_length, center_y)], fill=color, width=2)
        
        # Corner crosshairs - top left
        draw.line([(50, 50), (50, 50 + line_length//2)], fill=color, width=2)
        draw.line([(50, 50), (50 + line_length//2, 50)], fill=color, width=2)
        
        # Corner crosshairs - top right
        draw.line([(self.size[0] - 50, 50), 
                  (self.size[0] - 50, 50 + line_length//2)], fill=color, width=2)
        draw.line([(self.size[0] - 50, 50), 
                  (self.size[0] - 50 - line_length//2, 50)], fill=color, width=2)
        
        # Corner crosshairs - bottom left
        draw.line([(50, self.size[1] - 50), 
                  (50, self.size[1] - 50 - line_length//2)], fill=color, width=2)
        draw.line([(50, self.size[1] - 50), 
                  (50 + line_length//2, self.size[1] - 50)], fill=color, width=2)
        
        # Corner crosshairs - bottom right
        draw.line([(self.size[0] - 50, self.size[1] - 50), 
                  (self.size[0] - 50, self.size[1] - 50 - line_length//2)], fill=color, width=2)
        draw.line([(self.size[0] - 50, self.size[1] - 50), 
                  (self.size[0] - 50 - line_length//2, self.size[1] - 50)], fill=color, width=2)
        
        # Draw border
        draw.rectangle([10, 10, self.size[0] - 10, self.size[1] - 10], 
                      outline=color, width=2)
        
        # Add labels
        font = self._get_font(36)
        draw.text((center_x, 30), "TOP", fill=color, font=font, anchor="mm")
        draw.text((center_x, self.size[1] - 30), "BOTTOM", fill=color, font=font, anchor="mm")
        draw.text((30, center_y), "LEFT", fill=color, font=font, anchor="mm", angle=90)
        draw.text((self.size[0] - 30, center_y), "RIGHT", fill=color, font=font, anchor="mm", angle=270)
    
    def _get_font(self, size):
        """Get a font for drawing text"""
        try:
            # Try to load a nice font if available
            return ImageFont.truetype("arial.ttf", size)
        except IOError:
            # Fall back to default font
            return ImageFont.load_default()
    
    def _draw_paragraph(self, draw, text, position, width, font, color):
        """Draw a paragraph of text with word wrapping"""
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            # Handle Pillow version compatibility for text width calculation
            try:
                # Use textlength for newer Pillow versions
                word_width = draw.textlength(word + " ", font=font)
            except AttributeError:
                # Fallback for older Pillow versions
                word_width = font.getsize(word + " ")[0]
            
            if current_width + word_width <= width:
                current_line.append(word)
                current_width += word_width
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width
        
        if current_line:
            lines.append(" ".join(current_line))
        
        x, y = position
        # Fix deprecated getsize method
        bbox = font.getbbox("Ay")
        line_height = (bbox[3] - bbox[1]) * 1.2
        
        for line in lines:
            draw.text((x, y), line, fill=color, font=font)
            y += line_height

def main():
    parser = argparse.ArgumentParser(description="InkCraft RIP Test Pattern Generator")
    parser.add_argument("pattern", choices=PATTERNS.keys(), help="Pattern type to generate")
    parser.add_argument("-o", "--output", required=True, help="Output image file path")
    parser.add_argument("--dpi", type=int, default=720, help="Resolution in DPI (default: 720)")
    parser.add_argument("--width", type=int, default=2048, help="Image width in pixels (default: 2048)")
    parser.add_argument("--height", type=int, default=2048, help="Image height in pixels (default: 2048)")
    parser.add_argument("--color-mode", choices=["L", "RGB"], default="L", 
                      help="Color mode: L for grayscale, RGB for color (default: L)")
    
    # Pattern-specific options
    group = parser.add_argument_group("Pattern-specific options")
    group.add_argument("--line-width", type=int, help="Line width for grid pattern")
    group.add_argument("--spacing", type=int, help="Spacing for grid pattern")
    group.add_argument("--bar-count", type=int, help="Number of bars for colorbar pattern")
    group.add_argument("--direction", choices=["horizontal", "vertical"], 
                     help="Direction for gradient pattern")
    group.add_argument("--min-width", type=int, help="Minimum line width for resolution pattern")
    group.add_argument("--max-width", type=int, help="Maximum line width for resolution pattern")
    
    args = parser.parse_args()
    
    # Create pattern generator
    generator = TestPatternGenerator(
        resolution=(args.dpi, args.dpi),
        size=(args.width, args.height)
    )
    
    # Collect pattern options
    options = {
        'color_mode': args.color_mode
    }
    
    # Add pattern-specific options if provided
    if args.line_width is not None:
        options['line_width'] = args.line_width
    
    if args.spacing is not None:
        options['spacing'] = args.spacing
    
    if args.bar_count is not None:
        options['bar_count'] = args.bar_count
    
    if args.direction is not None:
        options['direction'] = args.direction
    
    if args.min_width is not None:
        options['min_width'] = args.min_width
    
    if args.max_width is not None:
        options['max_width'] = args.max_width
    
    # Generate the pattern
    print(f"Generating {PATTERNS[args.pattern]}...")
    generator.create_pattern(args.pattern, args.output, options)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 