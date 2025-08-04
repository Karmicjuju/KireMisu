# R-2 Reading Progress Testing Documentation

This document provides comprehensive testing coverage for the R-2: Mark-read & progress bars functionality in KireMisu.

## Testing Overview

The R-2 testing suite ensures that reading progress functionality meets the exit criteria: **"Reading progress visible"** - Users can see their reading progress across the application.

## Test Categories

### 1. API Unit Tests (`tests/api/`)

#### `test_mark_read_progress.py`
Comprehensive API tests for mark-read functionality and progress tracking endpoints.

**Test Classes:**
- `TestMarkReadAPI`: Mark-read toggle endpoint testing
- `TestSeriesProgressAPI`: Series progress calculation testing  
- `TestDashboardStatsAPI`: Dashboard statistics aggregation testing
- `TestProgressAggregationValidation`: Database consistency validation

**Key Test Scenarios:**
- Mark chapters as read/unread successfully
- Series progress updates correctly when chapters are marked
- Dashboard stats reflect accurate reading statistics
- Progress aggregation maintains database consistency
- Concurrent mark-read operations work correctly
- Error handling for invalid chapter IDs

#### `test_reader_progress_integration.py` 
Extended reader API tests covering progress update flows and integration.

**Test Classes:**
- `TestReaderProgressIntegration`: Reader API integration with progress tracking

**Key Test Scenarios:**
- Reader chapter info includes progress information
- Reader progress updates integrate with mark-read functionality
- Progress validation with edge cases
- Concurrent reader and mark-read operations
- Chapter navigation with progress tracking
- Timestamp consistency across APIs

### 2. Frontend Component Tests (`frontend/tests/unit/`)

#### `progress-components.test.tsx`
Mock component tests for new UI components being implemented.

**Test Categories:**
- `ProgressBar Component`: Visual progress display with different values
- `MarkReadButton Component`: Read/unread toggle functionality
- `DashboardStats Component`: Statistics display and formatting
- `ChapterListWithProgress Component`: Chapter lists with progress indicators

**Key Test Scenarios:**
- Progress bars render with correct percentages
- Mark read buttons handle API calls and state changes
- Dashboard stats display all required information
- Chapter lists show individual chapter progress
- Error handling and loading states
- Accessibility features (ARIA labels, screen reader support)

### 3. Integration Tests (`tests/integration/`)

#### `test_mark_read_workflow.py`
End-to-end workflow testing for complete mark-read functionality.

**Test Classes:**
- `TestMarkReadWorkflowIntegration`: Complete workflow validation

**Key Test Scenarios:**
- Complete series reading workflow (mark all chapters)
- Partial reading with unreading workflow
- Dashboard stats update during reading workflow
- Reading progress persistence across sessions
- Concurrent reading workflow
- Mixed volume reading across different volumes
- Error recovery workflow
- Progress calculation edge cases

### 4. E2E Tests (`frontend/tests/e2e/`)

#### `reading-progress-visibility.spec.ts`
Playwright E2E tests validating the main exit criteria.

**Test Categories:**
- Progress visibility on library page
- Chapter progress in series detail view
- Real-time progress updates
- Dashboard statistics display
- Recent reading activity
- Progress bar responsiveness
- Mark read button states
- Progress persistence across refreshes
- Reader interface progress display
- Navigation between chapters
- Accessibility compliance
- Responsive design
- Performance validation
- Error handling and graceful degradation

### 5. Performance Tests (`tests/performance/`)

#### `test_progress_performance.py`
Performance validation for large manga collections.

**Test Classes:**
- `TestProgressCalculationPerformance`: Large-scale performance testing

**Key Test Scenarios:**
- Dashboard stats with 5,000+ chapters (100 series × 50 chapters)
- Series progress calculation for large chapter counts
- Concurrent progress requests performance
- Batch mark-read operations performance
- Progress aggregation performance
- Database query performance optimization
- Memory usage during large operations
- Scalability limits testing (1,000 chapters per series)

## Running the Tests

### Backend API Tests
```bash
# Run all API tests
pytest tests/api/ -v

# Run specific test categories
pytest tests/api/test_mark_read_progress.py -v
pytest tests/api/test_reader_progress_integration.py -v

# Run integration tests
pytest tests/integration/test_mark_read_workflow.py -v

# Run performance tests (warning: creates large datasets)
pytest tests/performance/test_progress_performance.py -v
```

### Frontend Component Tests
```bash
# Navigate to frontend directory
cd frontend

# Run component tests
npm test -- progress-components.test.tsx

# Run with coverage
npm test -- --coverage progress-components.test.tsx
```

### E2E Tests
```bash
# Navigate to frontend directory
cd frontend

# Run E2E tests
npx playwright test reading-progress-visibility.spec.ts

# Run with UI mode for debugging
npx playwright test reading-progress-visibility.spec.ts --ui

# Run specific test
npx playwright test reading-progress-visibility.spec.ts -g "User can see series progress"
```

## Test Data Requirements

### API Tests
- Test series with 5-10 chapters each
- Mixed read/unread states for comprehensive testing
- Various file formats (CBZ, CBR, PDF, folders)
- Multiple volumes per series

### Performance Tests
- Large datasets (100 series × 50 chapters = 5,000 chapters)
- Extreme scalability test (1,000 chapters in single series)
- Mixed progress states across the library

### E2E Tests
- Functional manga library with real test files
- Series in different states (completed, in-progress, unread)
- Valid chapter files for reader testing

## Exit Criteria Validation

### "Reading progress visible" - Verified by:

1. **Library Page Progress**
   - Series cards show progress bars
   - Progress percentages displayed (e.g., "50%")
   - Chapter counts visible (e.g., "5/10 chapters read")

2. **Series Detail Progress**
   - Individual chapter progress indicators
   - Mark-read buttons with clear states
   - Chapter-level progress percentages

3. **Dashboard Statistics**
   - Overall library progress percentage
   - Series breakdown (completed/in-progress/unread)
   - Recent reading activity
   - Reading streak tracking

4. **Reader Interface Progress**
   - Current page progress in reader
   - Chapter completion tracking
   - Progress updates in real-time

5. **Real-time Updates**
   - Progress updates immediately when chapters marked
   - UI refreshes without page reload
   - Consistent state across different views

## Performance Benchmarks

### Response Time Targets
- Dashboard stats: < 5 seconds (5,000+ chapters)
- Series progress: < 2 seconds (50+ chapters)
- Mark-read operation: < 0.5 seconds per chapter
- Batch operations: < 10 seconds (20 chapters)

### Scalability Targets
- Support 1,000+ chapters per series
- Handle 100+ concurrent progress requests
- Memory usage < 200MB increase during operations

### Database Performance
- Progress aggregation queries: < 2 seconds
- Series statistics calculation: < 5 seconds
- Concurrent read/write operations supported

## Test Coverage Goals

### Backend Coverage
- **API Endpoints**: 100% of progress-related endpoints
- **Database Models**: All progress-related fields and relationships
- **Business Logic**: Progress calculation and aggregation logic
- **Error Handling**: All error conditions and edge cases

### Frontend Coverage
- **Components**: All progress-related UI components
- **User Interactions**: Mark-read, progress display, navigation
- **State Management**: Progress state updates and persistence
- **API Integration**: All progress-related API calls

### Integration Coverage
- **End-to-End Workflows**: Complete reading workflows
- **Cross-Component**: Progress updates across different UI areas
- **Data Consistency**: Database and UI state synchronization
- **Performance**: Acceptable performance under load

## Continuous Integration

### Test Execution Order
1. **API Unit Tests**: Fast validation of core functionality
2. **Component Tests**: UI component validation
3. **Integration Tests**: Workflow validation
4. **E2E Tests**: User experience validation
5. **Performance Tests**: Scalability validation (optional, resource-intensive)

### Test Data Management
- Test database isolation for each test run
- Cleanup procedures for large performance datasets
- Mock data generation for consistent testing
- Test fixture management for complex scenarios

## Debugging and Troubleshooting

### Common Issues
1. **Slow Performance Tests**: Use smaller datasets for development
2. **E2E Test Failures**: Check test data setup and database state
3. **Flaky Progress Updates**: Verify API response timing and caching
4. **Memory Issues**: Monitor test database size and cleanup

### Debug Commands
```bash
# Run tests with debug output
pytest tests/api/test_mark_read_progress.py -v -s

# Run single E2E test with debugging
npx playwright test reading-progress-visibility.spec.ts -g "specific test" --debug

# Check test database state
psql -d kiremisu_test -c "SELECT * FROM series; SELECT * FROM chapters;"
```

## Contributing

When adding new progress-related functionality:

1. **Add API Tests**: Unit tests for new endpoints
2. **Add Component Tests**: Tests for new UI components
3. **Update Integration Tests**: Workflow tests for new features
4. **Add E2E Tests**: User-facing functionality validation
5. **Consider Performance**: Test impact on large libraries
6. **Update Documentation**: Keep this documentation current

## Conclusion

This comprehensive testing suite ensures that the R-2 reading progress functionality is robust, performant, and user-friendly. The tests validate both technical correctness and user experience, ensuring that users can effectively track their reading progress across the KireMisu application.