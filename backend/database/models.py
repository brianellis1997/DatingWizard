"""
SQLAlchemy Database Models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ReferenceImage(Base):
    """Reference images uploaded by user for physical preference matching"""
    __tablename__ = "reference_images"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    category = Column(String, default="general")  # face, body, style, general
    description = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Preference(Base):
    """User preferences for matching"""
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    physical_weight = Column(Float, default=0.6)
    personality_weight = Column(Float, default=0.3)
    interest_weight = Column(Float, default=0.1)
    min_score = Column(Float, default=0.6)
    super_like_score = Column(Float, default=0.85)
    age_min = Column(Integer, default=25)
    age_max = Column(Integer, default=35)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class BioKeyword(Base):
    """Keywords to match in profiles (positive/negative/required)"""
    __tablename__ = "bio_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False)
    keyword_type = Column(String, nullable=False)  # positive, negative, required


class PersonalityTrait(Base):
    """Desired personality traits"""
    __tablename__ = "personality_traits"

    id = Column(Integer, primary_key=True, index=True)
    trait = Column(String, nullable=False, unique=True)


class SharedInterest(Base):
    """Shared interests to look for"""
    __tablename__ = "shared_interests"

    id = Column(Integer, primary_key=True, index=True)
    interest = Column(String, nullable=False, unique=True)
    is_dealbreaker = Column(Boolean, default=False)


class ClassificationResult(Base):
    """Results of profile classification"""
    __tablename__ = "classification_results"

    id = Column(Integer, primary_key=True, index=True)
    screenshot_path = Column(String, nullable=False)
    is_match = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=False)
    physical_score = Column(Float)
    personality_score = Column(Float)
    interest_score = Column(Float)

    # Extracted data
    name = Column(String)
    age = Column(Integer)
    bio = Column(Text)

    # Active learning fields
    model_version_id = Column(Integer, ForeignKey("model_versions.id"))
    user_feedback = Column(String)  # 'like', 'dislike', 'super_like', None

    # Embedding storage for training
    image_embedding = Column(LargeBinary)  # CLIP image embedding (512-dim vector)
    text_embedding = Column(LargeBinary)   # CLIP text embedding (512-dim vector)
    embedding_model_version = Column(String)  # Which model created embeddings

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    feedback_at = Column(DateTime(timezone=True))

    # Relationships
    reasons = relationship("ClassificationReason", back_populates="result", cascade="all, delete-orphan")
    model_version = relationship("ModelVersion", back_populates="classifications")


class ClassificationReason(Base):
    """Reasons for classification decision"""
    __tablename__ = "classification_reasons"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("classification_results.id"), nullable=False)
    reason = Column(Text, nullable=False)

    # Relationships
    result = relationship("ClassificationResult", back_populates="reasons")


class InstagramSearch(Base):
    """Instagram search sessions"""
    __tablename__ = "instagram_searches"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, nullable=False)
    limit = Column(Integer, default=20)
    min_score = Column(Float, default=0.6)
    total_found = Column(Integer, default=0)
    matches_found = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    results = relationship("InstagramResult", back_populates="search", cascade="all, delete-orphan")


class InstagramResult(Base):
    """Instagram profile results"""
    __tablename__ = "instagram_results"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("instagram_searches.id"), nullable=True)  # Nullable for single username scrapes
    classification_result_id = Column(Integer, ForeignKey("classification_results.id"))

    # Instagram data
    username = Column(String, nullable=False)
    name = Column(String)
    bio = Column(Text)
    url = Column(String)
    followers = Column(Integer)
    profile_image_url = Column(String)

    # Screenshot and embeddings (for CLIP integration)
    screenshot_path = Column(String)
    image_embedding = Column(LargeBinary)  # CLIP image embedding (512-dim vector)
    embedding_model_version = Column(String)  # Which model created embeddings

    # Classification scores (denormalized for quick access)
    confidence_score = Column(Float)
    physical_score = Column(Float)
    personality_score = Column(Float)
    interest_score = Column(Float)
    is_match = Column(Boolean)

    # User feedback for training
    user_feedback = Column(String)  # 'like', 'dislike', 'super_like', None
    feedback_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search = relationship("InstagramSearch", back_populates="results")
    classification = relationship("ClassificationResult")


class ModelVersion(Base):
    """Tracks different versions of the classification model"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_number = Column(Integer, nullable=False, unique=True)
    model_type = Column(String, nullable=False)  # 'resnet50', 'clip', 'fine_tuned'
    model_path = Column(String)  # Path to saved model weights
    is_active = Column(Boolean, default=False)

    # Training metadata
    training_samples = Column(Integer, default=0)
    training_accuracy = Column(Float)
    validation_accuracy = Column(Float)

    # Performance metrics
    total_predictions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    super_likes = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    trained_at = Column(DateTime(timezone=True))

    # Relationships
    classifications = relationship("ClassificationResult", back_populates="model_version")


class TrainingJob(Base):
    """Tracks model training jobs"""
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"))
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'

    # Training parameters
    epochs = Column(Integer, default=10)
    batch_size = Column(Integer, default=32)
    learning_rate = Column(Float, default=0.001)

    # Progress tracking
    current_epoch = Column(Integer, default=0)
    current_loss = Column(Float)
    current_accuracy = Column(Float)

    # Results
    final_loss = Column(Float)
    final_accuracy = Column(Float)
    error_message = Column(Text)

    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
