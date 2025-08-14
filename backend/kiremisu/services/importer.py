"""Importer service for importing manga series and chapters into the database."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, LibraryPath, Series
from kiremisu.services.filesystem_parser import FilesystemParser, SeriesInfo

logger = structlog.get_logger(__name__)


class ImportStats:
    """Statistics tracking for import operations."""

    def __init__(self):
        self.series_found = 0
        self.series_created = 0
        self.series_updated = 0
        self.chapters_found = 0
        self.chapters_created = 0
        self.chapters_updated = 0
        self.errors = 0

    def to_dict(self) -> dict[str, int]:
        """Convert stats to dictionary."""
        return {
            "series_found": self.series_found,
            "series_created": self.series_created,
            "series_updated": self.series_updated,
            "chapters_found": self.chapters_found,
            "chapters_created": self.chapters_created,
            "chapters_updated": self.chapters_updated,
            "errors": self.errors,
        }


class ImporterService:
    """Service for importing manga series and chapters from filesystem."""

    def __init__(self):
        """Initialize the importer service."""
        self.parser = FilesystemParser()

    async def scan_library_paths(
        self,
        db: AsyncSession,
        library_path_id: UUID | None = None,
    ) -> ImportStats:
        """Scan one or all library paths and import series/chapters.

        Args:
            db: Database session
            library_path_id: Optional specific library path ID to scan.
                           If None, scan all enabled paths.

        Returns:
            ImportStats: Statistics about the import operation

        Raises:
            ValueError: If specified library path doesn't exist
        """
        operation_logger = logger.bind(
            operation_type="library_import",
            library_path_id=str(library_path_id) if library_path_id else "all",
        )
        operation_logger.info("Starting library import")

        stats = ImportStats()

        try:
            # Get library paths to scan
            paths_to_scan = await self._get_paths_to_scan(db, library_path_id)

            if not paths_to_scan:
                operation_logger.warning("No library paths found to scan")
                return stats

            # Scan each library path
            for library_path in paths_to_scan:
                path_logger = operation_logger.bind(
                    library_path_id=str(library_path.id),
                    library_path=library_path.path,
                )
                path_logger.info("Scanning library path")

                try:
                    # Parse series from filesystem
                    series_list = await self.parser.scan_library_path(library_path.path)
                    path_logger.info("Found series", series_count=len(series_list))

                    # Import each series with individual transaction isolation
                    for series_info in series_list:
                        try:
                            # Use a nested transaction per series for better isolation
                            async with db.begin_nested():
                                await self._import_series(db, series_info, stats)
                                await db.flush()  # Flush to database without committing
                        except Exception as series_e:
                            # Roll back this series only, continue with others
                            series_logger = path_logger.bind(series_title=series_info.title_primary)
                            series_logger.error(
                                "Error importing series, rolling back", error=str(series_e)
                            )
                            stats.errors += 1
                            await db.rollback()

                    # Update last scan time for this path
                    await self._update_last_scan_time(db, library_path.id)

                    # Commit changes for this path
                    await db.commit()

                except Exception as e:
                    path_logger.error("Error scanning library path", error=str(e))
                    stats.errors += 1
                    await db.rollback()  # Roll back any uncommitted changes for this path

            operation_logger.info("Library import completed", stats=stats.to_dict())
            return stats

        except Exception as e:
            operation_logger.error("Library import failed", error=str(e))
            await db.rollback()
            stats.errors += 1
            return stats

    async def _get_paths_to_scan(
        self,
        db: AsyncSession,
        library_path_id: UUID | None = None,
    ) -> list[LibraryPath]:
        """Get library paths to scan based on the request."""
        if library_path_id:
            # Scan specific path
            result = await db.execute(select(LibraryPath).where(LibraryPath.id == library_path_id))
            path = result.scalar_one_or_none()
            if not path:
                raise ValueError(f"Library path not found: {library_path_id}")
            return [path]
        else:
            # Scan all enabled paths
            result = await db.execute(select(LibraryPath).where(LibraryPath.enabled.is_(True)))
            return list(result.scalars().all())

    async def _import_series(
        self,
        db: AsyncSession,
        series_info: SeriesInfo,
        stats: ImportStats,
    ) -> None:
        """Import a single series and its chapters."""
        series_logger = logger.bind(
            operation_type="series_import",
            series_title=series_info.title_primary,
            series_path=series_info.file_path,
        )

        try:
            stats.series_found += 1
            stats.chapters_found += len(series_info.chapters)

            # Check if series already exists by file path
            existing_series = await self._get_series_by_path(db, series_info.file_path)

            if existing_series:
                # Update existing series
                series_logger.info("Updating existing series")
                await self._update_series(db, existing_series, series_info, stats)
            else:
                # Create new series
                series_logger.info("Creating new series")
                await self._create_series(db, series_info, stats)

        except Exception as e:
            series_logger.error("Error importing series", error=str(e))
            stats.errors += 1

    async def _get_series_by_path(
        self,
        db: AsyncSession,
        file_path: str,
    ) -> Series | None:
        """Get existing series by file path."""
        result = await db.execute(select(Series).where(Series.file_path == file_path))
        return result.scalar_one_or_none()

    async def _create_series(
        self,
        db: AsyncSession,
        series_info: SeriesInfo,
        stats: ImportStats,
    ) -> Series:
        """Create a new series and its chapters."""
        # Create series
        series = Series(
            title_primary=series_info.title_primary,
            title_alternative=series_info.title_alternative,
            author=series_info.author,
            artist=series_info.artist,
            description=series_info.description,
            file_path=series_info.file_path,
            cover_image_path=series_info.cover_image_path,
            source_metadata=series_info.source_metadata,
            total_chapters=len(series_info.chapters),
        )

        db.add(series)
        await db.flush()  # Get the series ID
        stats.series_created += 1

        # Create chapters
        for chapter_info in series_info.chapters:
            await self._create_chapter(db, series.id, chapter_info, stats)

        return series

    async def _update_series(
        self,
        db: AsyncSession,
        existing_series: Series,
        series_info: SeriesInfo,
        stats: ImportStats,
    ) -> None:
        """Update an existing series and its chapters."""
        # Update series metadata (preserve user metadata)
        series_updated = False

        if existing_series.title_primary != series_info.title_primary:
            existing_series.title_primary = series_info.title_primary
            series_updated = True

        if existing_series.title_alternative != series_info.title_alternative:
            existing_series.title_alternative = series_info.title_alternative
            series_updated = True

        if existing_series.author != series_info.author:
            existing_series.author = series_info.author
            series_updated = True

        if existing_series.artist != series_info.artist:
            existing_series.artist = series_info.artist
            series_updated = True

        if existing_series.description != series_info.description:
            existing_series.description = series_info.description
            series_updated = True

        if existing_series.cover_image_path != series_info.cover_image_path:
            existing_series.cover_image_path = series_info.cover_image_path
            series_updated = True

        # Update source metadata (merge with existing)
        if series_info.source_metadata:
            # Create new dict to ensure SQLAlchemy detects the change
            updated_metadata = dict(existing_series.source_metadata or {})
            updated_metadata.update(series_info.source_metadata)
            existing_series.source_metadata = updated_metadata
            series_updated = True

        if series_updated:
            existing_series.updated_at = datetime.utcnow()
            stats.series_updated += 1

        # Handle chapters
        await self._sync_series_chapters(db, existing_series, series_info.chapters, stats)

        # Update total chapter count
        existing_series.total_chapters = len(series_info.chapters)

    async def _sync_series_chapters(
        self,
        db: AsyncSession,
        series: Series,
        new_chapters: list,
        stats: ImportStats,
    ) -> None:
        """Synchronize chapters for a series."""
        # Get existing chapters in batch to avoid N+1 queries
        result = await db.execute(select(Chapter).where(Chapter.series_id == series.id))
        existing_chapters = {
            (ch.chapter_number, ch.volume_number): ch for ch in result.scalars().all()
        }

        # Process new/updated chapters
        for chapter_info in new_chapters:
            key = (chapter_info.chapter_number, chapter_info.volume_number)

            if key in existing_chapters:
                # Update existing chapter
                await self._update_chapter(db, existing_chapters[key], chapter_info, stats)
            else:
                # Create new chapter
                await self._create_chapter(db, series.id, chapter_info, stats)

    async def _create_chapter(
        self,
        db: AsyncSession,
        series_id: UUID,
        chapter_info,
        stats: ImportStats,
    ) -> Chapter:
        """Create a new chapter."""
        chapter = Chapter(
            series_id=series_id,
            chapter_number=chapter_info.chapter_number,
            volume_number=chapter_info.volume_number,
            title=chapter_info.title,
            file_path=chapter_info.file_path,
            file_size=chapter_info.file_size,
            page_count=chapter_info.page_count,
            source_metadata=chapter_info.source_metadata,
        )

        db.add(chapter)
        stats.chapters_created += 1
        return chapter

    async def _update_chapter(
        self,
        db: AsyncSession,
        existing_chapter: Chapter,
        chapter_info,
        stats: ImportStats,
    ) -> None:
        """Update an existing chapter."""
        chapter_updated = False

        # Update fields that might change
        if existing_chapter.title != chapter_info.title:
            existing_chapter.title = chapter_info.title
            chapter_updated = True

        if existing_chapter.file_path != chapter_info.file_path:
            existing_chapter.file_path = chapter_info.file_path
            chapter_updated = True

        if existing_chapter.file_size != chapter_info.file_size:
            existing_chapter.file_size = chapter_info.file_size
            chapter_updated = True

        if existing_chapter.page_count != chapter_info.page_count:
            existing_chapter.page_count = chapter_info.page_count
            chapter_updated = True

        # Update source metadata (merge)
        if chapter_info.source_metadata:
            # Create new dict to ensure SQLAlchemy detects the change
            updated_metadata = dict(existing_chapter.source_metadata or {})
            updated_metadata.update(chapter_info.source_metadata)
            existing_chapter.source_metadata = updated_metadata
            chapter_updated = True

        if chapter_updated:
            existing_chapter.updated_at = datetime.utcnow()
            stats.chapters_updated += 1

    async def _update_last_scan_time(
        self,
        db: AsyncSession,
        library_path_id: UUID,
    ) -> None:
        """Update the last scan time for a library path."""
        await db.execute(
            update(LibraryPath)
            .where(LibraryPath.id == library_path_id)
            .values(last_scan=datetime.utcnow())
        )
