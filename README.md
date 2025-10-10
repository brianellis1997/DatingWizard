# Dating Wizard 🧙‍♂️

An AI-powered dating assistant that analyzes dating profiles using multimodal AI (computer vision + NLP) to find compatible matches based on your personalized preferences.

## 🎉 **NEW: Working Prototype Available!**

The **classification prototype** is now complete and functional! This MVP allows you to:
- ✅ Upload reference images of people you find attractive
- ✅ Set personality traits and interests you value
- ✅ Classify profile screenshots with detailed reasoning
- ✅ Automatically discover and classify Instagram profiles
- ✅ Measure accuracy with evaluation tools

**[📚 See PROTOTYPE_GUIDE.md for complete instructions](PROTOTYPE_GUIDE.md)**

### Quick Start

```bash
# Interactive setup wizard
python quick_start.py

# Or manually:
# 1. Set up preferences
python preference_cli.py

# 2. Test on a screenshot
python demo_classifier.py --mode single --screenshot path/to/profile.png

# 3. Run Instagram pipeline
python instagram_classifier_pipeline.py --query "fitness" --limit 20
```

## Features

### 🎯 Smart Swiping
- Computer vision-based profile analysis
- Learns from your preferences over time
- Configurable matching criteria (bio keywords, interests, age range)
- Super like support for high-confidence matches

### 💬 Intelligent Messaging
- LLM-powered message generation (OpenAI/Anthropic)
- Personalized openers based on profile content
- Context-aware responses
- Goal-oriented conversation flow (rapport → number → date)
- Customizable messaging style

### 📅 Calendar Integration
- Apple Calendar support via CalDAV
- Automatic availability checking
- Date scheduling with smart time suggestions
- Event creation with reminders

### 🤖 Automation Modes
- **Auto Mode**: Full automation of swiping and messaging
- **Swipe Mode**: Only automated swiping
- **Message Mode**: Only automated messaging
- **Learn Mode**: Interactive training to improve preferences

## Setup

### Prerequisites
- macOS/Linux/Windows
- Python 3.9+
- Chrome browser
- Tinder account

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/DatingWizard.git
cd DatingWizard
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Tesseract OCR:
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

5. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

### Configuration

1. **Edit `.env`** with your credentials:
   - OpenAI/Anthropic API key for message generation
   - Calendar credentials (optional)
   - Tinder login details (optional)

2. **Customize `config/preferences.json`**:
   - Age range preferences
   - Bio keywords (positive/negative)
   - Interests and dealbreakers
   - Messaging style
   - Automation settings

3. **Train the AI** (optional):
   - Add liked profiles to `config/liked_profiles/`
   - Add disliked profiles to `config/disliked_profiles/`
   - Or use Learn Mode to train interactively

## Usage

### Basic Usage

```bash
# Run in full auto mode
python main.py --mode auto

# Run in swipe-only mode
python main.py --mode swipe

# Run in message-only mode
python main.py --mode message

# Run in learning mode (interactive training)
python main.py --mode learn
```

### First Run

1. Start the wizard:
```bash
python main.py --mode learn
```

2. The browser will open to Tinder.com
3. **Login manually** when prompted
4. In learn mode, you'll see each profile and can decide:
   - R: Swipe right
   - L: Swipe left
   - S: Super like
   - Q: Quit

5. After training on 20-30 profiles, switch to auto mode:
```bash
python main.py --mode auto
```

### Advanced Options

```bash
# Use custom config file
python main.py --config path/to/config.json

# Run with specific preferences
python main.py --mode auto --config config/conservative.json
```

## Project Structure

```
DatingWizard/
├── src/
│   ├── controllers/       # Browser automation
│   ├── analyzers/         # Profile analysis
│   ├── messaging/         # Message generation
│   ├── calendar/          # Calendar integration
│   └── utils/            # Helper functions
├── config/
│   ├── preferences.json  # User preferences
│   ├── liked_profiles/   # Training data (liked)
│   └── disliked_profiles/ # Training data (disliked)
├── data/
│   ├── screenshots/       # Profile screenshots
│   └── stats.json        # Usage statistics
├── logs/                  # Application logs
├── main.py               # Main entry point
└── requirements.txt      # Python dependencies
```

## Safety & Ethics

### Important Considerations

1. **Terms of Service**: This tool may violate Tinder's ToS. Use at your own risk.
2. **Privacy**: All data is stored locally. Never share your `.env` file.
3. **Respect**: Use responsibly and treat matches with respect.
4. **Consent**: Be transparent about using automation if asked.
5. **Rate Limiting**: Built-in delays prevent detection and server overload.

### Best Practices

- Start with conservative settings
- Review messages before enabling full automation
- Use learn mode to improve accuracy
- Regularly update preferences based on results
- Take breaks to appear more human-like

## Troubleshooting

### Common Issues

1. **Login fails**
   - Enable manual login mode
   - Check for Tinder updates
   - Try different browser

2. **OCR not working**
   - Verify Tesseract installation
   - Check screenshot quality
   - Adjust screen resolution

3. **Messages not sending**
   - Check API keys in `.env`
   - Verify rate limits
   - Review message generation logs

4. **Calendar not syncing**
   - Verify CalDAV credentials
   - Check calendar permissions
   - Test with simple event first

## Customization

### Adding Custom Message Styles

Edit `src/messaging/message_generator.py`:
```python
style_map = {
    "your_style": "Description of your messaging style",
    # ...
}
```

### Modifying Swipe Criteria

Edit `config/preferences.json`:
```json
{
  "bio_keywords": {
    "positive": ["your", "keywords"],
    "negative": ["dealbreaker", "words"]
  }
}
```

### Training Custom Models

Place example images in:
- `config/liked_profiles/` - Profiles you like
- `config/disliked_profiles/` - Profiles you don't like

The system will learn from these examples.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Disclaimer

This tool is for educational purposes only. The developers are not responsible for:
- Account bans or restrictions
- Misuse of the automation
- Any consequences from using this tool

Always comply with platform terms of service and local laws.

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues first
- Include logs when reporting bugs

---

**Remember**: The best connections come from genuine interactions. Use this tool to save time, but always be authentic in your conversations.
