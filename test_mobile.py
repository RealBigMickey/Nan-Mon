#!/usr/bin/env python3

import pygame
import sys
import os

# Add nanmon to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nanmon'))

from nanmon.input_manager import InputManager
from nanmon.display_manager import DisplayManager

def test_mobile_controls():
    pygame.init()
    
    # Create a simple test window
    dm = DisplayManager(initial_size=(400, 600))
    input_manager = InputManager(dm)
    
    print("Mobile Controls Test")
    print("===================")
    print("- Click/Touch anywhere in the game area to set movement target")
    print("- Click/Touch in grey areas (letterbox) to toggle mode")
    print("- Drag to create swipe gestures for menu navigation")
    print("- Press ESC to quit")
    print()
    
    clock = pygame.time.Clock()
    running = True
    player_pos = [300.0, 450.0]  # Test player position
    
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                # Test input manager
                input_result = input_manager.handle_event(event)
                
                # Print results for debugging
                if any(input_result.values()):
                    print(f"Input: {input_result}")
                
                if input_result['mode_switch']:
                    print("Mode switch triggered!")
                
                if input_result['menu_nav']:
                    print(f"Menu navigation: {input_result['menu_nav']}")
                
                if input_result['select']:
                    print("Select triggered!")
                
                if input_result['skip']:
                    print("Skip triggered!")
        
        # Test movement
        move_x, move_y = input_manager.get_movement_input((player_pos[0], player_pos[1]))
        if move_x != 0 or move_y != 0:
            player_pos[0] += move_x * 100 * dt  # Move at 100 pixels per second
            player_pos[1] += move_y * 100 * dt
            print(f"Player moving: {move_x:.2f}, {move_y:.2f} -> pos: {player_pos[0]:.1f}, {player_pos[1]:.1f}")
        
        # Simple rendering
        frame = dm.get_logical_surface()
        frame.fill((50, 50, 50))
        
        # Draw player as red circle
        pygame.draw.circle(frame, (255, 0, 0), (int(player_pos[0]), int(player_pos[1])), 10)
        
        # Draw touch position if any
        if input_manager.touch_active and input_manager.touch_position:
            tx, ty = input_manager.touch_position
            pygame.draw.circle(frame, (0, 255, 0), (int(tx), int(ty)), 5)
            pygame.draw.line(frame, (0, 255, 0), (int(player_pos[0]), int(player_pos[1])), (int(tx), int(ty)), 2)
        
        dm.present()
    
    pygame.quit()

if __name__ == "__main__":
    test_mobile_controls()
