"""
Results and Statistics API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime, timedelta

from backend.database.db import get_db
from backend.database.models import ClassificationResult, ModelVersion
from backend.models.schemas import ClassificationResultResponse, ResultsStats, ClassifierStats, FeedbackSubmit
from backend.services.classifier_service import get_classifier_service
from loguru import logger

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/history", response_model=List[ClassificationResultResponse])
async def get_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    matches_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get classification history"""
    query = db.query(ClassificationResult)

    if matches_only:
        query = query.filter(ClassificationResult.is_match == True)

    return query.order_by(ClassificationResult.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/matches", response_model=List[ClassificationResultResponse])
async def get_matches(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all matches"""
    return db.query(ClassificationResult).filter(
        ClassificationResult.is_match == True
    ).order_by(ClassificationResult.created_at.desc()).offset(skip).limit(limit).all()


@router.delete("/{result_id}")
async def delete_result(result_id: int, db: Session = Depends(get_db)):
    """Delete a classification result"""
    result = db.query(ClassificationResult).filter(ClassificationResult.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    db.delete(result)
    db.commit()

    return {"message": "Result deleted successfully"}


@router.get("/stats/overview", response_model=ResultsStats)
async def get_results_stats(db: Session = Depends(get_db)):
    """Get results statistics"""
    total = db.query(func.count(ClassificationResult.id)).scalar()
    matches = db.query(func.count(ClassificationResult.id)).filter(
        ClassificationResult.is_match == True
    ).scalar()

    avg_confidence = db.query(func.avg(ClassificationResult.confidence_score)).scalar() or 0

    # Today's stats
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())

    today_total = db.query(func.count(ClassificationResult.id)).filter(
        ClassificationResult.created_at >= today_start
    ).scalar()

    today_matches = db.query(func.count(ClassificationResult.id)).filter(
        and_(
            ClassificationResult.created_at >= today_start,
            ClassificationResult.is_match == True
        )
    ).scalar()

    return {
        "total_classified": total,
        "total_matches": matches,
        "match_rate": (matches / total * 100) if total > 0 else 0,
        "avg_confidence": avg_confidence,
        "classifications_today": today_total,
        "matches_today": today_matches
    }


@router.get("/stats/classifier", response_model=ClassifierStats)
async def get_classifier_stats():
    """Get classifier statistics"""
    classifier_service = get_classifier_service()
    stats = classifier_service.get_stats()

    return {
        "reference_images": stats['reference_images'],
        "positive_examples": stats['positive_examples'],
        "negative_examples": stats['negative_examples'],
        "total_training_data": stats['total_training_data'],
        "weights": {
            "physical_weight": stats['weights']['physical'],
            "personality_weight": stats['weights']['personality'],
            "interest_weight": stats['weights']['interests']
        },
        "min_score_threshold": stats['min_score_threshold'],
        "super_like_threshold": stats['super_like_threshold']
    }


@router.post("/{result_id}/feedback", response_model=ClassificationResultResponse)
async def submit_feedback(
    result_id: int,
    feedback_data: FeedbackSubmit,
    db: Session = Depends(get_db)
):
    """
    Submit user feedback (like/dislike/super_like) for a classification result.
    This is critical for the active learning loop.
    """
    # Get the classification result
    result = db.query(ClassificationResult).filter(ClassificationResult.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Classification result not found")

    # Update feedback
    result.user_feedback = feedback_data.feedback
    result.feedback_at = datetime.now()

    # Update model version performance metrics if this result has a model version
    if result.model_version_id:
        model_version = db.query(ModelVersion).filter(ModelVersion.id == result.model_version_id).first()

        if model_version:
            # Increment appropriate counter
            if feedback_data.feedback == 'like':
                model_version.likes += 1
            elif feedback_data.feedback == 'dislike':
                model_version.dislikes += 1
            elif feedback_data.feedback == 'super_like':
                model_version.super_likes += 1

            model_version.total_predictions += 1

            logger.info(f"Updated model version {model_version.version_number} metrics: "
                        f"{model_version.likes} likes, {model_version.dislikes} dislikes, "
                        f"{model_version.super_likes} super likes")

    db.commit()
    db.refresh(result)

    logger.info(f"Feedback '{feedback_data.feedback}' submitted for result {result_id}")

    return result


@router.delete("/{result_id}/feedback")
async def remove_feedback(result_id: int, db: Session = Depends(get_db)):
    """Remove feedback from a classification result"""
    result = db.query(ClassificationResult).filter(ClassificationResult.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Classification result not found")

    # Decrement model version metrics if removing feedback
    if result.user_feedback and result.model_version_id:
        model_version = db.query(ModelVersion).filter(ModelVersion.id == result.model_version_id).first()

        if model_version:
            if result.user_feedback == 'like' and model_version.likes > 0:
                model_version.likes -= 1
            elif result.user_feedback == 'dislike' and model_version.dislikes > 0:
                model_version.dislikes -= 1
            elif result.user_feedback == 'super_like' and model_version.super_likes > 0:
                model_version.super_likes -= 1

            if model_version.total_predictions > 0:
                model_version.total_predictions -= 1

    result.user_feedback = None
    result.feedback_at = None

    db.commit()
    db.refresh(result)

    logger.info(f"Feedback removed from result {result_id}")

    return {"message": "Feedback removed successfully"}
