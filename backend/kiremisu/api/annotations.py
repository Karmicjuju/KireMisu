"""Annotation API endpoints for KireMisu."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session, selectinload

from kiremisu.database.connection import get_db
from kiremisu.database.models import Annotation, Chapter
from kiremisu.database.schemas import (
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationResponse,
    AnnotationListResponse,
    ChapterAnnotationsResponse,
)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.post("/", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    annotation_data: AnnotationCreate,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Create a new annotation for a chapter."""
    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == annotation_data.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Validate page number if provided
    if annotation_data.page_number is not None:
        if annotation_data.page_number < 1 or annotation_data.page_number > chapter.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"Page number must be between 1 and {chapter.page_count}",
            )

    # Create annotation
    annotation = Annotation(
        chapter_id=annotation_data.chapter_id,
        content=annotation_data.content,
        page_number=annotation_data.page_number,
        annotation_type=annotation_data.annotation_type,
        position_x=annotation_data.position_x,
        position_y=annotation_data.position_y,
        color=annotation_data.color,
    )

    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    return AnnotationResponse.from_model(annotation)


@router.get("/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: UUID,
    include_chapter: bool = Query(False, description="Include chapter information"),
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Get a specific annotation by ID."""
    query = db.query(Annotation).filter(Annotation.id == annotation_id)

    if include_chapter:
        query = query.options(selectinload(Annotation.chapter))

    annotation = query.first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    return AnnotationResponse.from_model(annotation, include_chapter=include_chapter)


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: UUID,
    annotation_data: AnnotationUpdate,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Update an existing annotation."""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Get chapter for validation
    chapter = db.query(Chapter).filter(Chapter.id == annotation.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Associated chapter not found")

    # Update fields if provided
    if annotation_data.content is not None:
        annotation.content = annotation_data.content

    if annotation_data.page_number is not None:
        if annotation_data.page_number < 1 or annotation_data.page_number > chapter.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"Page number must be between 1 and {chapter.page_count}",
            )
        annotation.page_number = annotation_data.page_number

    if annotation_data.annotation_type is not None:
        annotation.annotation_type = annotation_data.annotation_type

    if annotation_data.position_x is not None:
        annotation.position_x = annotation_data.position_x

    if annotation_data.position_y is not None:
        annotation.position_y = annotation_data.position_y

    if annotation_data.color is not None:
        annotation.color = annotation_data.color

    db.commit()
    db.refresh(annotation)

    return AnnotationResponse.from_model(annotation)


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """Delete an annotation."""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.delete(annotation)
    db.commit()


@router.get("/", response_model=AnnotationListResponse)
async def list_annotations(
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    page_number: Optional[int] = Query(None, description="Filter by page number"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of annotations to return"),
    offset: int = Query(0, ge=0, description="Number of annotations to skip"),
    db: Session = Depends(get_db),
) -> AnnotationListResponse:
    """List annotations with optional filtering."""
    query = db.query(Annotation)

    # Apply filters
    if chapter_id:
        query = query.filter(Annotation.chapter_id == chapter_id)

    if annotation_type:
        query = query.filter(Annotation.annotation_type == annotation_type)

    if page_number:
        query = query.filter(Annotation.page_number == page_number)

    # Get total count before applying pagination
    total = query.count()

    # Apply pagination and ordering
    annotations = (
        query.order_by(desc(Annotation.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return AnnotationListResponse(
        annotations=[AnnotationResponse.from_model(a) for a in annotations],
        total=total,
        chapter_id=chapter_id,
        annotation_type=annotation_type,
    )


@router.get("/chapters/{chapter_id}", response_model=ChapterAnnotationsResponse)
async def get_chapter_annotations(
    chapter_id: UUID,
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    page_number: Optional[int] = Query(None, description="Filter by specific page"),
    db: Session = Depends(get_db),
) -> ChapterAnnotationsResponse:
    """Get all annotations for a specific chapter, grouped by page."""
    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Build query for annotations
    query = db.query(Annotation).filter(Annotation.chapter_id == chapter_id)

    if annotation_type:
        query = query.filter(Annotation.annotation_type == annotation_type)

    if page_number:
        query = query.filter(Annotation.page_number == page_number)

    # Get annotations ordered by page and creation time
    annotations = (
        query.order_by(Annotation.page_number.asc(), Annotation.created_at.asc())
        .all()
    )

    return ChapterAnnotationsResponse.from_chapter_and_annotations(chapter, annotations)


@router.get("/chapters/{chapter_id}/pages/{page_number}", response_model=List[AnnotationResponse])
async def get_page_annotations(
    chapter_id: UUID,
    page_number: int,
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    db: Session = Depends(get_db),
) -> List[AnnotationResponse]:
    """Get all annotations for a specific page in a chapter."""
    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Validate page number
    if page_number < 1 or page_number > chapter.page_count:
        raise HTTPException(
            status_code=400,
            detail=f"Page number must be between 1 and {chapter.page_count}",
        )

    # Build query
    query = db.query(Annotation).filter(
        and_(
            Annotation.chapter_id == chapter_id,
            Annotation.page_number == page_number,
        )
    )

    if annotation_type:
        query = query.filter(Annotation.annotation_type == annotation_type)

    # Get annotations ordered by creation time
    annotations = query.order_by(Annotation.created_at.asc()).all()

    return [AnnotationResponse.from_model(a) for a in annotations]


@router.post("/chapters/{chapter_id}/pages/{page_number}", response_model=AnnotationResponse, status_code=201)
async def create_page_annotation(
    chapter_id: UUID,
    page_number: int,
    annotation_data: AnnotationCreate,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Create an annotation for a specific page (convenience endpoint)."""
    # Override the chapter_id and page_number from the URL
    annotation_data.chapter_id = chapter_id
    annotation_data.page_number = page_number

    return await create_annotation(annotation_data, db)


# Bulk operations
@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter_annotations(
    chapter_id: UUID,
    annotation_type: Optional[str] = Query(None, description="Delete only specific annotation type"),
    page_number: Optional[int] = Query(None, description="Delete only annotations on specific page"),
    db: Session = Depends(get_db),
) -> None:
    """Delete all annotations for a chapter (with optional filtering)."""
    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Build query
    query = db.query(Annotation).filter(Annotation.chapter_id == chapter_id)

    if annotation_type:
        query = query.filter(Annotation.annotation_type == annotation_type)

    if page_number:
        if page_number < 1 or page_number > chapter.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"Page number must be between 1 and {chapter.page_count}",
            )
        query = query.filter(Annotation.page_number == page_number)

    # Delete annotations
    deleted_count = query.delete()
    db.commit()

    # Note: In a production system, you might want to return the count of deleted annotations
    # or use a soft delete approach for better data integrity