"""
SQLAlchemy Database Models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
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

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reasons = relationship("ClassificationReason", back_populates="result", cascade="all, delete-orphan")


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
    search_id = Column(Integer, ForeignKey("instagram_searches.id"), nullable=False)
    classification_result_id = Column(Integer, ForeignKey("classification_results.id"))

    # Instagram data
    username = Column(String, nullable=False)
    name = Column(String)
    bio = Column(Text)
    url = Column(String)
    followers = Column(Integer)
    profile_image_url = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search = relationship("InstagramSearch", back_populates="results")
    classification = relationship("ClassificationResult")
