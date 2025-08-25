#!/usr/bin/env python3
"""
Dating Wizard - Main automation script
Automates Tinder swiping, messaging, and date scheduling
"""

import os
import sys
import time
import random
import json
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv
from loguru import logger
import argparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from controllers.tinder_controller import TinderController
from analyzers.profile_analyzer import ProfileAnalyzer
from messaging.message_generator import MessageGenerator, ConversationStage
from calendar_manager.calendar_integration import CalendarManager


class DatingWizard:
    """Main orchestrator for the dating automation system"""
    
    def __init__(self, config_path: str = "config/preferences.json"):
        logger.add("logs/dating_wizard_{time}.log", rotation="1 day")
        logger.info("Initializing Dating Wizard...")
        
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.tinder = TinderController(headless=False)
        self.analyzer = ProfileAnalyzer(config_path)
        self.messenger = MessageGenerator(config_path)
        self.calendar = CalendarManager(config_path)
        
        # Statistics
        self.stats = {
            'profiles_viewed': 0,
            'right_swipes': 0,
            'left_swipes': 0,
            'matches': 0,
            'messages_sent': 0,
            'dates_scheduled': 0
        }
        
    def _load_config(self, path: str) -> Dict:
        """Load configuration from file"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}
        
    def run(self, mode: str = "auto"):
        """Main execution loop"""
        logger.info(f"Starting Dating Wizard in {mode} mode")
        
        try:
            # Login to Tinder
            if not self._login():
                logger.error("Failed to login, exiting...")
                return
                
            if mode == "auto":
                self._run_auto_mode()
            elif mode == "swipe":
                self._run_swipe_mode()
            elif mode == "message":
                self._run_message_mode()
            elif mode == "learn":
                self._run_learning_mode()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self._cleanup()
            
    def _login(self) -> bool:
        """Handle login process"""
        logger.info("Please login to Tinder manually in the browser window...")
        return self.tinder.login()
        
    def _run_auto_mode(self):
        """Fully automated swiping and messaging"""
        logger.info("Running in full auto mode")
        
        while True:
            try:
                # Check time restrictions
                if not self._is_active_hour():
                    logger.info("Outside active hours, waiting...")
                    time.sleep(300)  # Check every 5 minutes
                    continue
                    
                # Swipe on profiles
                self._auto_swipe_batch()
                
                # Check and respond to messages
                self._process_messages()
                
                # Random longer break
                if random.random() < 0.1:  # 10% chance
                    delay = random.uniform(60, 180)
                    logger.info(f"Taking a break for {delay:.0f} seconds...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error in auto mode: {e}")
                time.sleep(30)
                
    def _run_swipe_mode(self):
        """Only automated swiping"""
        logger.info("Running in swipe-only mode")
        
        while True:
            try:
                self._auto_swipe_batch()
                
                # Take a break between batches
                delay = random.uniform(30, 60)
                logger.info(f"Break for {delay:.0f} seconds...")
                time.sleep(delay)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in swipe mode: {e}")
                time.sleep(30)
                
    def _run_message_mode(self):
        """Only automated messaging"""
        logger.info("Running in message-only mode")
        
        while True:
            try:
                self._process_messages()
                
                # Check for new messages every few minutes
                delay = random.uniform(120, 300)
                logger.info(f"Waiting {delay:.0f} seconds before next check...")
                time.sleep(delay)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in message mode: {e}")
                time.sleep(30)
                
    def _run_learning_mode(self):
        """Interactive mode to train preferences"""
        logger.info("Running in learning mode - you decide on each profile")
        
        while True:
            try:
                # Get current profile
                profile = self.tinder.get_current_profile()
                if not profile or not profile.get('name'):
                    logger.warning("No profile found or profile data incomplete")
                    print("\n" + "="*50)
                    print("Waiting for profile to load...")
                    print("Try refreshing the browser or navigating manually to profiles")
                    print("="*50)
                    decision = input("Press [R]efresh, [C]ontinue waiting, or [Q]uit? ").lower()
                    if decision == 'q':
                        break
                    elif decision == 'r':
                        self.tinder.driver.refresh()
                    time.sleep(3)
                    continue
                    
                # Display profile info
                print("\n" + "="*50)
                print(f"Name: {profile.get('name', 'Unknown')}, Age: {profile.get('age', 'Unknown')}")
                print(f"Bio: {profile.get('bio', 'No bio')[:200]}")
                print(f"Interests: {', '.join(profile.get('interests', []))}")
                print("="*50)
                
                # Get user decision
                decision = input("Swipe [R]ight, [L]eft, [S]uper like, or [Q]uit? ").lower()
                
                if decision == 'q':
                    break
                elif decision == 'r':
                    self.tinder.swipe_right()
                    # Save as positive example
                    screenshot = self.tinder.take_screenshot()
                    self.analyzer.add_training_example(screenshot, liked=True)
                elif decision == 'l':
                    self.tinder.swipe_left()
                    # Save as negative example
                    screenshot = self.tinder.take_screenshot()
                    self.analyzer.add_training_example(screenshot, liked=False)
                elif decision == 's':
                    self.tinder.super_like()
                    screenshot = self.tinder.take_screenshot()
                    self.analyzer.add_training_example(screenshot, liked=True)
                    
                # Human-like delay
                self.tinder.human_delay()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in learning mode: {e}")
                
    def _auto_swipe_batch(self, batch_size: int = 10):
        """Automatically swipe on a batch of profiles"""
        logger.info(f"Starting swipe batch (size: {batch_size})")
        
        for i in range(batch_size):
            try:
                # Take screenshot for analysis
                screenshot_path = self.tinder.take_screenshot()
                
                # Get profile data
                profile = self.tinder.get_current_profile()
                self.stats['profiles_viewed'] += 1
                
                # Analyze profile
                analysis = self.analyzer.analyze_screenshot(screenshot_path)
                
                logger.info(f"Profile: {profile.get('name', 'Unknown')} - "
                          f"Decision: {analysis['decision']} "
                          f"(confidence: {analysis['confidence']:.2f})")
                
                # Perform swipe action
                if analysis['decision'] == 'super_like':
                    success = self.tinder.super_like()
                elif analysis['decision'] == 'right':
                    success = self.tinder.swipe_right()
                    self.stats['right_swipes'] += 1
                else:
                    success = self.tinder.swipe_left()
                    self.stats['left_swipes'] += 1
                    
                # Check for match
                if success and analysis['decision'] in ['right', 'super_like']:
                    if self.tinder.check_for_match():
                        self.stats['matches'] += 1
                        self._handle_new_match(profile)
                        self.tinder.close_match_popup()
                        
                # Human-like delay between swipes
                delay = random.uniform(
                    self.config['automation']['min_delay_seconds'],
                    self.config['automation']['max_delay_seconds']
                )
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error during swipe: {e}")
                time.sleep(5)
                
        self._log_stats()
        
    def _process_messages(self):
        """Process and respond to messages"""
        logger.info("Checking messages...")
        
        try:
            matches = self.tinder.get_matches()
            
            for match in matches[:5]:  # Process up to 5 matches
                try:
                    # Open chat
                    if not self.tinder.open_chat(match['name']):
                        continue
                        
                    # Get conversation history
                    messages = self.tinder.get_chat_messages()
                    
                    if not messages:
                        # Send opener
                        self._send_opener(match)
                    else:
                        # Check if we need to respond
                        if self._should_respond(messages):
                            self._send_response(messages, match)
                            
                    # Random delay between chats
                    time.sleep(random.uniform(3, 8))
                    
                except Exception as e:
                    logger.error(f"Error processing messages for {match['name']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error getting matches: {e}")
            
    def _handle_new_match(self, profile: Dict):
        """Handle a new match"""
        logger.success(f"New match with {profile.get('name', 'Unknown')}!")
        
        if self.config['automation']['auto_message']:
            # Wait a bit before sending message
            delay = random.uniform(30, 120)
            logger.info(f"Will send opener in {delay:.0f} seconds...")
            # Note: In production, this would be queued
            
    def _send_opener(self, match: Dict):
        """Send opening message to a match"""
        try:
            # Generate opener
            opener = self.messenger.generate_opener(match)
            
            # Send message
            if self.tinder.send_message(opener):
                self.stats['messages_sent'] += 1
                logger.success(f"Sent opener to {match['name']}: {opener}")
                
        except Exception as e:
            logger.error(f"Failed to send opener: {e}")
            
    def _send_response(self, messages: List[Dict], match: Dict):
        """Send response in ongoing conversation"""
        try:
            # Get last message from them
            their_last = None
            for msg in reversed(messages):
                if msg['sender'] == 'match':
                    their_last = msg['text']
                    break
                    
            if not their_last:
                return
                
            # Generate response
            response = self.messenger.generate_response(messages, their_last)
            
            # Check if we should suggest a date
            if len(messages) > 10:
                # Get calendar availability
                available_times = self.calendar.suggest_date_times(match['name'])
                if available_times:
                    response = self.messenger.suggest_date(messages, 
                                                          [{'day': t, 'time': t} for t in available_times])
                    
            # Send message
            if self.tinder.send_message(response):
                self.stats['messages_sent'] += 1
                logger.success(f"Sent response to {match['name']}: {response}")
                
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
            
    def _should_respond(self, messages: List[Dict]) -> bool:
        """Determine if we should send a response"""
        if not messages:
            return False
            
        # Check if last message was from them
        last_message = messages[-1]
        return last_message['sender'] == 'match'
        
    def _is_active_hour(self) -> bool:
        """Check if current time is within active hours"""
        current_hour = datetime.now().hour
        active_hours = self.config['automation']['hours_active']
        
        start_hour = int(active_hours[0].split(':')[0])
        end_hour = int(active_hours[1].split(':')[0])
        
        return start_hour <= current_hour < end_hour
        
    def _log_stats(self):
        """Log current statistics"""
        logger.info(f"Stats - Viewed: {self.stats['profiles_viewed']}, "
                   f"Right: {self.stats['right_swipes']}, "
                   f"Left: {self.stats['left_swipes']}, "
                   f"Matches: {self.stats['matches']}, "
                   f"Messages: {self.stats['messages_sent']}")
                   
    def _cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        self.tinder.close()
        
        # Save final stats
        with open('data/stats.json', 'w') as f:
            json.dump(self.stats, f, indent=2)
            
        logger.info("Dating Wizard shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Dating Wizard - Automated Dating Assistant')
    parser.add_argument('--mode', choices=['auto', 'swipe', 'message', 'learn'],
                       default='auto', help='Operation mode')
    parser.add_argument('--config', default='config/preferences.json',
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs('data/screenshots', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('config/liked_profiles', exist_ok=True)
    os.makedirs('config/disliked_profiles', exist_ok=True)
    
    # Run the wizard
    wizard = DatingWizard(args.config)
    wizard.run(args.mode)


if __name__ == "__main__":
    main()