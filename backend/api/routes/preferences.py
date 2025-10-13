"""
Preference Management API Endpoints
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
from pathlib import Path

from backend.database.db import get_db
from backend.database.models import (
    ReferenceImage, Preference, BioKeyword,
    PersonalityTrait, SharedInterest
)
from backend.models.schemas import (
    ReferenceImageResponse, PreferenceResponse, PreferenceUpdate,
    KeywordCreate, KeywordResponse, TraitCreate, TraitResponse,
    InterestCreate, InterestResponse
)
from backend.services.classifier_service import get_classifier_service
from backend.config import settings

router = APIRouter(prefix="/preferences", tags=["preferences"])


# Reference Images
@router.post("/reference-images", response_model=ReferenceImageResponse)
async def upload_reference_image(
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a reference image for physical preference matching"""

    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save file
    file_path = settings.REFERENCE_IMAGES_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create thumbnail
    classifier_service = get_classifier_service()
    thumbnail_path = classifier_service.create_thumbnail(str(file_path))

    # Save to database
    db_image = ReferenceImage(
        file_path=str(file_path),
        thumbnail_path=thumbnail_path,
        category=category,
        description=description
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    # Reload classifier to include new image
    classifier_service.reload_classifier()

    return db_image


@router.get("/reference-images", response_model=List[ReferenceImageResponse])
async def list_reference_images(db: Session = Depends(get_db)):
    """List all reference images"""
    return db.query(ReferenceImage).all()


@router.delete("/reference-images/{image_id}")
async def delete_reference_image(image_id: int, db: Session = Depends(get_db)):
    """Delete a reference image"""
    image = db.query(ReferenceImage).filter(ReferenceImage.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete files
    try:
        if Path(image.file_path).exists():
            Path(image.file_path).unlink()
        if image.thumbnail_path and Path(image.thumbnail_path).exists():
            Path(image.thumbnail_path).unlink()
    except Exception as e:
        print(f"Error deleting files: {e}")

    # Delete from database
    db.delete(image)
    db.commit()

    # Reload classifier
    classifier_service = get_classifier_service()
    classifier_service.reload_classifier()

    return {"message": "Image deleted successfully"}


# Preferences
@router.get("/", response_model=PreferenceResponse)
async def get_preferences(db: Session = Depends(get_db)):
    """Get current preferences"""
    pref = db.query(Preference).first()

    if not pref:
        # Create default preferences
        pref = Preference()
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return pref


@router.put("/", response_model=PreferenceResponse)
async def update_preferences(
    updates: PreferenceUpdate,
    db: Session = Depends(get_db)
):
    """Update preferences"""
    pref = db.query(Preference).first()

    if not pref:
        pref = Preference()
        db.add(pref)

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pref, field, value)

    db.commit()
    db.refresh(pref)

    # Note: No need to reload classifier for weight changes
    # Weights are read from DB on each classification
    # Only reload when reference images or traits/interests change

    return pref


# Bio Keywords
@router.post("/keywords", response_model=KeywordResponse)
async def add_keyword(keyword: KeywordCreate, db: Session = Depends(get_db)):
    """Add a bio keyword"""
    db_keyword = BioKeyword(**keyword.model_dump())
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)

    # Reload classifier
    get_classifier_service().reload_classifier()

    return db_keyword


@router.get("/keywords", response_model=List[KeywordResponse])
async def list_keywords(db: Session = Depends(get_db)):
    """List all bio keywords"""
    return db.query(BioKeyword).all()


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Delete a bio keyword"""
    keyword = db.query(BioKeyword).filter(BioKeyword.id == keyword_id).first()

    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    db.delete(keyword)
    db.commit()

    # Reload classifier
    get_classifier_service().reload_classifier()

    return {"message": "Keyword deleted successfully"}


# Personality Traits
@router.post("/traits", response_model=TraitResponse)
async def add_trait(trait: TraitCreate, db: Session = Depends(get_db)):
    """Add a personality trait"""
    db_trait = PersonalityTrait(**trait.model_dump())
    db.add(db_trait)
    db.commit()
    db.refresh(db_trait)

    # Reload classifier
    get_classifier_service().reload_classifier()

    return db_trait


@router.get("/traits", response_model=List[TraitResponse])
async def list_traits(db: Session = Depends(get_db)):
    """List all personality traits"""
    return db.query(PersonalityTrait).all()


@router.delete("/traits/{trait_id}")
async def delete_trait(trait_id: int, db: Session = Depends(get_db)):
    """Delete a personality trait"""
    trait = db.query(PersonalityTrait).filter(PersonalityTrait.id == trait_id).first()

    if not trait:
        raise HTTPException(status_code=404, detail="Trait not found")

    db.delete(trait)
    db.commit()

    # Reload classifier
    get_classifier_service().reload_classifier()

    return {"message": "Trait deleted successfully"}


# Shared Interests
@router.post("/interests", response_model=InterestResponse)
async def add_interest(interest: InterestCreate, db: Session = Depends(get_db)):
    """Add a shared interest"""
    db_interest = SharedInterest(**interest.model_dump())
    db.add(db_interest)
    db.commit()
    db.refresh(db_interest)

    # Reload classifier
    get_classifier_service().reload_classifier()

    return db_interest


@router.get("/interests", response_model=List[InterestResponse])
async def list_interests(db: Session = Depends(get_db)):
    """List all shared interests"""
    return db.query(SharedInterest).all()


@router.delete("/interests/{interest_id}")
async def delete_interest(interest_id: int, db: Session = Depends(get_db)):
    """Delete a shared interest"""
    interest = db.query(SharedInterest).filter(SharedInterest.id == interest_id).first()

    if not interest:
        raise HTTPException(status_code=404, detail="Interest not found")

    db.delete(interest)
    db.commit()

    # Reload classifier
    get_classifier_service().reload_classifier()

    return {"message": "Interest deleted successfully"}
