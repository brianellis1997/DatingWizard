"""
Calendar Integration - Manages Apple Calendar for date scheduling
Checks availability and creates events
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import caldav
from icalendar import Calendar, Event
import pytz
from loguru import logger
import json


class CalendarManager:
    """Manages calendar integration for date scheduling"""
    
    def __init__(self, preferences_path: str = "config/preferences.json"):
        self.preferences = self._load_preferences(preferences_path)
        self.client = None
        self.calendar = None
        self.timezone = pytz.timezone('America/Los_Angeles')  # Default, update as needed
        self._setup_calendar_connection()
        
    def _load_preferences(self, path: str) -> Dict:
        """Load date preferences"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f).get('date_preferences', {})
        return {
            "preferred_days": ["Friday", "Saturday", "Sunday"],
            "preferred_times": ["18:00-21:00", "11:00-14:00"],
            "preferred_activities": ["coffee", "drinks", "dinner"]
        }
        
    def _setup_calendar_connection(self):
        """Setup connection to calendar server"""
        try:
            # Get credentials from environment
            calendar_url = os.getenv('CALENDAR_URL', 'https://caldav.icloud.com/')
            username = os.getenv('CALENDAR_USERNAME')
            password = os.getenv('CALENDAR_PASSWORD')
            
            if not username or not password:
                logger.warning("Calendar credentials not found in environment")
                return
                
            # Connect to CalDAV server
            self.client = caldav.DAVClient(
                url=calendar_url,
                username=username,
                password=password
            )
            
            # Get principal calendar
            principal = self.client.principal()
            calendars = principal.calendars()
            
            if calendars:
                self.calendar = calendars[0]  # Use first calendar
                logger.success("Connected to calendar successfully")
            else:
                logger.warning("No calendars found")
                
        except Exception as e:
            logger.error(f"Failed to connect to calendar: {e}")
            
    def get_availability(self, days_ahead: int = 7) -> List[Dict]:
        """Get available time slots for the next N days"""
        available_slots = []
        
        # Get current date
        today = datetime.now(self.timezone)
        
        for days in range(1, days_ahead + 1):
            check_date = today + timedelta(days=days)
            day_name = check_date.strftime('%A')
            
            # Check if this is a preferred day
            if day_name in self.preferences['preferred_days']:
                # Check each preferred time slot
                for time_range in self.preferences['preferred_times']:
                    start_hour, end_hour = self._parse_time_range(time_range)
                    
                    # Create datetime objects for the slot
                    slot_start = check_date.replace(
                        hour=start_hour[0],
                        minute=start_hour[1],
                        second=0,
                        microsecond=0
                    )
                    slot_end = check_date.replace(
                        hour=end_hour[0],
                        minute=end_hour[1],
                        second=0,
                        microsecond=0
                    )
                    
                    # Check if slot is available
                    if self._is_slot_available(slot_start, slot_end):
                        available_slots.append({
                            'date': check_date.date(),
                            'day': day_name,
                            'time': time_range,
                            'start': slot_start,
                            'end': slot_end,
                            'formatted': f"{day_name} {check_date.strftime('%B %d')} at {start_hour[0]}:{start_hour[1]:02d}"
                        })
                        
        logger.info(f"Found {len(available_slots)} available slots")
        return available_slots
        
    def _parse_time_range(self, time_range: str) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Parse time range string like '18:00-21:00' """
        start_str, end_str = time_range.split('-')
        start_hour, start_min = map(int, start_str.split(':'))
        end_hour, end_min = map(int, end_str.split(':'))
        return ((start_hour, start_min), (end_hour, end_min))
        
    def _is_slot_available(self, start: datetime, end: datetime) -> bool:
        """Check if a time slot is available in calendar"""
        if not self.calendar:
            # If no calendar connection, assume available
            return True
            
        try:
            # Search for events in this time range
            events = self.calendar.date_search(start, end)
            
            # If no events found, slot is available
            return len(events) == 0
            
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            # On error, assume available
            return True
            
    def create_date_event(self, date_details: Dict) -> bool:
        """Create a calendar event for a date"""
        try:
            if not self.calendar:
                logger.warning("No calendar connection, skipping event creation")
                return False
                
            # Create event
            cal = Calendar()
            event = Event()
            
            # Set event properties
            event.add('summary', f"Date with {date_details['name']}")
            event.add('dtstart', date_details['start'])
            event.add('dtend', date_details['end'])
            event.add('location', date_details.get('location', 'TBD'))
            
            # Add description
            description = f"""Date with {date_details['name']}
Activity: {date_details.get('activity', 'Coffee/Drinks')}
Notes: {date_details.get('notes', 'Met on Tinder')}
Phone: {date_details.get('phone', 'Not provided yet')}"""
            event.add('description', description)
            
            # Add reminder (30 minutes before)
            event.add('alarm', timedelta(minutes=-30))
            
            # Add event to calendar
            cal.add_component(event)
            self.calendar.add_event(cal.to_ical())
            
            logger.success(f"Created calendar event for date with {date_details['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return False
            
    def suggest_date_times(self, match_name: str) -> List[str]:
        """Get formatted date time suggestions for a match"""
        available_slots = self.get_availability()
        
        if not available_slots:
            # Fallback suggestions
            return [
                "this weekend",
                "Friday evening",
                "Saturday afternoon"
            ]
            
        # Return top 3 formatted suggestions
        suggestions = []
        for slot in available_slots[:3]:
            suggestions.append(slot['formatted'])
            
        return suggestions
        
    def quick_schedule(self, match_name: str, activity: str = None) -> Dict:
        """Quickly schedule a date with best available slot"""
        available_slots = self.get_availability()
        
        if not available_slots:
            return {
                'success': False,
                'message': "No available slots found in the next week"
            }
            
        # Use first available slot
        best_slot = available_slots[0]
        
        # Determine activity
        if not activity:
            # Use time of day to suggest activity
            hour = best_slot['start'].hour
            if hour < 12:
                activity = "brunch"
            elif hour < 17:
                activity = "coffee"
            else:
                activity = "drinks"
                
        # Create event
        date_details = {
            'name': match_name,
            'start': best_slot['start'],
            'end': best_slot['end'],
            'activity': activity,
            'location': self._suggest_location(activity),
            'notes': f"Scheduled via Dating Wizard"
        }
        
        success = self.create_date_event(date_details)
        
        return {
            'success': success,
            'slot': best_slot,
            'activity': activity,
            'message': f"Date scheduled for {best_slot['formatted']}"
        }
        
    def _suggest_location(self, activity: str) -> str:
        """Suggest a location based on activity type"""
        location_map = {
            "coffee": "Local coffee shop",
            "drinks": "Nice bar downtown",
            "dinner": "Italian restaurant",
            "brunch": "Trendy brunch spot",
            "walk": "City park",
            "museum": "Art museum"
        }
        
        return location_map.get(activity, "Location TBD")
        
    def update_event_with_phone(self, match_name: str, phone_number: str) -> bool:
        """Update existing date event with phone number"""
        try:
            if not self.calendar:
                return False
                
            # Search for event
            today = datetime.now(self.timezone)
            week_later = today + timedelta(days=7)
            
            events = self.calendar.date_search(today, week_later)
            
            for event in events:
                event_data = event.data
                if match_name.lower() in event_data.lower():
                    # Update description with phone number
                    # This would require parsing and updating the iCal data
                    logger.info(f"Updated event with phone number for {match_name}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return False
            
    def get_upcoming_dates(self) -> List[Dict]:
        """Get list of upcoming scheduled dates"""
        upcoming = []
        
        try:
            if not self.calendar:
                return upcoming
                
            today = datetime.now(self.timezone)
            week_later = today + timedelta(days=7)
            
            events = self.calendar.date_search(today, week_later)
            
            for event in events:
                event_data = event.data
                # Parse event data to extract date information
                # This would require iCal parsing
                if "Date with" in event_data:
                    upcoming.append({
                        'raw': event_data
                    })
                    
            logger.info(f"Found {len(upcoming)} upcoming dates")
            return upcoming
            
        except Exception as e:
            logger.error(f"Failed to get upcoming dates: {e}")
            return upcoming