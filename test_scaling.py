#!/usr/bin/env python3

import pygame
import sys
import os

# Add nanmon to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nanmon'))

from nanmon.display_manager import DisplayManager
from nanmon.constants import WIDTH as LOGICAL_W, HEIGHT as LOGICAL_H

def test_scaling():
    pygame.init()
    
    # Test different window sizes
    test_sizes = [
        (400, 600),   # Small window (exact aspect ratio)
        (800, 1200),  # Default size
        (1000, 800),  # Wide window (different aspect ratio)
        (300, 800),   # Tall narrow window
        (1600, 900),  # Large wide window
    ]
    
    for width, height in test_sizes:
        print(f"\nTesting window size: {width}x{height}")
        
        # Create display manager with this size
        dm = DisplayManager(initial_size=(width, height))
        
        print(f"Logical size: {LOGICAL_W}x{LOGICAL_H}")
        print(f"Window size: {width}x{height}")
        print(f"Dest rect: {dm.dest_rect}")
        print(f"Scale computed: {dm._compute_scale(width, height):.3f}")
        
        # Test manual resize
        print(f"Testing resize to {width+100}x{height+100}")
        dm.window = pygame.display.set_mode((width+100, height+100), pygame.RESIZABLE)
        dm._recompute_letterbox()
        print(f"After resize - Dest rect: {dm.dest_rect}")
        
        pygame.display.quit()
        pygame.init()  # Reinitialize for next test
    
    pygame.quit()

if __name__ == "__main__":
    test_scaling()
