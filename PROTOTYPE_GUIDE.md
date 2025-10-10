# Dating Wizard Prototype - User Guide

## 🎯 Overview

The Dating Wizard Prototype is a multimodal AI system that classifies potential dating partners based on your preferences. It analyzes profile screenshots using computer vision and NLP to determine compatibility.

### Key Features

- **Multimodal Classification**: Analyzes both images and text
- **Customizable Preferences**: Set importance weights for physical, personality, and interests
- **Reference Images**: Upload photos of people you find attractive
- **Instagram Integration**: Automatically discover and classify Instagram profiles
- **Detailed Insights**: Get reasons for each classification decision

## 🚀 Quick Start

### 1. Set Up Your Preferences

First, configure your ideal partner preferences:

```bash
python preference_cli.py
```

This interactive CLI will guide you through:
- Uploading reference images of attractive people
- Setting personality traits you value
- Defining shared interests
- Configuring importance weights

**Example:**
```bash
# Upload reference images
python preference_cli.py
> Add reference image? (y/n): y
> Enter path to image: /path/to/attractive_person.jpg
> Category: face
> Description: Love this type of smile

# Set weights
# Physical: 0.6 (60% importance)
# Personality: 0.3 (30% importance)
# Interests: 0.1 (10% importance)
```

### 2. Test the Classifier

#### Interactive Demo

The easiest way to test the classifier:

```bash
python demo_classifier.py --mode interactive
```

Then enter paths to profile screenshots when prompted.

#### Single Screenshot

Classify a single profile:

```bash
python demo_classifier.py --mode single --screenshot path/to/profile.png
```

#### Batch Processing

Classify multiple screenshots:

```bash
python demo_classifier.py --mode batch --directory data/test_profiles/matches/
```

### 3. Evaluate Accuracy

Test the classifier on labeled data:

```bash
# Create test dataset structure
python evaluate_classifier.py --create-dataset

# Add screenshots to:
# - data/test_profiles/matches/ (profiles you'd like)
# - data/test_profiles/non_matches/ (profiles you wouldn't like)

# Run evaluation
python evaluate_classifier.py --error-analysis
```

### 4. Instagram Pipeline (Advanced)

Automatically find and classify Instagram profiles:

```bash
python instagram_classifier_pipeline.py --query "fitness" --limit 20 --min-score 0.7
```

## 📊 Understanding Results

### Classification Result Format

Each classification provides:

```
✅ MATCH (Confidence: 78.5%)
============================================================

📊 Component Scores:
  • Physical:    85.0% (weight: 60.0%)
  • Personality: 72.0% (weight: 30.0%)
  • Interests:   65.0% (weight: 10.0%)

📝 Extracted Data:
  • Name: Sarah
  • Age: 28
  • Bio: Love hiking, yoga, and coffee...

💡 Reasons:
  • Strong visual similarity to your reference images
  • Shares your interest in hiking
  • Shares your interest in yoga
  • Age 28 is within your preferred range (25-35)
```

### Interpreting Scores

- **Confidence Score**: Overall match probability (0-100%)
  - ≥85%: Exceptional match
  - 70-85%: Strong match
  - 60-70%: Moderate match
  - <60%: Not a match (by default)

- **Component Scores**:
  - **Physical**: Visual similarity to your preferences
  - **Personality**: Bio keyword and trait matching
  - **Interests**: Shared hobbies and activities

## 🔧 Configuration

### Preferences File Structure

Located at `config/preferences.json`:

```json
{
  "partner_preferences": {
    "physical": {
      "importance_weight": 0.6,
      "reference_images": []
    },
    "personality": {
      "importance_weight": 0.3,
      "traits": ["adventurous", "health-conscious", "ambitious"]
    },
    "interests": {
      "importance_weight": 0.1,
      "shared_interests": ["hiking", "yoga", "reading"],
      "dealbreaker_interests": ["smoking", "drugs"]
    }
  },
  "matching_criteria": {
    "minimum_score": 0.6,
    "super_like_score": 0.85
  },
  "age_range": {
    "min": 25,
    "max": 35
  },
  "bio_keywords": {
    "positive": ["fitness", "travel", "foodie"],
    "negative": ["drama", "hookup"]
  }
}
```

### Adjusting Weights

To optimize for different priorities:

**Looks-focused** (70/20/10):
```json
"physical": {"importance_weight": 0.7}
"personality": {"importance_weight": 0.2}
"interests": {"importance_weight": 0.1}
```

**Personality-focused** (30/50/20):
```json
"physical": {"importance_weight": 0.3}
"personality": {"importance_weight": 0.5}
"interests": {"importance_weight": 0.2}
```

**Balanced** (50/30/20):
```json
"physical": {"importance_weight": 0.5}
"personality": {"importance_weight": 0.3}
"interests": {"importance_weight": 0.2}
```

## 📸 Working with Screenshots

### Best Practices

1. **High Quality**: Use clear, well-lit screenshots
2. **Full Profile**: Capture both images and bio text
3. **Resolution**: At least 800x1000 pixels recommended
4. **Format**: JPG or PNG

### Taking Screenshots

**Instagram Profiles**:
- Open profile in browser
- Take full-page screenshot (Cmd+Shift+4 on Mac)
- Save to your test directory

**Dating Apps** (Tinder, Bumble, etc.):
- Use web version when possible
- Capture card/profile view
- Include both photo and bio

### Example Screenshot Structure

```
data/test_profiles/
├── matches/
│   ├── profile_01.png
│   ├── profile_02.png
│   └── profile_03.png
└── non_matches/
    ├── profile_04.png
    └── profile_05.png
```

## 🤖 Using the Classifier in Code

```python
from src.analyzers.dating_classifier import DatingClassifier

# Initialize
classifier = DatingClassifier('config/preferences.json')

# Classify a screenshot
result = classifier.classify_screenshot('path/to/screenshot.png')

# Check if match
if result.is_match:
    print(f"Match! Confidence: {result.confidence_score:.1%}")
    print(f"Reasons: {result.reasons}")
else:
    print(f"Not a match ({result.confidence_score:.1%})")

# Access component scores
print(f"Physical: {result.component_scores['physical']:.1%}")
print(f"Personality: {result.component_scores['personality']:.1%}")
print(f"Interests: {result.component_scores['interests']:.1%}")

# Batch processing
results = classifier.batch_classify([
    'screenshot1.png',
    'screenshot2.png',
    'screenshot3.png'
])

# Export results
import json
with open('results.json', 'w') as f:
    json.dump([r.to_dict() for r in results], f, indent=2)
```

## 📈 Improving Accuracy

### 1. Add More Reference Images

The more reference images you provide, the better:

```bash
python preference_cli.py
# Add 10-20 reference images of people you find attractive
```

### 2. Add Training Examples

Save screenshots to training directories:

```bash
# Profiles you liked
cp good_profile.png config/liked_profiles/

# Profiles you didn't like
cp bad_profile.png config/disliked_profiles/
```

### 3. Tune Keywords

Update `bio_keywords` in preferences.json:

```json
{
  "bio_keywords": {
    "positive": ["your", "specific", "interests"],
    "negative": ["dealbreakers", "red", "flags"]
  }
}
```

### 4. Adjust Thresholds

Lower threshold for more matches:
```json
{"matching_criteria": {"minimum_score": 0.55}}
```

Higher threshold for only best matches:
```json
{"matching_criteria": {"minimum_score": 0.75}}
```

## 🔍 Instagram Pipeline Workflow

### 1. Search by Hashtag

```bash
python instagram_classifier_pipeline.py --query "#hiking" --limit 30
```

### 2. Search by Location

```bash
python instagram_classifier_pipeline.py --query "New York" --limit 20
```

### 3. Review Results

```bash
# List all result sessions
python instagram_classifier_pipeline.py --list-results

# Analyze specific session
python instagram_classifier_pipeline.py --analyze data/instagram_results/matches_20241009_140530.json
```

### 4. Export Matches

Results are saved to `data/instagram_results/` as JSON files containing:
- Profile information (username, bio, URL)
- Classification results
- Screenshot paths
- Timestamps

## 🛠️ Troubleshooting

### OCR Not Working

If text extraction fails:

1. **Install Tesseract**:
   ```bash
   brew install tesseract  # macOS
   ```

2. **Verify Installation**:
   ```bash
   tesseract --version
   ```

### Poor Classification Accuracy

If accuracy is low (<60%):

1. **Add more reference images** (10-20 recommended)
2. **Add training examples** to liked/disliked folders
3. **Check preference weights** match your priorities
4. **Review misclassified examples** using error analysis

### Instagram Scraper Issues

If Instagram scraping fails:

1. **Run in non-headless mode**: Edit `instagram_scraper.py`, set `headless=False`
2. **Check rate limiting**: Add delays between requests
3. **Update selectors**: Instagram may have changed their HTML
4. **Use manual screenshots**: Take screenshots yourself and use demo classifier

### Low Scores for Good Matches

If you're seeing low scores for profiles you like:

1. **Lower the threshold**:
   ```json
   {"matching_criteria": {"minimum_score": 0.5}}
   ```

2. **Adjust weights**: Increase weight for aspects that matter most
3. **Add more examples**: Your preferences may not be well-defined yet

## 📚 Command Reference

### Demo Classifier

```bash
# Interactive mode
python demo_classifier.py --mode interactive

# Single screenshot
python demo_classifier.py --mode single --screenshot path/to/image.png

# Batch processing
python demo_classifier.py --mode batch --directory path/to/screenshots/

# Export results
python demo_classifier.py --mode batch --directory path/to/screenshots/ --export results.json

# Show classifier info
python demo_classifier.py --mode info
```

### Evaluation

```bash
# Create dataset structure
python evaluate_classifier.py --create-dataset

# Evaluate
python evaluate_classifier.py --dataset data/test_profiles/

# With error analysis
python evaluate_classifier.py --error-analysis

# Export metrics
python evaluate_classifier.py --export metrics.json
```

### Instagram Pipeline

```bash
# Search and classify
python instagram_classifier_pipeline.py --query "fitness" --limit 20

# Custom match threshold
python instagram_classifier_pipeline.py --query "yoga" --limit 30 --min-score 0.7

# List saved results
python instagram_classifier_pipeline.py --list-results

# Analyze results
python instagram_classifier_pipeline.py --analyze data/instagram_results/matches_*.json
```

### Preferences

```bash
# Interactive setup
python preference_cli.py

# View current preferences
python preference_cli.py --show

# Add reference images
python preference_cli.py --add-images image1.jpg image2.jpg

# Export preferences
python preference_cli.py --export my_prefs.json

# Import preferences
python preference_cli.py --import my_prefs.json
```

## 🎓 Next Steps

### For Testing

1. Collect 20-30 profile screenshots from Instagram/dating apps
2. Label them as matches/non-matches
3. Run evaluation to measure accuracy
4. Iterate on preferences and weights

### For Production

1. Build larger training dataset (100+ examples)
2. Fine-tune ResNet on your specific preferences
3. Implement real-time screenshot capture
4. Add automated messaging (Phase 2)
5. Integrate calendar for date scheduling (Phase 3)

## 💡 Tips & Best Practices

1. **Start conservative**: Use high threshold (0.7+) initially
2. **Review matches manually**: Don't trust the AI blindly
3. **Update preferences regularly**: As you see results
4. **Use diverse reference images**: Different angles, settings, expressions
5. **Be specific with keywords**: Generic terms don't help much
6. **Respect privacy**: Don't share or misuse classified profiles
7. **Follow platform ToS**: Be aware of Instagram/dating app policies

## 📞 Support

For issues or questions:
1. Check this guide
2. Review code comments
3. Check logs in `logs/` directory
4. Run with `--help` flag for command details

## 🔐 Privacy & Ethics

- All data is stored locally
- No data is sent to external services (except LLM APIs for future messaging)
- Respect people's privacy - don't share classified results
- Use responsibly and ethically
- Follow platform Terms of Service

---

**Happy matching! 🎉**
