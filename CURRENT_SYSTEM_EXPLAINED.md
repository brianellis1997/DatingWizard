# Current Dating Wizard System - Technical Explanation

## What the Classifier Status Means

When you see the Dashboard showing:
- **Reference Images**: 3
- **Training Examples**: 3
- **Min Score**: 60%

Here's what it actually means:

### Reference Images
These are the photos you uploaded in the Preferences page. The system extracts **visual features** from each image using ResNet50.

**Not actually "training"** - just storing feature vectors for comparison.

### Training Examples
Misleading name! Should be called "Comparison Points"

Currently: `Reference Images + Positive Examples + Negative Examples`
- Positive Examples: Photos in `config/liked_profiles/` (legacy CLI feature)
- Negative Examples: Photos in `config/disliked_profiles/` (legacy CLI feature)

Since you're using the web UI, you only have Reference Images.

### Min Score Threshold
The minimum similarity score (0-100%) for a profile to be considered a "match"
- Default: 60%
- Adjustable in preferences

## How Classification Actually Works

### Step 1: Extract Text (OCR)
```python
# Uses Tesseract OCR
text = pytesseract.image_to_string(screenshot)
# Extracts: name, age, bio text
```

**Current Text Analysis**:
- Simple keyword matching
- Searches bio for your personality traits ("kind", "funny")
- Searches bio for your interests ("hiking", "cooking")
- No semantic understanding - just exact word matches

### Step 2: Visual Analysis (ResNet50)
```python
# Extract 2048-dimensional feature vector
screenshot_features = resnet50.extract_features(screenshot)

# Compare to your reference images using cosine similarity
similarities = []
for ref_image in reference_images:
    sim = cosine_similarity(screenshot_features, ref_image.features)
    similarities.append(sim)

# Average similarity
physical_score = mean(similarities)
```

**What ResNet50 Actually Does**:
- Pre-trained on ImageNet (1.2M images of objects: cats, dogs, cars, etc.)
- **NOT trained on faces or people!**
- Frozen weights - no learning happens
- Just compares: "How similar are these feature vectors?"

**Limitations**:
- Doesn't understand faces specifically
- Doesn't know what "athletic build" or "artistic vibe" means
- Can't connect visual features to semantic concepts
- Generic object features, not dating-specific

### Step 3: Calculate Final Score
```python
final_score = (
    physical_score * physical_weight +      # e.g., 0.5 * 0.6 = 0.30
    personality_score * personality_weight + # e.g., 0.4 * 0.3 = 0.12
    interest_score * interest_weight         # e.g., 0.6 * 0.1 = 0.06
)
# Result: 0.48 (48%) - NO MATCH if threshold is 60%
```

### Step 4: Generate Reasons
Based on score ranges:
- `physical_score >= 0.75` → "Strong visual similarity to your reference images"
- `0.50 <= physical_score < 0.75` → "Moderate visual compatibility"
- `physical_score < 0.35` → "Photos don't align with your visual preferences"

## Why It's Not Learning

### Current System is Zero-Shot
1. **ResNet50**: Weights are frozen, never updated
2. **No feedback loop**: When you classify profiles, it doesn't remember
3. **No personalization**: Doesn't adapt to your specific preferences
4. **Static comparison**: Always uses same reference image features

### What "Training" Would Actually Mean
True training would involve:
1. Collecting your likes/dislikes as labeled data
2. Fine-tuning the model weights to learn YOUR preferences
3. Model gets better at predicting what YOU like
4. Adapts to patterns you might not even know you have

**Example**:
- You like 20 profiles with "dark hair" → Model learns this pattern
- Even if you didn't specify "dark hair" as a trait
- Next classifications give higher scores to dark-haired profiles

## Current Workflow

```
Screenshot Upload
    ↓
OCR (Tesseract)
    ↓
Extract: name, age, bio
    ↓
ResNet50 Feature Extraction
    ↓
Cosine Similarity vs Reference Images
    ↓
Keyword Matching (personality/interests)
    ↓
Weighted Score Calculation
    ↓
Match/No Match Decision
    ↓
Display Results (NO FEEDBACK STORED)
```

## What's Missing for True Learning

1. **Feedback Collection**
   - ❌ No like/dislike buttons
   - ❌ Not storing which profiles you actually liked
   - ❌ Can't learn from your decisions

2. **Model Updates**
   - ❌ Weights never change
   - ❌ No fine-tuning pipeline
   - ❌ Same model for everyone (generic)

3. **Performance Tracking**
   - ❌ Don't know if model is getting better
   - ❌ No accuracy metrics
   - ❌ Can't compare versions

4. **Personalization**
   - ❌ Model doesn't adapt to you
   - ❌ Same feature extraction for all users
   - ❌ Generic similarity, not personalized preference

## Proposed Improvements (See ACTIVE_LEARNING_PLAN.md)

1. **Replace ResNet50 with CLIP**
   - Better visual features for faces
   - Understands text descriptions
   - Can match "athletic build" semantically

2. **Add Feedback Loop**
   - Like/dislike buttons on results
   - Store feedback in database
   - Use for model training

3. **Implement Fine-Tuning**
   - Train model on YOUR feedback
   - Gets better over time
   - Personalized to your preferences

4. **Version Management**
   - Track model improvements
   - Compare performance metrics
   - Rollback if new version is worse

## Performance Expectations

### Current System (ResNet50)
- **Speed**: ~0.5 seconds per classification
- **Accuracy**: Depends on reference image quality
- **Learning**: None - static forever

### Proposed System (CLIP + Fine-Tuning)
- **Speed**: ~1-2 seconds per classification
- **Accuracy**: Improves with feedback (target: 75-85%)
- **Learning**: Gets better every 50-100 feedbacks

## Summary

**Current System = Smart Photo Comparison**
- Like asking: "Does this person look similar to these reference photos?"
- Uses AI for feature extraction, but no learning
- Fast and simple, but limited

**Proposed System = Adaptive Preference Learning**
- Like asking: "Based on 100 people I've liked/disliked, would I like this person?"
- Uses AI to learn your preferences
- Slower initially, but gets smarter over time

The "Classifier Status" dashboard currently shows static metrics. With the active learning system, it would show:
- **Model Version**: v3 (Fine-tuned on 150 samples)
- **Like Rate**: 78% (model predictions you agreed with)
- **Training Accuracy**: 87%
- **Last Updated**: 2 days ago

Would you like me to start implementing the active learning system?
