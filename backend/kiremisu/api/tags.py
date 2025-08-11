"""API endpoints for tag management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload

from kiremisu.database.connection import get_db
from kiremisu.database.models import Tag, Series, series_tags
from kiremisu.database.schemas import (
    TagResponse,
    TagCreate,
    TagUpdate,
    TagListResponse,
    SeriesTagAssignment,
)

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("/", response_model=TagListResponse)
async def get_tags(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of tags to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of tags to return"),
    search: Optional[str] = Query(None, description="Search term for tag name"),
    sort_by: str = Query("usage", enum=["name", "usage", "created"], description="Sort order"),
) -> TagListResponse:
    """Get list of all tags."""
    query = select(Tag)

    # Add search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.where(Tag.name.ilike(search_term))

    # Add sorting
    if sort_by == "name":
        query = query.order_by(Tag.name.asc())
    elif sort_by == "usage":
        query = query.order_by(Tag.usage_count.desc(), Tag.name.asc())
    elif sort_by == "created":
        query = query.order_by(Tag.created_at.desc())

    # Get total count for pagination
    total_query = select(func.count(Tag.id))
    if search:
        total_query = total_query.where(Tag.name.ilike(f"%{search}%"))
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # Add pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    tags = result.scalars().all()

    return TagListResponse(tags=[TagResponse.from_model(tag) for tag in tags], total=total)


@router.post("/", response_model=TagResponse)
async def create_tag(tag_data: TagCreate, db: AsyncSession = Depends(get_db)) -> TagResponse:
    """Create a new tag."""
    # Check if tag with same name already exists (case-insensitive)
    existing_tag = await db.execute(
        select(Tag).where(func.lower(Tag.name) == func.lower(tag_data.name))
    )
    if existing_tag.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tag with this name already exists")

    # Create new tag
    new_tag = Tag(
        name=tag_data.name,
        description=tag_data.description,
        color=tag_data.color,
    )

    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)

    return TagResponse.from_model(new_tag)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: UUID, db: AsyncSession = Depends(get_db)) -> TagResponse:
    """Get tag details by ID."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return TagResponse.from_model(tag)


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID, tag_data: TagUpdate, db: AsyncSession = Depends(get_db)
) -> TagResponse:
    """Update tag details."""
    # Get existing tag
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check for name conflicts if name is being updated
    if tag_data.name and tag_data.name != tag.name:
        existing_tag = await db.execute(
            select(Tag).where(func.lower(Tag.name) == func.lower(tag_data.name), Tag.id != tag_id)
        )
        if existing_tag.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Tag with this name already exists")

    # Update fields
    update_data = tag_data.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(update(Tag).where(Tag.id == tag_id).values(**update_data))
        await db.commit()
        await db.refresh(tag)

    return TagResponse.from_model(tag)


@router.delete("/{tag_id}")
async def delete_tag(tag_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """Delete a tag."""
    # Check if tag exists
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Delete the tag (cascade will handle series_tags relationships)
    await db.execute(delete(Tag).where(Tag.id == tag_id))
    await db.commit()

    return {"message": "Tag deleted successfully"}


# Series-specific tag endpoints
@router.get("/series/{series_id}", response_model=List[TagResponse])
async def get_series_tags(series_id: UUID, db: AsyncSession = Depends(get_db)) -> List[TagResponse]:
    """Get all tags assigned to a series."""
    # First verify series exists
    series_result = await db.execute(select(Series).where(Series.id == series_id))
    series = series_result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Get tags for this series
    result = await db.execute(
        select(Tag)
        .join(series_tags)
        .where(series_tags.c.series_id == series_id)
        .order_by(Tag.name.asc())
    )
    tags = result.scalars().all()

    return [TagResponse.from_model(tag) for tag in tags]


@router.put("/series/{series_id}", response_model=List[TagResponse])
async def assign_tags_to_series(
    series_id: UUID, assignment: SeriesTagAssignment, db: AsyncSession = Depends(get_db)
) -> List[TagResponse]:
    """Assign tags to a series (replaces existing tags)."""
    # Verify series exists
    series_result = await db.execute(select(Series).where(Series.id == series_id))
    series = series_result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Verify all tags exist
    tags_result = await db.execute(select(Tag).where(Tag.id.in_(assignment.tag_ids)))
    tags = tags_result.scalars().all()

    if len(tags) != len(assignment.tag_ids):
        found_ids = {tag.id for tag in tags}
        missing_ids = set(assignment.tag_ids) - found_ids
        raise HTTPException(status_code=400, detail=f"Tags not found: {list(missing_ids)}")

    # Get current tags to calculate usage changes
    current_tags_result = await db.execute(
        select(Tag.id).join(series_tags).where(series_tags.c.series_id == series_id)
    )
    current_tag_ids = {row[0] for row in current_tags_result.fetchall()}

    # Remove current tag assignments
    await db.execute(delete(series_tags).where(series_tags.c.series_id == series_id))

    # Add new tag assignments
    if assignment.tag_ids:
        values = [{"series_id": series_id, "tag_id": tag_id} for tag_id in assignment.tag_ids]
        await db.execute(series_tags.insert().values(values))

    # Update usage counts for affected tags
    tags_to_decrement = current_tag_ids - set(assignment.tag_ids)
    tags_to_increment = set(assignment.tag_ids) - current_tag_ids

    if tags_to_decrement:
        await db.execute(
            update(Tag).where(Tag.id.in_(tags_to_decrement)).values(usage_count=Tag.usage_count - 1)
        )

    if tags_to_increment:
        await db.execute(
            update(Tag).where(Tag.id.in_(tags_to_increment)).values(usage_count=Tag.usage_count + 1)
        )

    await db.commit()

    # Return updated tags
    result = await db.execute(
        select(Tag)
        .join(series_tags)
        .where(series_tags.c.series_id == series_id)
        .order_by(Tag.name.asc())
    )
    updated_tags = result.scalars().all()

    return [TagResponse.from_model(tag) for tag in updated_tags]


@router.post("/series/{series_id}/add", response_model=List[TagResponse])
async def add_tags_to_series(
    series_id: UUID, assignment: SeriesTagAssignment, db: AsyncSession = Depends(get_db)
) -> List[TagResponse]:
    """Add tags to a series (keeps existing tags)."""
    # Verify series exists
    series_result = await db.execute(select(Series).where(Series.id == series_id))
    series = series_result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Verify all tags exist
    tags_result = await db.execute(select(Tag).where(Tag.id.in_(assignment.tag_ids)))
    tags = tags_result.scalars().all()

    if len(tags) != len(assignment.tag_ids):
        found_ids = {tag.id for tag in tags}
        missing_ids = set(assignment.tag_ids) - found_ids
        raise HTTPException(status_code=400, detail=f"Tags not found: {list(missing_ids)}")

    # Get current tag assignments
    current_assignments = await db.execute(
        select(series_tags.c.tag_id).where(series_tags.c.series_id == series_id)
    )
    current_tag_ids = {row[0] for row in current_assignments.fetchall()}

    # Only add tags that aren't already assigned
    new_tag_ids = set(assignment.tag_ids) - current_tag_ids

    if new_tag_ids:
        # Add new tag assignments
        values = [{"series_id": series_id, "tag_id": tag_id} for tag_id in new_tag_ids]
        await db.execute(series_tags.insert().values(values))

        # Update usage counts
        await db.execute(
            update(Tag).where(Tag.id.in_(new_tag_ids)).values(usage_count=Tag.usage_count + 1)
        )

        await db.commit()

    # Return all current tags for the series
    result = await db.execute(
        select(Tag)
        .join(series_tags)
        .where(series_tags.c.series_id == series_id)
        .order_by(Tag.name.asc())
    )
    all_tags = result.scalars().all()

    return [TagResponse.from_model(tag) for tag in all_tags]


@router.delete("/series/{series_id}/remove", response_model=List[TagResponse])
async def remove_tags_from_series(
    series_id: UUID, assignment: SeriesTagAssignment, db: AsyncSession = Depends(get_db)
) -> List[TagResponse]:
    """Remove specific tags from a series."""
    # Verify series exists
    series_result = await db.execute(select(Series).where(Series.id == series_id))
    series = series_result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Remove specified tag assignments
    await db.execute(
        delete(series_tags).where(
            series_tags.c.series_id == series_id, series_tags.c.tag_id.in_(assignment.tag_ids)
        )
    )

    # Update usage counts
    await db.execute(
        update(Tag).where(Tag.id.in_(assignment.tag_ids)).values(usage_count=Tag.usage_count - 1)
    )

    await db.commit()

    # Return remaining tags for the series
    result = await db.execute(
        select(Tag)
        .join(series_tags)
        .where(series_tags.c.series_id == series_id)
        .order_by(Tag.name.asc())
    )
    remaining_tags = result.scalars().all()

    return [TagResponse.from_model(tag) for tag in remaining_tags]
