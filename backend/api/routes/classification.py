"""
Classification API Endpoints
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
import shutil
from pathlib import Path

from backend.database.db import get_db
from backend.database.models import ClassificationResult, ClassificationReason, ModelVersion
from backend.models.schemas import (
    ClassificationResultResponse,
    BatchClassificationRequest,
    BatchClassificationResponse
)
from backend.services.classifier_service import get_classifier_service
from backend.config import settings

router = APIRouter(prefix="/classify", tags=["classification"])


@router.post("/screenshot", response_model=ClassificationResultResponse)
async def classify_screenshot(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Classify a single profile screenshot"""

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save file
    file_path = settings.SCREENSHOTS_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Get active model version
    active_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()

    # Classify
    classifier_service = get_classifier_service()
    result = classifier_service.classify_screenshot(str(file_path))

    # Extract CLIP embedding for storage
    import pickle
    image_embedding = None
    embedding_model_version = None

    if hasattr(classifier_service.classifier, 'extract_embedding'):
        embedding = classifier_service.classifier.extract_embedding(str(file_path))
        if embedding is not None:
            image_embedding = pickle.dumps(embedding)
            embedding_model_version = "openai/clip-vit-base-patch32"

    # Save to database
    db_result = ClassificationResult(
        screenshot_path=str(file_path),
        is_match=result.is_match,
        confidence_score=result.confidence_score,
        physical_score=result.component_scores['physical'],
        personality_score=result.component_scores['personality'],
        interest_score=result.component_scores['interests'],
        name=result.extracted_data.get('name'),
        age=result.extracted_data.get('age'),
        bio=result.extracted_data.get('bio'),
        model_version_id=active_model.id if active_model else None,
        image_embedding=image_embedding,
        embedding_model_version=embedding_model_version
    )
    db.add(db_result)
    db.flush()

    # Save reasons
    for reason_text in result.reasons:
        reason = ClassificationReason(result_id=db_result.id, reason=reason_text)
        db.add(reason)

    db.commit()
    db.refresh(db_result)

    return db_result


@router.post("/batch", response_model=BatchClassificationResponse)
async def classify_batch(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Classify multiple profile screenshots"""

    # Save all files
    file_paths = []
    for file in files:
        if not file.content_type.startswith("image/"):
            continue

        file_path = settings.SCREENSHOTS_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_paths.append(str(file_path))

    # Get active model version
    active_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()

    # Classify batch
    classifier_service = get_classifier_service()
    results = classifier_service.classify_batch(file_paths)

    # Save to database
    db_results = []
    matches = 0

    for result in results:
        db_result = ClassificationResult(
            screenshot_path=result.metadata['screenshot_path'],
            is_match=result.is_match,
            confidence_score=result.confidence_score,
            physical_score=result.component_scores['physical'],
            personality_score=result.component_scores['personality'],
            interest_score=result.component_scores['interests'],
            name=result.extracted_data.get('name'),
            age=result.extracted_data.get('age'),
            bio=result.extracted_data.get('bio'),
            model_version_id=active_model.id if active_model else None
        )
        db.add(db_result)
        db.flush()

        # Save reasons
        for reason_text in result.reasons:
            reason = ClassificationReason(result_id=db_result.id, reason=reason_text)
            db.add(reason)

        db_results.append(db_result)
        if result.is_match:
            matches += 1

    db.commit()

    # Refresh all results
    for db_result in db_results:
        db.refresh(db_result)

    return {
        "total": len(files),
        "processed": len(results),
        "matches": matches,
        "results": db_results
    }


@router.get("/results/{result_id}", response_model=ClassificationResultResponse)
async def get_result(result_id: int, db: Session = Depends(get_db)):
    """Get a specific classification result"""
    result = db.query(ClassificationResult).filter(ClassificationResult.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return result
