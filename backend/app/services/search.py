"""Search service for manga library full-text search functionality."""

import re
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import text, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.series import Series
from app.models.search_history import SearchHistory


class SearchService:
    """Service for handling manga library search operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def parse_search_query(self, query: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Parse search query and extract filters.
        
        Returns:
            - Cleaned search text
            - Dictionary of filters (tags, author, etc.)
        """
        if not query or not query.strip():
            return "", {}

        # Clean and normalize query
        query = query.strip()
        filters = {}
        search_text_parts = []

        # Extract filters like "author:mangaka", "tag:action", etc.
        filter_pattern = r'(\w+):\s*([^\s]+)'
        matches = re.finditer(filter_pattern, query, re.IGNORECASE)
        
        for match in matches:
            filter_type = match.group(1).lower()
            filter_value = match.group(2)
            
            if filter_type not in filters:
                filters[filter_type] = []
            filters[filter_type].append(filter_value)
            
            # Remove the filter from the query text
            query = query.replace(match.group(0), '', 1)

        # Clean remaining text
        search_text = ' '.join(query.split()).strip()
        
        return search_text, filters

    def build_search_vector_query(self, search_text: str) -> str:
        """
        Build PostgreSQL tsquery string for full-text search.
        
        Args:
            search_text: The cleaned search text
            
        Returns:
            PostgreSQL tsquery compatible string
        """
        if not search_text:
            return ""

        # Split into words and handle each
        words = search_text.split()
        processed_words = []

        for word in words:
            # Remove special characters but keep letters, numbers, and basic punctuation
            # More restrictive regex to prevent injection
            clean_word = re.sub(r'[^a-zA-Z0-9\-_]', '', word.strip())
            if clean_word and len(clean_word) >= 2:  # Minimum 2 characters
                # Escape special tsquery characters
                clean_word = clean_word.replace('&', '').replace('|', '').replace('!', '').replace('(', '').replace(')', '')
                if clean_word:  # Only add if still has content after cleaning
                    # Add prefix matching for partial word searches
                    processed_words.append(f"{clean_word}:*")

        if not processed_words:
            return ""

        # Join with AND operator for all words must match
        return " & ".join(processed_words)

    async def search_series(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Series], int]:
        """
        Search manga series with full-text search and ranking.
        
        Args:
            query: Search query string
            user_id: Optional user ID for search history
            limit: Maximum results to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (results, total_count)
        """
        if not query or not query.strip():
            # Return recent series if no query
            count_stmt = select(func.count(Series.id))
            count_result = await self.db.execute(count_stmt)
            total = count_result.scalar() or 0
            
            stmt = select(Series).order_by(Series.updated_at.desc()).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            results = result.scalars().all()
            return list(results), total

        search_text, filters = self.parse_search_query(query)
        
        # Start with base statement
        base_stmt = select(Series)
        count_stmt = select(func.count(Series.id))
        
        # Apply full-text search if we have search text
        if search_text:
            tsquery = self.build_search_vector_query(search_text)
            if tsquery:
                # Update search vector if it doesn't exist
                self._update_search_vectors()
                
                # Use parameterized queries to prevent SQL injection
                try:
                    # Perform full-text search with ranking using bound parameters
                    search_filter = func.to_tsvector('english', 
                        func.coalesce(Series.title, '') + ' ' + 
                        func.coalesce(Series.author, '') + ' ' + 
                        func.coalesce(Series.artist, '') + ' ' + 
                        func.coalesce(Series.description, '')
                    ).op('@@')(func.to_tsquery('english', tsquery))
                    
                    base_stmt = base_stmt.where(search_filter).order_by(
                        func.ts_rank_cd(
                            func.to_tsvector('english',
                                func.coalesce(Series.title, '') + ' ' + 
                                func.coalesce(Series.author, '') + ' ' + 
                                func.coalesce(Series.artist, '') + ' ' + 
                                func.coalesce(Series.description, '')
                            ),
                            func.to_tsquery('english', tsquery)
                        ).desc(),
                        Series.updated_at.desc()
                    )
                    count_stmt = count_stmt.where(search_filter)
                except Exception as e:
                    # If tsquery fails due to invalid syntax, fall back to safe ILIKE search
                    search_pattern = f"%{search_text[:100]}%"  # Limit length to prevent abuse
                    search_filter = or_(
                        Series.title.ilike(search_pattern),
                        Series.author.ilike(search_pattern),
                        Series.artist.ilike(search_pattern),
                        Series.description.ilike(search_pattern)
                    )
                    base_stmt = base_stmt.where(search_filter).order_by(Series.title.asc())
                    count_stmt = count_stmt.where(search_filter)
            else:
                # Fallback to ILIKE search if tsquery fails
                search_pattern = f"%{search_text}%"
                search_filter = or_(
                    Series.title.ilike(search_pattern),
                    Series.author.ilike(search_pattern),
                    Series.artist.ilike(search_pattern),
                    Series.description.ilike(search_pattern)
                )
                base_stmt = base_stmt.where(search_filter).order_by(Series.title.asc())
                count_stmt = count_stmt.where(search_filter)
        else:
            # No search text, just order by updated_at
            base_stmt = base_stmt.order_by(Series.updated_at.desc())

        # Apply additional filters with proper sanitization
        if 'author' in filters:
            # Limit number of author filters to prevent abuse
            author_list = filters['author'][:5]  # Max 5 author filters
            author_conditions = []
            for author in author_list:
                # Sanitize author input
                safe_author = re.sub(r'[^a-zA-Z0-9\s\-_.]', '', str(author)[:100])
                if safe_author.strip():
                    author_conditions.append(Series.author.ilike(f"%{safe_author}%"))
            
            if author_conditions:
                author_filter = or_(*author_conditions)
                base_stmt = base_stmt.where(author_filter)
                count_stmt = count_stmt.where(author_filter)
            
        if 'status' in filters:
            # Whitelist allowed status values
            allowed_statuses = {'ongoing', 'completed', 'hiatus', 'cancelled'}
            safe_statuses = [status for status in filters['status'][:5] if status.lower() in allowed_statuses]
            if safe_statuses:
                status_filter = Series.status.in_(safe_statuses)
                base_stmt = base_stmt.where(status_filter)
                count_stmt = count_stmt.where(status_filter)

        # Get total count before pagination
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Apply pagination
        paginated_stmt = base_stmt.offset(offset).limit(limit)
        result = await self.db.execute(paginated_stmt)
        results = list(result.scalars().all())

        # Save to search history if user is provided
        if user_id and query.strip():
            await self._save_search_history(user_id, query.strip(), total)

        return results, total

    async def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """
        Get autocomplete suggestions for search queries.
        
        Args:
            partial_query: Partial search query
            limit: Maximum suggestions to return
            
        Returns:
            List of suggested search terms
        """
        if not partial_query or len(partial_query.strip()) < 2:
            return []

        partial_query = partial_query.strip().lower()
        suggestions = set()

        # Sanitize the partial query to prevent injection
        safe_partial_query = re.sub(r'[^a-zA-Z0-9\s\-_.]', '', partial_query[:50])
        if not safe_partial_query.strip():
            return []
            
        # Get suggestions from series titles
        title_stmt = select(Series.title).where(
            Series.title.ilike(f"%{safe_partial_query}%")
        ).limit(min(limit, 20))  # Cap limit to prevent abuse
        title_result = await self.db.execute(title_stmt)
        title_suggestions = title_result.scalars().all()
        
        for title in title_suggestions:
            if title and safe_partial_query.lower() in title.lower():
                suggestions.add(title)

        # Get suggestions from authors
        author_stmt = select(Series.author).where(
            and_(
                Series.author.isnot(None),
                Series.author.ilike(f"%{safe_partial_query}%")
            )
        ).limit(min(limit, 20))  # Cap limit to prevent abuse
        author_result = await self.db.execute(author_stmt)
        author_suggestions = author_result.scalars().all()
        
        for author in author_suggestions:
            if author and safe_partial_query.lower() in author.lower():
                suggestions.add(author)

        # Convert to list and sort by relevance (starts with query first)
        suggestion_list = list(suggestions)
        suggestion_list.sort(key=lambda x: (not x.lower().startswith(safe_partial_query.lower()), len(x), x.lower()))
        
        return suggestion_list[:limit]

    async def get_recent_searches(self, user_id: UUID, limit: int = 10) -> List[str]:
        """
        Get recent search queries for a user.
        
        Args:
            user_id: User ID
            limit: Maximum searches to return
            
        Returns:
            List of recent search queries
        """
        stmt = select(SearchHistory.query).where(
            SearchHistory.user_id == user_id
        ).order_by(
            SearchHistory.created_at.desc()
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        recent_searches = result.scalars().all()

        return list(recent_searches)

    def _update_search_vectors(self):
        """Update search vectors for series that don't have them."""
        # This would typically be handled by a database trigger or background job
        # For now, we'll compute it on-the-fly in the search query
        pass

    async def _save_search_history(self, user_id: UUID, query: str, results_count: int):
        """
        Save search query to history.
        
        Args:
            user_id: User ID
            query: Search query
            results_count: Number of results found
        """
        try:
            # Check if this exact query was searched recently (within last hour)
            recent_stmt = select(SearchHistory).where(
                and_(
                    SearchHistory.user_id == user_id,
                    SearchHistory.query == query,
                    SearchHistory.created_at > func.now() - text("INTERVAL '1 hour'")
                )
            )
            recent_result = await self.db.execute(recent_stmt)
            recent_search = recent_result.scalar_one_or_none()

            if not recent_search:
                search_history = SearchHistory(
                    user_id=user_id,
                    query=query,
                    results_count=results_count
                )
                self.db.add(search_history)
                await self.db.commit()

                # Keep only last 50 searches per user
                old_stmt = select(SearchHistory).where(
                    SearchHistory.user_id == user_id
                ).order_by(SearchHistory.created_at.desc()).offset(50)
                old_result = await self.db.execute(old_stmt)
                old_searches = old_result.scalars().all()

                for old_search in old_searches:
                    await self.db.delete(old_search)
                
                if old_searches:
                    await self.db.commit()

        except Exception as e:
            # Log detailed error internally but don't expose details
            logger.error(f"Error saving search history: {e}", exc_info=True)
            await self.db.rollback()