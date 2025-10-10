"""
Instagram Search API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database.db import get_db
from backend.database.models import InstagramSearch, InstagramResult
from backend.models.schemas import InstagramSearchCreate, InstagramSearchResponse

router = APIRouter(prefix="/instagram", tags=["instagram"])


@router.post("/search", response_model=InstagramSearchResponse)
async def search_instagram(search: InstagramSearchCreate, db: Session = Depends(get_db)):
    """
    Search Instagram profiles and classify them
    Note: Instagram integration to be completed - this is a placeholder
    """
    # Create search record
    db_search = InstagramSearch(
        query=search.query,
        limit=search.limit,
        min_score=search.min_score,
        total_found=0,
        matches_found=0
    )
    db.add(db_search)
    db.commit()
    db.refresh(db_search)

    # TODO: Integrate with existing instagram_classifier_pipeline.py
    # For now, return empty results

    return db_search


@router.get("/searches", response_model=List[InstagramSearchResponse])
async def list_searches(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all Instagram search sessions"""
    return db.query(InstagramSearch).order_by(
        InstagramSearch.created_at.desc()
    ).offset(skip).limit(limit).all()


@router.get("/searches/{search_id}", response_model=InstagramSearchResponse)
async def get_search(search_id: int, db: Session = Depends(get_db)):
    """Get a specific Instagram search with results"""
    search = db.query(InstagramSearch).filter(InstagramSearch.id == search_id).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    return search
