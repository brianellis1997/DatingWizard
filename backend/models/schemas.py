"""
Pydantic schemas for API validation and serialization
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


# Reference Images
class ReferenceImageCreate(BaseModel):
    category: str = "general"
    description: Optional[str] = None


class ReferenceImageResponse(BaseModel):
    id: int
    file_path: str
    thumbnail_path: Optional[str]
    category: str
    description: Optional[str]
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Preferences
class PreferenceWeights(BaseModel):
    physical_weight: float = Field(ge=0, le=1, default=0.6)
    personality_weight: float = Field(ge=0, le=1, default=0.3)
    interest_weight: float = Field(ge=0, le=1, default=0.1)


class PreferenceUpdate(BaseModel):
    physical_weight: Optional[float] = Field(None, ge=0, le=1)
    personality_weight: Optional[float] = Field(None, ge=0, le=1)
    interest_weight: Optional[float] = Field(None, ge=0, le=1)
    min_score: Optional[float] = Field(None, ge=0, le=1)
    super_like_score: Optional[float] = Field(None, ge=0, le=1)
    age_min: Optional[int] = Field(None, ge=18, le=100)
    age_max: Optional[int] = Field(None, ge=18, le=100)


class PreferenceResponse(BaseModel):
    id: int
    physical_weight: float
    personality_weight: float
    interest_weight: float
    min_score: float
    super_like_score: float
    age_min: int
    age_max: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Keywords and Traits
class KeywordCreate(BaseModel):
    keyword: str
    keyword_type: str = Field(pattern="^(positive|negative|required)$")


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    keyword_type: str

    model_config = ConfigDict(from_attributes=True)


class TraitCreate(BaseModel):
    trait: str


class TraitResponse(BaseModel):
    id: int
    trait: str

    model_config = ConfigDict(from_attributes=True)


class InterestCreate(BaseModel):
    interest: str
    is_dealbreaker: bool = False


class InterestResponse(BaseModel):
    id: int
    interest: str
    is_dealbreaker: bool

    model_config = ConfigDict(from_attributes=True)


# Classification
class ClassificationReasonResponse(BaseModel):
    id: int
    reason: str

    model_config = ConfigDict(from_attributes=True)


class ClassificationResultResponse(BaseModel):
    id: int
    screenshot_path: str
    is_match: bool
    confidence_score: float
    physical_score: float
    personality_score: float
    interest_score: float
    name: Optional[str]
    age: Optional[int]
    bio: Optional[str]
    created_at: datetime
    reasons: List[ClassificationReasonResponse] = []

    # Active learning fields
    model_version_id: Optional[int] = None
    user_feedback: Optional[str] = None
    feedback_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ClassificationResultCreate(BaseModel):
    screenshot_path: str
    is_match: bool
    confidence_score: float
    physical_score: float
    personality_score: float
    interest_score: float
    name: Optional[str] = None
    age: Optional[int] = None
    bio: Optional[str] = None
    reasons: List[str] = []


# Instagram
class InstagramSearchCreate(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.6, ge=0, le=1)


class InstagramResultResponse(BaseModel):
    id: int
    username: str
    name: Optional[str]
    bio: Optional[str]
    url: Optional[str]
    followers: Optional[int]
    profile_image_url: Optional[str]
    created_at: datetime
    classification: Optional[ClassificationResultResponse]

    model_config = ConfigDict(from_attributes=True)


class InstagramSearchResponse(BaseModel):
    id: int
    query: str
    limit: int
    min_score: float
    total_found: int
    matches_found: int
    created_at: datetime
    results: List[InstagramResultResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Stats
class ClassifierStats(BaseModel):
    reference_images: int
    positive_examples: int
    negative_examples: int
    total_training_data: int
    weights: PreferenceWeights
    min_score_threshold: float
    super_like_threshold: float


class ResultsStats(BaseModel):
    total_classified: int
    total_matches: int
    match_rate: float
    avg_confidence: float
    classifications_today: int
    matches_today: int


# Batch operations
class BatchClassificationRequest(BaseModel):
    screenshot_paths: List[str]


class BatchClassificationResponse(BaseModel):
    total: int
    processed: int
    matches: int
    results: List[ClassificationResultResponse]


# Active Learning & Model Versioning

# Feedback
class FeedbackSubmit(BaseModel):
    feedback: str = Field(..., pattern="^(like|dislike|super_like)$")


class FeedbackResponse(BaseModel):
    id: int
    user_feedback: str
    feedback_at: datetime
    model_version_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# Model Versions
class ModelVersionCreate(BaseModel):
    version_number: int
    model_type: str = Field(..., pattern="^(resnet50|clip|fine_tuned)$")
    model_path: Optional[str] = None


class ModelVersionResponse(BaseModel):
    id: int
    version_number: int
    model_type: str
    model_path: Optional[str]
    is_active: bool

    # Training metadata
    training_samples: int
    training_accuracy: Optional[float]
    validation_accuracy: Optional[float]

    # Performance metrics
    total_predictions: int
    likes: int
    dislikes: int
    super_likes: int

    created_at: datetime
    trained_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelVersionUpdate(BaseModel):
    is_active: Optional[bool] = None


class ModelVersionPerformance(BaseModel):
    version_id: int
    version_number: int
    model_type: str
    like_rate: float  # likes / (likes + dislikes)
    super_like_rate: float  # super_likes / total
    total_predictions: int
    is_active: bool


# Training Jobs
class TrainingJobCreate(BaseModel):
    epochs: int = Field(default=10, ge=1, le=100)
    batch_size: int = Field(default=16, ge=4, le=64)
    learning_rate: float = Field(default=0.0001, gt=0, lt=1)


class TrainingJobResponse(BaseModel):
    id: int
    model_version_id: Optional[int]
    status: str

    # Training parameters
    epochs: int
    batch_size: int
    learning_rate: float

    # Progress
    current_epoch: int
    current_loss: Optional[float]
    current_accuracy: Optional[float]

    # Results
    final_loss: Optional[float]
    final_accuracy: Optional[float]
    error_message: Optional[str]

    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingProgress(BaseModel):
    job_id: int
    status: str
    progress_percent: float  # 0-100
    current_epoch: int
    total_epochs: int
    current_loss: Optional[float]
    current_accuracy: Optional[float]
    eta_seconds: Optional[int]
