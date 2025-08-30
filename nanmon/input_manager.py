from __future__ import annotations
import pygame
import math
from typing import Dict, Tuple, Optional, Any
from .constants import WIDTH, HEIGHT


class InputManager:
    """
    Handles both keyboard/PC and touch/mobile input
    Provides unified interface for game controls
    """
    
    def __init__(self, display_manager=None):
        self.display_manager = display_manager
        
        # Touch/mobile state
        self.is_mobile = False  # Can be set to force mobile mode
        self.touch_active = False  # Track if touch is currently held down
        self.touch_position: Optional[Tuple[float, float]] = None  # Current touch position
        self.touch_move_threshold = 10  # Minimum distance to consider as movement
        
        # Swipe detection for menu
        self.swipe_start: Optional[Tuple[float, float]] = None
        self.swipe_min_distance = 50
        self.last_swipe_direction: Optional[str] = None
        
        # Touch UI areas
        self.mode_switch_touch = False  # Track if mode switch area was touched
        
        # Key states (for PC compatibility)
        self.keys_pressed: Dict[int, bool] = {}
        
    def detect_mobile(self) -> bool:
        """Auto-detect if we're on a mobile platform"""
        try:
            # Check for touch support
            return pygame.get_init() and hasattr(pygame, 'FINGERDOWN')
        except:
            return False
    
    def world_to_logical(self, screen_x: int, screen_y: int) -> Tuple[Optional[float], Optional[float]]:
        """Convert screen coordinates to logical game coordinates"""
        if self.display_manager:
            # Get the dest_rect (where game is rendered on screen)
            dest_rect = self.display_manager.dest_rect
            
            # Convert screen coords to logical coords
            if (screen_x < dest_rect.x or screen_x > dest_rect.x + dest_rect.width or
                screen_y < dest_rect.y or screen_y > dest_rect.y + dest_rect.height):
                # Touch is outside game area (in letterbox)
                return None, None
                
            # Map to logical coordinates
            rel_x = (screen_x - dest_rect.x) / dest_rect.width
            rel_y = (screen_y - dest_rect.y) / dest_rect.height
            
            logical_x = rel_x * WIDTH
            logical_y = rel_y * HEIGHT
            
            return logical_x, logical_y
        else:
            # Fallback - assume no scaling
            return float(screen_x), float(screen_y)
    
    def is_touch_in_letterbox(self, screen_x: int, screen_y: int) -> bool:
        """Check if touch is in the letterbox area (outside game)"""
        if self.display_manager:
            dest_rect = self.display_manager.dest_rect
            return (screen_x < dest_rect.x or screen_x > dest_rect.x + dest_rect.width or
                    screen_y < dest_rect.y or screen_y > dest_rect.y + dest_rect.height)
        return False
    
    def handle_event(self, event: pygame.event.Event) -> Dict[str, Any]:
        """
        Process input events and return standardized input state
        Returns dict with keys: movement, mode_switch, select, skip, menu_nav
        """
        result = {
            'movement': None,  # (dx, dy) or None
            'mode_switch': False,
            'select': False,
            'skip': False,
            'menu_nav': None,  # 'up', 'down', 'left', 'right' or None
        }
        
        # Handle keyboard events
        if event.type == pygame.KEYDOWN:
            self.keys_pressed[event.key] = True
            
            # Space bar actions
            if event.key == pygame.K_SPACE:
                result['mode_switch'] = True
                result['select'] = True
                result['skip'] = True
            
            # Menu navigation
            if event.key in (pygame.K_UP, pygame.K_w):
                result['menu_nav'] = 'up'
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                result['menu_nav'] = 'down'
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                result['menu_nav'] = 'left'
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                result['menu_nav'] = 'right'
                
        elif event.type == pygame.KEYUP:
            self.keys_pressed[event.key] = False
        
        # Handle touch/mouse events
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click/touch
                screen_x, screen_y = event.pos
                logical_x, logical_y = self.world_to_logical(screen_x, screen_y)
                
                if self.is_touch_in_letterbox(screen_x, screen_y):
                    # Touch in letterbox area - mode switch
                    result['mode_switch'] = True
                    self.mode_switch_touch = True
                else:
                    # Touch in game area
                    result['select'] = True
                    result['skip'] = True
                    
                    if logical_x is not None and logical_y is not None:
                        # Start touch movement - track touch position and set active
                        self.touch_active = True
                        self.touch_position = (logical_x, logical_y)
                
                # Start swipe detection
                self.swipe_start = event.pos
                
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                # Stop touch movement immediately when touch is released
                self.touch_active = False
                self.touch_position = None
                self.swipe_start = None
                self.mode_switch_touch = False
                
        elif event.type == pygame.MOUSEMOTION:
            # Update touch position if touch is active
            if self.touch_active and pygame.mouse.get_pressed()[0]:
                screen_x, screen_y = event.pos
                logical_x, logical_y = self.world_to_logical(screen_x, screen_y)
                
                if logical_x is not None and logical_y is not None:
                    self.touch_position = (logical_x, logical_y)
            
            # Handle swipe detection
            if self.swipe_start and pygame.mouse.get_pressed()[0]:
                # Check for swipe gesture
                current_pos = event.pos
                dx = current_pos[0] - self.swipe_start[0]
                dy = current_pos[1] - self.swipe_start[1]
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > self.swipe_min_distance:
                    # Determine swipe direction
                    if abs(dx) > abs(dy):
                        if dx > 0:
                            result['menu_nav'] = 'right'
                            self.last_swipe_direction = 'right'
                        else:
                            result['menu_nav'] = 'left'
                            self.last_swipe_direction = 'left'
                    else:
                        if dy > 0:
                            result['menu_nav'] = 'down'
                            self.last_swipe_direction = 'down'
                        else:
                            result['menu_nav'] = 'up'
                            self.last_swipe_direction = 'up'
                    
                    # Reset swipe start to avoid repeated triggers
                    self.swipe_start = event.pos
        
        # Handle finger events for true mobile
        elif event.type == pygame.FINGERDOWN:
            self.is_mobile = True
            screen_x = int(event.x * pygame.display.get_surface().get_width())
            screen_y = int(event.y * pygame.display.get_surface().get_height())
            logical_x, logical_y = self.world_to_logical(screen_x, screen_y)
            
            if self.is_touch_in_letterbox(screen_x, screen_y):
                result['mode_switch'] = True
            else:
                result['select'] = True
                result['skip'] = True
                if logical_x is not None and logical_y is not None:
                    # Start touch movement
                    self.touch_active = True
                    self.touch_position = (logical_x, logical_y)
            
            self.swipe_start = (screen_x, screen_y)
            
        elif event.type == pygame.FINGERUP:
            # Stop touch movement immediately
            self.touch_active = False
            self.touch_position = None
            self.swipe_start = None
            
        elif event.type == pygame.FINGERMOTION:
            # Update touch position if active
            if self.touch_active:
                screen_x = int(event.x * pygame.display.get_surface().get_width())
                screen_y = int(event.y * pygame.display.get_surface().get_height())
                logical_x, logical_y = self.world_to_logical(screen_x, screen_y)
                
                if logical_x is not None and logical_y is not None:
                    self.touch_position = (logical_x, logical_y)
            
            # Handle swipe detection
            if self.swipe_start:
                screen_x = int(event.x * pygame.display.get_surface().get_width())
                screen_y = int(event.y * pygame.display.get_surface().get_height())
                dx = screen_x - self.swipe_start[0]
                dy = screen_y - self.swipe_start[1]
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > self.swipe_min_distance:
                    if abs(dx) > abs(dy):
                        result['menu_nav'] = 'right' if dx > 0 else 'left'
                    else:
                        result['menu_nav'] = 'down' if dy > 0 else 'up'
                    
                    self.swipe_start = (screen_x, screen_y)
        
        return result
    
    def get_movement_input(self, player_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        Get movement input for the player
        Returns (dx, dy) normalized movement vector
        """
        # PC keyboard movement
        keys = pygame.key.get_pressed()
        right = 1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0
        left = 1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0
        down = 1 if (keys[pygame.K_DOWN] or keys[pygame.K_s]) else 0
        up = 1 if (keys[pygame.K_UP] or keys[pygame.K_w]) else 0
        
        kb_dx = right - left
        kb_dy = down - up
        
        # If we have keyboard input, use it (PC mode)
        if kb_dx != 0 or kb_dy != 0:
            return float(kb_dx), float(kb_dy)
        
        # Mobile touch movement - only move while touch is active
        if self.touch_active and self.touch_position:
            px, py = player_pos
            tx, ty = self.touch_position
            
            # Calculate direction to touch position
            dx = tx - px
            dy = ty - py
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Only move if we're not already very close to the touch point
            if distance > 5.0:  # Small threshold to avoid jittering
                # Normalize movement vector
                return dx / distance, dy / distance
        
        return 0.0, 0.0
    
    def clear_touch_target(self):
        """Clear the current touch movement target"""
        self.touch_active = False
        self.touch_position = None
