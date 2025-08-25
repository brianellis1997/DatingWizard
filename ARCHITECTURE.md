# Dating Wizard System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│                    (Configuration & Control)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Orchestration Layer                      │
│                  (Main Controller & Queue)                   │
└──────┬──────────────┬──────────────┬──────────────┬────────┘
       │              │              │              │
┌──────▼──────┐ ┌────▼──────┐ ┌────▼──────┐ ┌────▼──────┐
│  Automation │ │  Analysis │ │ Messaging │ │  Calendar │
│    Engine   │ │   Engine  │ │   Engine  │ │Integration│
└─────────────┘ └───────────┘ └───────────┘ └───────────┘
       │              │              │              │
┌──────▼──────────────▼──────────────▼──────────────▼────────┐
│                        Data Layer                           │
│                 (SQLite DB & Encrypted Storage)             │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Orchestration Layer

```python
class DatingWizardOrchestrator:
    def __init__(self):
        self.automation = AutomationEngine()
        self.analyzer = ProfileAnalyzer()
        self.messenger = MessageGenerator()
        self.calendar = CalendarManager()
        self.queue = TaskQueue()
        
    def run(self):
        # Main event loop
        while True:
            task = self.queue.get_next_task()
            self.process_task(task)
```

**Responsibilities:**
- Task scheduling and prioritization
- Component coordination
- Error handling and recovery
- Rate limiting and throttling

### 2. Automation Engine

```python
class AutomationEngine:
    def __init__(self):
        self.driver = self._init_appium()
        self.vision = VisionFallback()
        
    def swipe_right(self):
        # Perform right swipe action
        
    def swipe_left(self):
        # Perform left swipe action
        
    def extract_profile(self):
        # Extract profile data from current view
        
    def send_message(self, message):
        # Send message in chat
```

**Sub-components:**
- **AppiumClient**: Primary automation driver
- **VisionFallback**: Computer vision-based backup
- **ActionRecorder**: Log all actions for debugging
- **StateManager**: Track current app state

### 3. Analysis Engine

```python
class ProfileAnalyzer:
    def __init__(self):
        self.nlp = NLPProcessor()
        self.image_analyzer = ImageAnalyzer()
        self.preference_matcher = PreferenceMatcher()
        
    def analyze_profile(self, profile_data):
        bio_score = self.nlp.analyze_bio(profile_data['bio'])
        image_scores = self.image_analyzer.analyze_images(profile_data['images'])
        match_score = self.preference_matcher.calculate_match(profile_data)
        
        return {
            'should_swipe': match_score > THRESHOLD,
            'match_score': match_score,
            'interests': bio_score['interests'],
            'personality_traits': image_scores['traits']
        }
```

**Analysis Pipeline:**
1. **Text Analysis**
   - Keyword extraction
   - Sentiment analysis
   - Interest identification
   - Red flag detection

2. **Image Analysis**
   - Activity detection (gym, travel, etc.)
   - Group photo identification
   - Style/aesthetic matching

3. **Preference Matching**
   - Weighted scoring system
   - Must-have vs nice-to-have criteria
   - Deal-breaker detection

### 4. Messaging Engine

```python
class MessageGenerator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.template_engine = TemplateEngine()
        self.conversation_tracker = ConversationTracker()
        
    def generate_opener(self, profile_data):
        context = self._build_context(profile_data)
        message = self.llm_client.generate(context, message_type='opener')
        return self._personalize(message, profile_data)
        
    def generate_response(self, conversation_history, new_message):
        context = self.conversation_tracker.get_context(conversation_history)
        response = self.llm_client.generate(context, message_type='response')
        return response
```

**Message Types:**
- **Openers**: Initial messages based on profile
- **Responses**: Context-aware replies
- **Date Proposals**: Calendar-integrated suggestions
- **Re-engagement**: Messages for stalled conversations

### 5. Calendar Integration

```python
class CalendarManager:
    def __init__(self):
        self.calendar_client = CalendarClient()
        self.availability_checker = AvailabilityChecker()
        
    def suggest_date_times(self, preferences=None):
        available_slots = self.availability_checker.get_available_slots()
        filtered_slots = self._filter_by_preferences(available_slots, preferences)
        return filtered_slots[:3]  # Return top 3 options
        
    def book_date(self, date_details):
        event = self._create_event(date_details)
        return self.calendar_client.add_event(event)
```

**Features:**
- Check availability
- Propose multiple time slots
- Book confirmed dates
- Send calendar invites
- Reminder management

## Data Models

### Profile Model
```python
{
    "id": "unique_id",
    "name": "string",
    "age": "integer",
    "bio": "text",
    "images": ["url1", "url2"],
    "interests": ["interest1", "interest2"],
    "matched_at": "timestamp",
    "swipe_decision": "right/left",
    "match_score": "float",
    "conversation_id": "string"
}
```

### Conversation Model
```python
{
    "id": "unique_id",
    "profile_id": "foreign_key",
    "messages": [
        {
            "sender": "user/match",
            "content": "text",
            "timestamp": "datetime"
        }
    ],
    "status": "active/stalled/scheduled_date",
    "last_activity": "timestamp"
}
```

### Preference Model
```python
{
    "user_id": "unique_id",
    "age_range": {"min": 25, "max": 35},
    "interests_required": ["fitness", "travel"],
    "interests_preferred": ["reading", "cooking"],
    "deal_breakers": ["smoking", "drugs"],
    "bio_keywords": ["professional", "ambitious"],
    "swipe_threshold": 0.7
}
```

## Security Architecture

### Data Protection
```python
class SecurityManager:
    def __init__(self):
        self.encryptor = Fernet(self._load_key())
        
    def encrypt_sensitive_data(self, data):
        return self.encryptor.encrypt(data.encode())
        
    def decrypt_sensitive_data(self, encrypted_data):
        return self.encryptor.decrypt(encrypted_data).decode()
```

### Authentication Flow
1. **Local Authentication**: Face ID/Touch ID for app access
2. **API Keys**: Encrypted storage in keychain
3. **Session Management**: Automatic timeout and refresh

## Deployment Architecture

### Local Development
```
MacBook/iMac
    ├── Dating Wizard App
    ├── Appium Server
    ├── SQLite Database
    └── iPhone (USB/WiFi connected)
```

### Production Setup
```
Mac Mini Server (Always On)
    ├── Dating Wizard Service
    ├── Appium Grid
    ├── PostgreSQL Database
    ├── Redis Queue
    └── iPhone (Dedicated Device)
```

## Error Handling Strategy

### Automation Failures
```python
class ErrorHandler:
    def handle_automation_error(self, error):
        if isinstance(error, ElementNotFoundError):
            return self.retry_with_vision_fallback()
        elif isinstance(error, AppCrashError):
            return self.restart_app_and_resume()
        elif isinstance(error, NetworkError):
            return self.wait_and_retry()
```

### Recovery Mechanisms
1. **Automatic Retry**: With exponential backoff
2. **Fallback Methods**: Vision-based when automation fails
3. **State Recovery**: Resume from last known good state
4. **Manual Intervention**: Alert user for critical failures

## Performance Considerations

### Optimization Strategies
1. **Caching**: Profile analysis results
2. **Batch Processing**: Group similar operations
3. **Async Operations**: Non-blocking I/O
4. **Resource Pooling**: Reuse connections

### Scalability
- **Horizontal**: Multiple device support
- **Vertical**: Optimize single device throughput
- **Queue Management**: Priority-based task scheduling

## Monitoring & Logging

### Metrics to Track
```python
METRICS = {
    'swipes_per_hour': Counter,
    'match_rate': Gauge,
    'message_response_rate': Gauge,
    'date_conversion_rate': Gauge,
    'automation_success_rate': Gauge,
    'average_response_time': Histogram
}
```

### Logging Levels
- **DEBUG**: Detailed automation steps
- **INFO**: Successful operations
- **WARNING**: Recoverable errors
- **ERROR**: Failed operations
- **CRITICAL**: System failures

## API Integrations

### External Services
1. **OpenAI/Anthropic**: Message generation
2. **Apple EventKit**: Calendar access
3. **iCloud**: Calendar sync (optional)
4. **Twilio**: SMS notifications (optional)

### Internal APIs
```python
# RESTful API for configuration
GET /api/preferences
POST /api/preferences
GET /api/stats
GET /api/conversations/{id}
POST /api/manual-swipe
```

## Testing Strategy

### Unit Tests
```python
def test_profile_analyzer():
    analyzer = ProfileAnalyzer()
    profile = mock_profile_data()
    result = analyzer.analyze_profile(profile)
    assert result['match_score'] >= 0
    assert result['match_score'] <= 1
```

### Integration Tests
- Automation flow testing
- Message generation validation
- Calendar integration verification

### End-to-End Tests
- Complete swipe-to-date workflow
- Error recovery scenarios
- Performance benchmarks

## Configuration Management

### Environment Variables
```bash
# .env file
APPIUM_URL=http://localhost:4723
OPENAI_API_KEY=sk-...
CALENDAR_SYNC_INTERVAL=300
MAX_SWIPES_PER_HOUR=100
MESSAGE_GENERATION_MODEL=gpt-4
```

### User Preferences
```json
{
  "automation": {
    "enabled": true,
    "speed": "normal",
    "hours": ["09:00", "22:00"]
  },
  "matching": {
    "auto_swipe": true,
    "require_confirmation": false,
    "threshold": 0.7
  },
  "messaging": {
    "auto_opener": true,
    "style": "casual",
    "emoji_usage": "moderate"
  }
}
```