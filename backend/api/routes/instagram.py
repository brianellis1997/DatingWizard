"""
Instagram Scraping API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from backend.database.db import get_db
from backend.database.models import InstagramSearch, InstagramResult
from backend.models.schemas import (
    InstagramSearchCreate,
    InstagramSearchResponse,
    InstagramResultResponse,
    FeedbackSubmit
)
from backend.services.instagram_service import get_instagram_service
from loguru import logger

router = APIRouter(prefix="/instagram", tags=["instagram"])


@router.post("/scrape/hashtag", response_model=InstagramSearchResponse)
async def scrape_hashtag(
    search_params: InstagramSearchCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start scraping Instagram profiles from a hashtag.
    This is a long-running task that executes in the background.

    Conservative rate limiting:
    - 5-8 minutes between profiles
    - 1 hour pause every 20 profiles
    - Estimated time: 10 hours for 60 profiles
    """
    try:
        instagram_service = get_instagram_service()

        # Create search session immediately
        search_session = InstagramSearch(
            query=search_params.query,
            limit=search_params.limit,
            min_score=search_params.min_score
        )
        db.add(search_session)
        db.commit()
        db.refresh(search_session)

        logger.info(f"Starting Instagram hashtag scrape: #{search_params.query} (limit: {search_params.limit})")

        # Execute scraping in background
        background_tasks.add_task(
            _execute_hashtag_scrape,
            search_session.id,
            search_params.query,
            search_params.limit,
            search_params.min_score
        )

        return search_session

    except Exception as e:
        logger.error(f"Error starting Instagram scrape: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")


def _execute_hashtag_scrape(search_id: int, hashtag: str, limit: int, min_score: float):
    """Background task to execute hashtag scraping"""
    from backend.database.db import SessionLocal

    db = SessionLocal()
    try:
        instagram_service = get_instagram_service()

        # Execute the scrape
        search_session = db.query(InstagramSearch).filter(InstagramSearch.id == search_id).first()
        if not search_session:
            logger.error(f"Search session {search_id} not found")
            return

        # Perform the actual scraping
        instagram_service.scrape_hashtag(
            hashtag=hashtag,
            db_session=db,
            limit=limit,
            min_score=min_score
        )

        logger.info(f"Completed Instagram hashtag scrape for search {search_id}")

    except Exception as e:
        logger.error(f"Error in background scraping task: {e}")
    finally:
        db.close()


@router.post("/scrape/username", response_model=InstagramResultResponse)
async def scrape_username(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Scrape a single Instagram profile by username.
    Returns immediately with the result.
    """
    try:
        instagram_service = get_instagram_service()

        result = instagram_service.scrape_profile_by_username(
            username=username,
            db_session=db
        )

        if not result:
            raise HTTPException(status_code=404, detail=f"Failed to scrape profile: {username}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scraping username {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape profile: {str(e)}")


@router.get("/searches", response_model=List[InstagramSearchResponse])
async def list_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all Instagram search sessions"""
    searches = db.query(InstagramSearch).order_by(
        InstagramSearch.created_at.desc()
    ).offset(skip).limit(limit).all()

    return searches


@router.get("/searches/{search_id}", response_model=InstagramSearchResponse)
async def get_search(search_id: int, db: Session = Depends(get_db)):
    """Get a specific Instagram search session with all results"""
    search = db.query(InstagramSearch).filter(InstagramSearch.id == search_id).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search session not found")

    return search


@router.get("/results", response_model=List[InstagramResultResponse])
async def list_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    matches_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get Instagram scraping results"""
    query = db.query(InstagramResult)

    if matches_only:
        query = query.filter(InstagramResult.is_match == True)

    results = query.order_by(
        InstagramResult.confidence_score.desc()
    ).offset(skip).limit(limit).all()

    return results


@router.get("/results/{result_id}", response_model=InstagramResultResponse)
async def get_result(result_id: int, db: Session = Depends(get_db)):
    """Get a specific Instagram result"""
    result = db.query(InstagramResult).filter(InstagramResult.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return result


@router.post("/results/{result_id}/feedback", response_model=InstagramResultResponse)
async def submit_feedback(
    result_id: int,
    feedback_data: FeedbackSubmit,
    db: Session = Depends(get_db)
):
    """
    Submit user feedback (like/dislike/super_like) for an Instagram result.
    This data is used for active learning.
    """
    instagram_service = get_instagram_service()

    result = instagram_service.submit_feedback(
        db_session=db,
        result_id=result_id,
        feedback=feedback_data.feedback
    )

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return result


@router.delete("/results/{result_id}/feedback")
async def remove_feedback(result_id: int, db: Session = Depends(get_db)):
    """Remove feedback from an Instagram result"""
    instagram_service = get_instagram_service()

    result = instagram_service.remove_feedback(
        db_session=db,
        result_id=result_id
    )

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return {"message": "Feedback removed successfully"}


@router.delete("/results/{result_id}")
async def delete_result(result_id: int, db: Session = Depends(get_db)):
    """Delete an Instagram result"""
    result = db.query(InstagramResult).filter(InstagramResult.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    db.delete(result)
    db.commit()

    return {"message": "Result deleted successfully"}


@router.delete("/searches/{search_id}")
async def delete_search(search_id: int, db: Session = Depends(get_db)):
    """Delete an Instagram search session and all its results"""
    search = db.query(InstagramSearch).filter(InstagramSearch.id == search_id).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search session not found")

    db.delete(search)
    db.commit()

    return {"message": "Search session deleted successfully"}
