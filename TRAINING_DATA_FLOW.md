# Training Data Flow: How Embeddings Drive Model Learning

## Your Question
> "How is the classifier going to be trained exactly? Like I get that we're storing the ID, the score, and the feedback, but how is it going to correlate like, oh okay, this embedding I should optimize for? Should we be tracking the embeddings themselves, or are we going to use the IDs to go and compute the embedding?"

---

## The Answer: Embedding Storage Strategy

### Option 1: Recompute Embeddings On-The-Fly (Current Approach)
**What we're doing now:**
```
classification_results table:
├─ id: 52
├─ screenshot_path: "uploads/screenshots/profile_123.jpg"
├─ confidence_score: 0.85
├─ user_feedback: "super_like"
└─ created_at: "2025-10-13"

During training:
1. Load screenshot_path from database
2. Load image from disk
3. Compute CLIP embedding in real-time
4. Use embedding + feedback for training
```

**Pros:**
- ✅ Less storage (no embedding arrays in DB)
- ✅ Always uses latest CLIP model
- ✅ Simpler database schema

**Cons:**
- ❌ Slower training (must recompute embeddings)
- ❌ Requires keeping all images on disk
- ❌ Can't train if images are deleted

---

### Option 2: Pre-Compute and Store Embeddings (Recommended)
**What we should do:**
```sql
-- Add embedding column to classification_results
ALTER TABLE classification_results
ADD COLUMN image_embedding BLOB;  -- Store as binary numpy array

-- Or create separate table for embeddings
CREATE TABLE classification_embeddings (
    id INTEGER PRIMARY KEY,
    result_id INTEGER,
    embedding_type TEXT,  -- 'clip_image', 'clip_text', 'combined'
    embedding BLOB,  -- 512-dim vector for CLIP
    model_version_id INTEGER,
    created_at TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES classification_results(id)
);
```

**Storage format:**
```python
import numpy as np
import pickle

# After classification, store embedding
embedding = clip_model.encode_image(image)  # Shape: (512,)
embedding_bytes = pickle.dumps(embedding.numpy())

db_result.image_embedding = embedding_bytes
db.commit()

# During training, load embedding
embedding_bytes = db_result.image_embedding
embedding = pickle.loads(embedding_bytes)  # Back to numpy array
```

**Pros:**
- ✅ **Much faster training** (no re-computation)
- ✅ Can delete images after embedding extraction
- ✅ Can version embeddings (track which model created them)
- ✅ Enables fast similarity search

**Cons:**
- ❌ More storage (~2KB per embedding for CLIP)
- ❌ Slightly more complex schema

---

## How Training Actually Works

### Step-by-Step Training Flow

#### 1. **Data Collection** (What we're doing now)
```python
# User classifies a profile and gives feedback
classification = ClassificationResult(
    screenshot_path="profile_123.jpg",
    confidence_score=0.85,
    user_feedback="super_like",  # CRITICAL: This is the label!
    model_version_id=1
)

# The feedback becomes our training label:
# "super_like" = positive example (label = 1)
# "like" = positive example (label = 1)
# "dislike" = negative example (label = 0)
```

#### 2. **Embedding Extraction** (During or after classification)
```python
from PIL import Image
import torch

# Load the image
image = Image.open("profile_123.jpg")

# Extract CLIP embedding (512-dimensional vector)
with torch.no_grad():
    image_features = clip_model.encode_image(
        clip_processor(images=image, return_tensors="pt")["pixel_values"]
    )
    # image_features shape: (1, 512)

# This embedding is a dense representation of the image
# Similar images have similar embeddings (high cosine similarity)
```

#### 3. **Build Training Dataset**
```python
def prepare_training_data(db: Session):
    """Load all feedback examples as training data"""

    # Get all classifications with feedback
    results = db.query(ClassificationResult).filter(
        ClassificationResult.user_feedback.isnot(None)
    ).all()

    embeddings = []
    labels = []

    for result in results:
        # Option A: Load from stored embedding
        if result.image_embedding:
            embedding = pickle.loads(result.image_embedding)

        # Option B: Recompute from image
        else:
            image = Image.open(result.screenshot_path)
            embedding = extract_clip_embedding(image)

        embeddings.append(embedding)

        # Convert feedback to binary label
        label = 1 if result.user_feedback in ['like', 'super_like'] else 0
        labels.append(label)

    X = np.array(embeddings)  # Shape: (N, 512)
    y = np.array(labels)      # Shape: (N,)

    return X, y
```

#### 4. **Fine-Tune CLIP Model**

There are **two main approaches**:

##### Approach A: Train a Classification Head (Faster, Recommended)
```python
"""
Keep CLIP frozen, train only a small neural network on top
"""
import torch.nn as nn

class CLIPClassifier(nn.Module):
    def __init__(self, clip_model):
        super().__init__()
        self.clip = clip_model

        # Freeze CLIP weights
        for param in self.clip.parameters():
            param.requires_grad = False

        # Add trainable classification head
        self.classifier = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),  # Binary classification
            nn.Sigmoid()
        )

    def forward(self, images):
        # Extract CLIP embeddings (frozen)
        with torch.no_grad():
            embeddings = self.clip.encode_image(images)

        # Classify with trainable head
        scores = self.classifier(embeddings)
        return scores

# Training loop
model = CLIPClassifier(clip_model)
optimizer = torch.optim.Adam(model.classifier.parameters(), lr=0.001)
criterion = nn.BCELoss()

for epoch in range(10):
    for batch_embeddings, batch_labels in dataloader:
        optimizer.zero_grad()

        predictions = model(batch_embeddings)
        loss = criterion(predictions, batch_labels)

        loss.backward()
        optimizer.step()
```

**Why this works:**
- CLIP embeddings capture visual features
- Classification head learns: "If embedding looks like THIS, user likes it"
- Much faster than fine-tuning full CLIP
- Requires less data (~50-100 examples)

---

##### Approach B: Fine-Tune Entire CLIP (Better, but slower)
```python
"""
Use contrastive learning to fine-tune CLIP itself
"""
from transformers import CLIPModel, CLIPProcessor

# Unfreeze CLIP for fine-tuning
for param in clip_model.parameters():
    param.requires_grad = True

# Contrastive loss: pull liked images together, push disliked away
def contrastive_loss(embeddings, labels):
    """
    Make embeddings of liked profiles similar to each other
    Make embeddings of liked/disliked profiles dissimilar
    """
    positive_mask = labels == 1
    negative_mask = labels == 0

    # Anchor: random liked profile
    anchor = embeddings[positive_mask][0]

    # Positive: other liked profiles
    positives = embeddings[positive_mask][1:]

    # Negative: disliked profiles
    negatives = embeddings[negative_mask]

    # Loss: maximize similarity to positives, minimize to negatives
    pos_sim = torch.cosine_similarity(anchor, positives)
    neg_sim = torch.cosine_similarity(anchor, negatives)

    loss = -torch.log(pos_sim / (pos_sim + neg_sim))
    return loss.mean()

# Training
optimizer = torch.optim.Adam(clip_model.parameters(), lr=1e-5)

for epoch in range(5):
    for images, labels in dataloader:
        optimizer.zero_grad()

        # Extract embeddings with trainable CLIP
        embeddings = clip_model.encode_image(images)

        loss = contrastive_loss(embeddings, labels)
        loss.backward()
        optimizer.step()
```

**Why this works:**
- CLIP learns YOUR specific visual preferences
- Liked profiles cluster together in embedding space
- Disliked profiles pushed away
- Requires more data (~200+ examples)

---

## Recommended Strategy: Hybrid Approach

### Phase 1: Start with Classification Head (Weeks 1-2)
```python
# Fast MVP training
# Requires: 50-100 feedback examples
# Training time: 5-10 minutes
# Accuracy: 70-80%

1. Collect 50+ feedback examples
2. Extract CLIP embeddings (store in DB)
3. Train simple classifier head
4. Deploy new model version
5. A/B test against baseline
```

### Phase 2: Fine-Tune CLIP (Month 1-2)
```python
# Advanced training
# Requires: 200+ feedback examples
# Training time: 1-2 hours
# Accuracy: 85-95%

1. Collect 200+ feedback examples
2. Fine-tune CLIP with contrastive learning
3. Save fine-tuned model weights
4. Deploy as new model version
5. Monitor performance improvement
```

---

## Embedding Storage Implementation

### Database Migration
```python
# Add embedding storage to existing schema
"""
Migration: Add embedding column
"""
def upgrade():
    op.add_column(
        'classification_results',
        sa.Column('image_embedding', sa.LargeBinary(), nullable=True)
    )

    op.add_column(
        'classification_results',
        sa.Column('text_embedding', sa.LargeBinary(), nullable=True)
    )
```

### Save Embedding During Classification
```python
# In backend/services/classifier_service.py

def classify_screenshot(self, screenshot_path: str):
    # ... existing classification code ...

    # Extract and store embedding
    image = Image.open(screenshot_path)
    embedding = self._extract_clip_embedding(image)

    # Serialize embedding
    embedding_bytes = pickle.dumps(embedding.cpu().numpy())

    # Save to database
    db_result.image_embedding = embedding_bytes
    db.commit()

    return result

def _extract_clip_embedding(self, image):
    """Extract 512-dim CLIP embedding"""
    with torch.no_grad():
        inputs = self.processor(images=image, return_tensors="pt")
        embedding = self.model.get_image_features(**inputs)
        # Normalize embedding (important for cosine similarity)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    return embedding
```

### Load Embeddings for Training
```python
def load_training_data(db: Session):
    """Load embeddings and labels for training"""

    results = db.query(ClassificationResult).filter(
        ClassificationResult.user_feedback.isnot(None),
        ClassificationResult.image_embedding.isnot(None)
    ).all()

    embeddings = []
    labels = []

    for result in results:
        # Deserialize embedding
        embedding = pickle.loads(result.image_embedding)
        embeddings.append(embedding)

        # Map feedback to label
        label = 1 if result.user_feedback in ['like', 'super_like'] else 0
        labels.append(label)

    return np.array(embeddings), np.array(labels)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ 1. User Interaction                                     │
├─────────────────────────────────────────────────────────┤
│ User uploads profile → CLIP classifies → Shows result  │
│ User clicks "Super Like" (feedback = label)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Data Storage                                         │
├─────────────────────────────────────────────────────────┤
│ classification_results:                                 │
│   - screenshot_path: "profile_123.jpg"                  │
│   - image_embedding: <512-dim vector as bytes>         │
│   - user_feedback: "super_like" (LABEL)                │
│   - confidence_score: 0.85                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Training Pipeline (Triggered after N feedbacks)     │
├─────────────────────────────────────────────────────────┤
│ Load embeddings from database:                          │
│   X = [embedding_1, embedding_2, ..., embedding_N]     │
│   y = [1, 0, 1, ...]  # 1=like, 0=dislike              │
│                                                          │
│ Train model:                                            │
│   model.fit(X, y)                                       │
│                                                          │
│ Save new model version:                                 │
│   model_versions.version_number = 2                     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Model Deployment                                     │
├─────────────────────────────────────────────────────────┤
│ New model predicts:                                     │
│   embedding_new = extract_embedding(new_profile)        │
│   score_new = model.predict(embedding_new)              │
│                                                          │
│ Model has learned:                                      │
│   "Profiles with embeddings similar to liked examples   │
│    should score higher"                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Storage Requirements

### Per-Image Storage Calculation
```python
# CLIP embedding: 512 dimensions × 4 bytes (float32) = 2,048 bytes = 2KB

# For 1,000 classified profiles:
1000 profiles × 2KB = 2MB embeddings

# For 10,000 classified profiles:
10,000 profiles × 2KB = 20MB embeddings

# Totally manageable! SQLite can handle this easily.
```

### Image Storage (Bigger concern)
```python
# Screenshot: ~500KB per image (compressed JPEG)

# For 1,000 profiles:
1000 × 500KB = 500MB

# For 10,000 profiles:
10,000 × 500KB = 5GB

# Solution: After embedding extraction, optionally delete images
# Keep only embeddings for training
```

---

## Summary: Embedding Strategy

### ✅ Recommended Approach

**Store embeddings in database:**
1. Add `image_embedding` BLOB column to `classification_results`
2. Extract and store embedding during classification
3. Use stored embeddings for fast training
4. Optionally delete images after embedding extraction

**Training workflow:**
1. Collect feedback (labels)
2. Load embeddings from database
3. Train classifier head on embeddings
4. Deploy new model version
5. Repeat as more feedback accumulates

**Why this works:**
- Embeddings capture ALL visual information
- Feedback provides labels (like/dislike)
- Model learns pattern: "These embeddings → like, those embeddings → dislike"
- Future predictions use learned patterns

---

## Next Steps

1. **Immediate**: Add `image_embedding` column to database
2. **Week 1**: Modify classifier to save embeddings
3. **Week 2**: Implement training pipeline
4. **Month 1**: Fine-tune CLIP on your feedback data

