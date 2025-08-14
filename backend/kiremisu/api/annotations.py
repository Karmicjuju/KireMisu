"""Annotation API endpoints for KireMisu."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kiremisu.database.connection import get_db
from kiremisu.database.models import Annotation, Chapter
from kiremisu.database.schemas import (
    AnnotationCreate,
    AnnotationListResponse,
    AnnotationResponse,
    AnnotationUpdate,
    ChapterAnnotationsResponse,
)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.post("/", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    annotation_data: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
) -> AnnotationResponse:
    """Create a new annotation for a chapter."""
    # Verify chapter exists
    result = await db.execute(select(Chapter).where(Chapter.id == annotation_data.chapter_id))
    chapter = result.scalar_one_or_none()
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
    await db.commit()
    await db.refresh(annotation)

    return AnnotationResponse.from_model(annotation)


@router.get("/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: UUID,
    include_chapter: bool = Query(False, description="Include chapter information"),
    db: AsyncSession = Depends(get_db),
) -> AnnotationResponse:
    """Get a specific annotation by ID."""
    query = select(Annotation).where(Annotation.id == annotation_id)

    if include_chapter:
        query = query.options(selectinload(Annotation.chapter))

    result = await db.execute(query)
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    return AnnotationResponse.from_model(annotation, include_chapter=include_chapter)


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: UUID,
    annotation_data: AnnotationUpdate,
    db: AsyncSession = Depends(get_db),
) -> AnnotationResponse:
    """Update an existing annotation."""
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Get chapter for validation
    chapter_result = await db.execute(select(Chapter).where(Chapter.id == annotation.chapter_id))
    chapter = chapter_result.scalar_one_or_none()
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

    await db.commit()
    await db.refresh(annotation)

    return AnnotationResponse.from_model(annotation)


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an annotation."""
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.delete(annotation)
    await db.commit()


@router.get("/", response_model=AnnotationListResponse)
async def list_annotations(
    chapter_id: UUID | None = Query(None, description="Filter by chapter ID"),
    annotation_type: str | None = Query(None, description="Filter by annotation type"),
    page_number: int | None = Query(None, description="Filter by page number"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of annotations to return"),
    offset: int = Query(0, ge=0, description="Number of annotations to skip"),
    db: AsyncSession = Depends(get_db),
) -> AnnotationListResponse:
    """List annotations with optional filtering."""
    query = select(Annotation)

    # Apply filters
    if chapter_id:
        query = query.where(Annotation.chapter_id == chapter_id)

    if annotation_type:
        query = query.where(Annotation.annotation_type == annotation_type)

    if page_number:
        query = query.where(Annotation.page_number == page_number)

    # Get total count before applying pagination
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Apply pagination and ordering
    paginated_query = query.order_by(desc(Annotation.created_at)).offset(offset).limit(limit)
    result = await db.execute(paginated_query)
    annotations = result.scalars().all()

    return AnnotationListResponse(
        annotations=[AnnotationResponse.from_model(a) for a in annotations],
        total=total,
        chapter_id=chapter_id,
        annotation_type=annotation_type,
    )


@router.get("/chapters/{chapter_id}", response_model=ChapterAnnotationsResponse)
async def get_chapter_annotations(
    chapter_id: UUID,
    annotation_type: str | None = Query(None, description="Filter by annotation type"),
    page_number: int | None = Query(None, description="Filter by specific page"),
    db: AsyncSession = Depends(get_db),
) -> ChapterAnnotationsResponse:
    """Get all annotations for a specific chapter, grouped by page."""
    # Verify chapter exists
    chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Build query for annotations
    query = select(Annotation).where(Annotation.chapter_id == chapter_id)

    if annotation_type:
        query = query.where(Annotation.annotation_type == annotation_type)

    if page_number:
        query = query.where(Annotation.page_number == page_number)

    # Get annotations ordered by page and creation time
    ordered_query = query.order_by(Annotation.page_number.asc(), Annotation.created_at.asc())
    result = await db.execute(ordered_query)
    annotations = result.scalars().all()

    return ChapterAnnotationsResponse.from_chapter_and_annotations(chapter, annotations)


@router.get("/chapters/{chapter_id}/pages/{page_number}", response_model=list[AnnotationResponse])
async def get_page_annotations(
    chapter_id: UUID,
    page_number: int,
    annotation_type: str | None = Query(None, description="Filter by annotation type"),
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationResponse]:
    """Get all annotations for a specific page in a chapter."""
    # Verify chapter exists
    chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Validate page number
    if page_number < 1 or page_number > chapter.page_count:
        raise HTTPException(
            status_code=400,
            detail=f"Page number must be between 1 and {chapter.page_count}",
        )

    # Build query
    query = select(Annotation).where(
        and_(
            Annotation.chapter_id == chapter_id,
            Annotation.page_number == page_number,
        )
    )

    if annotation_type:
        query = query.where(Annotation.annotation_type == annotation_type)

    # Get annotations ordered by creation time
    ordered_query = query.order_by(Annotation.created_at.asc())
    result = await db.execute(ordered_query)
    annotations = result.scalars().all()

    return [AnnotationResponse.from_model(a) for a in annotations]


@router.post(
    "/chapters/{chapter_id}/pages/{page_number}", response_model=AnnotationResponse, status_code=201
)
async def create_page_annotation(
    chapter_id: UUID,
    page_number: int,
    annotation_data: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
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
    annotation_type: str | None = Query(
        None, description="Delete only specific annotation type"
    ),
    page_number: int | None = Query(
        None, description="Delete only annotations on specific page"
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all annotations for a chapter (with optional filtering)."""
    # Verify chapter exists
    chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Build delete query
    delete_query = delete(Annotation).where(Annotation.chapter_id == chapter_id)

    if annotation_type:
        delete_query = delete_query.where(Annotation.annotation_type == annotation_type)

    if page_number:
        if page_number < 1 or page_number > chapter.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"Page number must be between 1 and {chapter.page_count}",
            )
        delete_query = delete_query.where(Annotation.page_number == page_number)

    # Execute delete
    await db.execute(delete_query)
    await db.commit()
