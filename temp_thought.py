from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.song import Song
from core.database import get_async_session
from app.services.deduplication_service import DeduplicationService
from app.api.library import router  # Import existing router to extend it

# Since we are modifying the router in place, I will write the router update directly.
# This content is placeholder for my thought process. 
# Plan:
# 1. Modify app/routers/library.py to add /local-songs endpoint.
# 2. Implement logic: select(Song).where(Song.source == 'local').order_by(Song.model.created_at.desc())
