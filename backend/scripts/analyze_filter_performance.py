#!/usr/bin/env python3
"""
Performance analysis script for series filtering and sorting.

This script tests the performance of the new filtering and sorting functionality
and provides recommendations for optimization.
"""

import asyncio
import time
from typing import List, Dict, Any
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://kiremisu:kiremisu@localhost:5432/kiremisu")


class FilterPerformanceAnalyzer:
    """Analyzes the performance of series filtering and sorting queries."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection = None
    
    async def connect(self):
        """Connect to the database."""
        self.connection = await asyncpg.connect(self.database_url)
    
    async def disconnect(self):
        """Disconnect from the database."""
        if self.connection:
            await self.connection.close()
    
    async def execute_query(self, query: str, params: tuple = None) -> tuple:
        """Execute a query and return results and execution time."""
        start_time = time.time()
        try:
            if params:
                result = await self.connection.fetch(query, *params)
            else:
                result = await self.connection.fetch(query)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            return result, execution_time
        except Exception as e:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            print(f"Query failed: {e}")
            return None, execution_time
    
    async def analyze_basic_queries(self):
        """Analyze performance of basic filtering queries."""
        print("=== Basic Query Performance Analysis ===")
        
        queries = [
            ("Simple title search", 
             "SELECT id, title FROM series WHERE title ILIKE $1 LIMIT 20", 
             ('%attack%',)),
            
            ("Status filter", 
             "SELECT id, title, status FROM series WHERE status = $1 LIMIT 20", 
             ('completed',)),
            
            ("Author search", 
             "SELECT id, title, author FROM series WHERE author ILIKE $1 LIMIT 20", 
             ('%oda%',)),
            
            ("Combined text search", 
             "SELECT id, title, author FROM series WHERE title ILIKE $1 OR author ILIKE $2 OR artist ILIKE $3 LIMIT 20", 
             ('%action%', '%action%', '%action%')),
            
            ("JSONB genre filter", 
             "SELECT id, title FROM series WHERE metadata_json->'genres' @> $1 LIMIT 20", 
             ('["Action"]',)),
            
            ("JSONB rating filter", 
             "SELECT id, title FROM series WHERE (metadata_json->>'rating')::numeric >= $1 LIMIT 20", 
             (8.0,)),
            
            ("Complex combined filter", 
             """SELECT id, title, status, author, metadata_json 
                FROM series 
                WHERE status = $1 
                  AND (title ILIKE $2 OR author ILIKE $3) 
                  AND metadata_json->'genres' @> $4
                ORDER BY created_at DESC 
                LIMIT 20""", 
             ('completed', '%manga%', '%manga%', '["Action"]')),
        ]
        
        for description, query, params in queries:
            result, exec_time = await self.execute_query(query, params)
            count = len(result) if result else 0
            print(f"{description:25} | {exec_time:8.2f}ms | {count:3d} results")
    
    async def analyze_sorting_queries(self):
        """Analyze performance of sorting queries."""
        print("\n=== Sorting Query Performance Analysis ===")
        
        queries = [
            ("Sort by title ASC", 
             "SELECT id, title FROM series ORDER BY title ASC LIMIT 20"),
            
            ("Sort by title DESC", 
             "SELECT id, title FROM series ORDER BY title DESC LIMIT 20"),
            
            ("Sort by created_at DESC", 
             "SELECT id, title, created_at FROM series ORDER BY created_at DESC LIMIT 20"),
            
            ("Sort by author ASC", 
             "SELECT id, title, author FROM series ORDER BY author ASC NULLS LAST LIMIT 20"),
            
            ("Sort by JSONB rating DESC", 
             "SELECT id, title, metadata_json FROM series ORDER BY (metadata_json->>'rating')::numeric DESC NULLS LAST LIMIT 20"),
            
            ("Multi-level sort", 
             "SELECT id, title, status, author FROM series ORDER BY status ASC, title ASC LIMIT 20"),
            
            ("Sort with filter", 
             "SELECT id, title, status FROM series WHERE status = 'completed' ORDER BY title ASC LIMIT 20"),
        ]
        
        for description, query in queries:
            result, exec_time = await self.execute_query(query)
            count = len(result) if result else 0
            print(f"{description:25} | {exec_time:8.2f}ms | {count:3d} results")
    
    async def analyze_pagination_performance(self):
        """Analyze pagination performance with different offsets."""
        print("\n=== Pagination Performance Analysis ===")
        
        offsets = [0, 100, 500, 1000, 5000]
        base_query = "SELECT id, title FROM series ORDER BY created_at DESC LIMIT 20 OFFSET $1"
        
        for offset in offsets:
            result, exec_time = await self.execute_query(base_query, (offset,))
            count = len(result) if result else 0
            print(f"Offset {offset:5d}            | {exec_time:8.2f}ms | {count:3d} results")
    
    async def analyze_index_usage(self):
        """Analyze index usage for filtering queries."""
        print("\n=== Index Usage Analysis ===")
        
        # Get information about available indexes
        index_query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes 
        WHERE tablename IN ('series', 'filter_presets')
        ORDER BY tablename, indexname;
        """
        
        result, _ = await self.execute_query(index_query)
        
        print("Available indexes:")
        for row in result:
            print(f"  {row['tablename']}.{row['indexname']}")
            if 'gin' in row['indexdef'].lower():
                print(f"    GIN index: {row['indexdef']}")
            elif 'btree' in row['indexdef'].lower():
                print(f"    B-tree index: {row['indexdef']}")
    
    async def analyze_database_statistics(self):
        """Analyze database table statistics."""
        print("\n=== Database Statistics ===")
        
        stats_query = """
        SELECT 
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples
        FROM pg_stat_user_tables 
        WHERE tablename IN ('series', 'filter_presets');
        """
        
        result, _ = await self.execute_query(stats_query)
        
        for row in result:
            print(f"Table: {row['tablename']}")
            print(f"  Live tuples: {row['live_tuples']:,}")
            print(f"  Dead tuples: {row['dead_tuples']:,}")
            print(f"  Inserts: {row['inserts']:,}")
            print(f"  Updates: {row['updates']:,}")
            print(f"  Deletes: {row['deletes']:,}")
            print()
    
    async def generate_performance_recommendations(self):
        """Generate performance recommendations based on analysis."""
        print("\n=== Performance Recommendations ===")
        
        # Check if trigram extension is available
        trgm_query = "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
        result, _ = await self.execute_query(trgm_query)
        
        if result:
            print("✓ pg_trgm extension is available for better text search")
        else:
            print("⚠ Consider enabling pg_trgm extension for better text search performance")
            print("  Run: CREATE EXTENSION pg_trgm;")
        
        # Check for missing indexes
        series_count_query = "SELECT COUNT(*) as count FROM series"
        result, _ = await self.execute_query(series_count_query)
        series_count = result[0]['count'] if result else 0
        
        print(f"✓ Series table contains {series_count:,} records")
        
        if series_count > 1000:
            print("📊 For large datasets, consider:")
            print("  - Partitioning by status or date for very large datasets")
            print("  - Regular VACUUM and ANALYZE operations")
            print("  - Monitoring slow query log")
        
        if series_count > 10000:
            print("  - Consider connection pooling")
            print("  - Monitor memory usage for JSONB queries")
        
        print("\n🔍 Query Optimization Tips:")
        print("  - Use specific filters before generic text search")
        print("  - Limit JSONB operations when possible")
        print("  - Use EXPLAIN ANALYZE to identify slow queries")
        print("  - Consider materialized views for complex aggregations")


async def main():
    """Main function to run performance analysis."""
    analyzer = FilterPerformanceAnalyzer(DATABASE_URL)
    
    try:
        await analyzer.connect()
        print("🔍 Starting Series Filtering Performance Analysis")
        print(f"Database: {DATABASE_URL}")
        print("=" * 70)
        
        await analyzer.analyze_database_statistics()
        await analyzer.analyze_index_usage()
        await analyzer.analyze_basic_queries()
        await analyzer.analyze_sorting_queries()
        await analyzer.analyze_pagination_performance()
        await analyzer.generate_performance_recommendations()
        
        print("\n" + "=" * 70)
        print("✅ Performance analysis complete!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    finally:
        await analyzer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())