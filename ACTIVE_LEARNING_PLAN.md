# Active Learning & CLIP Integration Plan

## Overview
Transform the Dating Wizard from a static ResNet50 similarity matcher into an adaptive learning system using CLIP and user feedback.

## Current System Problems
- ❌ ResNet50 trained on ImageNet (objects, not faces)
- ❌ No learning from user feedback
- ❌ Simple keyword matching for text
- ❌ Can't understand semantic concepts ("athletic", "artistic vibe")

## Proposed Solution

### Phase 1: Database Schema & Feedback Collection ✅ COMPLETED
**Status**: Schema added to `backend/database/models.py`

**New Tables**:
1. **ModelVersion** - Tracks each version of the model
   - version_number, model_type, model_path
   - Training metrics (accuracy, samples)
   - Performance metrics (likes, dislikes, super_likes)
   - is_active flag

2. **TrainingJob** - Tracks training progress
   - Status (pending/running/completed/failed)
   - Hyperparameters (epochs, batch_size, learning_rate)
   - Progress (current_epoch, current_loss, current_accuracy)

3. **ClassificationResult** (updated)
   - Added: model_version_id, user_feedback, feedback_at

### Phase 2: CLIP Integration
**Why CLIP?**
- ✅ Understands both images AND text
- ✅ Can match "athletic build" or "artistic vibe" without training
- ✅ Pre-trained on 400M image-text pairs
- ✅ Runs well on Mac CPU (~1-2 seconds per image with ViT-B/32)
- ✅ Better features than ResNet50 for faces/people

**Implementation**:
```python
import torch
from transformers import CLIPProcessor, CLIPModel

# Load CLIP ViT-B/32 (150MB, fast on CPU)
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# For image similarity (like current ResNet)
image_features = model.get_image_features(pixel_values=inputs)

# NEW: For semantic matching
text = ["athletic build", "artistic vibe", "outdoorsy person"]
text_features = model.get_text_features(input_ids=text_inputs)
similarity = cosine_similarity(image_features, text_features)
```

**Benefits**:
- Can use text descriptions of preferences instead of just keywords
- Better visual features for people/faces
- Zero-shot semantic understanding

### Phase 3: Feedback UI
**Add to Classification Results Page**:
```typescript
// Three feedback buttons
<div className="feedback-buttons">
  <button onClick={() => handleFeedback('like')}>👍 Like</button>
  <button onClick={() => handleFeedback('dislike')}>👎 Dislike</button>
  <button onClick={() => handleFeedback('super_like')}>⭐ Super Like</button>
</div>
```

**Backend API**:
```python
@router.post("/results/{result_id}/feedback")
async def submit_feedback(result_id: int, feedback: str):
    # Update classification_result.user_feedback
    # Update classification_result.feedback_at
    # Update model_version performance metrics
```

### Phase 4: Active Learning Loop

**Trigger Training When**:
- User manually clicks "Train Model" button
- OR Automatically after N feedbacks (e.g., every 50 likes/dislikes)

**Training Pipeline**:

```python
class ModelTrainer:
    def __init__(self, model_version_id):
        self.base_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.version_id = model_version_id

    def prepare_training_data(self):
        # Fetch all ClassificationResults with user_feedback
        likes = db.query(ClassificationResult).filter_by(user_feedback='like').all()
        dislikes = db.query(ClassificationResult).filter_by(user_feedback='dislike').all()
        super_likes = db.query(ClassificationResult).filter_by(user_feedback='super_like').all()

        # Create dataset
        positive_samples = [(r.screenshot_path, 1) for r in likes + super_likes]
        negative_samples = [(r.screenshot_path, 0) for r in dislikes]

        return positive_samples + negative_samples

    def fine_tune(self, epochs=10, batch_size=16):
        # Fine-tune last 2 layers of CLIP vision encoder
        for param in self.base_model.parameters():
            param.requires_grad = False

        # Unfreeze last 2 transformer blocks
        for param in self.base_model.vision_model.encoder.layers[-2:].parameters():
            param.requires_grad = True

        # Add classification head
        self.classifier = nn.Linear(512, 2)  # binary: like/dislike

        # Train with BCE loss
        optimizer = torch.optim.AdamW(trainable_params, lr=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)

        # Training loop...
```

### Phase 5: Model Versioning

**Version Management**:
1. **Initial Version (v1)**: Base CLIP model (no training)
2. **Fine-tuned Versions (v2+)**: Trained on user feedback

**Switching Versions**:
```python
# Set active version
@router.post("/models/versions/{version_id}/activate")
async def activate_model_version(version_id: int):
    # Deactivate current
    db.query(ModelVersion).update({is_active: False})
    # Activate new
    db.query(ModelVersion).filter_by(id=version_id).update({is_active: True})
    # Reload classifier service
    classifier_service.reload_classifier()
```

**Rollback Support**:
- Each version saves model weights to `models/version_{N}.pt`
- User can revert to any previous version
- Compare performance metrics side-by-side

### Phase 6: Performance Tracking

**Dashboard UI**:
```typescript
<ModelVersionsTable>
  <tr>
    <td>v1 (Base CLIP)</td>
    <td>0 samples</td>
    <td>-</td>
    <td>245 predictions</td>
    <td>65% like rate</td>
    <td><button>Activate</button></td>
  </tr>
  <tr className="active">
    <td>v2 (Fine-tuned)</td>
    <td>120 samples</td>
    <td>87% accuracy</td>
    <td>89 predictions</td>
    <td>78% like rate</td>
    <td><button disabled>Active</button></td>
  </tr>
</ModelVersionsTable>
```

**Metrics to Track**:
- **Training Metrics**: accuracy, loss, validation accuracy
- **Usage Metrics**: total predictions, likes, dislikes, super_likes
- **Performance**: like_rate = likes / (likes + dislikes)
- **Improvement**: Compare like_rate between versions

## Implementation Timeline

### Sprint 1: Foundation (Current)
✅ Database schema for model versioning
🔄 Pydantic schemas
⏳ Migration script

### Sprint 2: CLIP Integration
⏳ Install CLIP dependencies (`transformers`, `torch`)
⏳ Create CLIPClassifier class
⏳ Add model switching logic
⏳ Test performance on Mac

### Sprint 3: Feedback Loop
⏳ Add feedback buttons to UI
⏳ Create feedback API endpoints
⏳ Update model version metrics
⏳ Test feedback flow

### Sprint 4: Training Pipeline
⏳ Implement ModelTrainer class
⏳ Create training job queue
⏳ Add "Train Model" button
⏳ Show training progress

### Sprint 5: Versioning & Dashboard
⏳ Model version management UI
⏳ Performance comparison dashboard
⏳ Version activation/rollback
⏳ Export/import models

## Technical Considerations

### Mac Performance
- **CLIP ViT-B/32**: ~150MB, 1-2 sec/image on CPU
- **CLIP ViT-L/14**: ~900MB, 3-4 sec/image (better quality)
- Recommendation: Start with ViT-B/32

### Training Requirements
- **Minimum samples**: 50-100 per class (liked/disliked)
- **Training time**: 5-10 minutes on Mac M1/M2 for 10 epochs
- **Storage**: ~200MB per model version

### Edge Cases
- What if user has no feedback yet? → Use base CLIP model
- What if training fails? → Keep previous version active, log error
- What if user deletes feedback? → Retrain with updated dataset

## Success Metrics
- **Accuracy**: Fine-tuned model achieves >75% accuracy
- **User satisfaction**: Like rate improves by 15%+ after training
- **Speed**: Training completes in <10 minutes
- **Stability**: Model versions can be switched without errors

## Next Steps
1. ✅ Review this plan
2. Create Pydantic schemas for new models
3. Add migration for new database tables
4. Install CLIP dependencies
5. Implement CLIP classifier
6. Add feedback buttons to UI

Would you like to proceed with this plan?
