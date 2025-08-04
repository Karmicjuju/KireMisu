# Manual Testing Script: R-1 Page Streaming + Basic Reader

## Prerequisites ✅

**Application Status:**
- ✅ Backend running at: http://localhost:8000
- ✅ Frontend running at: http://localhost:3000  
- ✅ PostgreSQL database running
- ✅ All Docker services healthy

**Before Testing:**
1. Ensure you have test manga files in one of these formats:
   - CBZ/ZIP files with images
   - CBR/RAR files with images  
   - PDF files
   - Folders containing image files (JPG, PNG, etc.)

## Test Scenario 1: Setup Test Data

### Step 1.1: Access the Application
1. Open browser and navigate to: http://localhost:3000
2. **Expected:** KireMisu homepage loads with sidebar navigation
3. **Verify:** Dark theme with glass morphism design elements

### Step 1.2: Configure Library Path
1. Click "Settings" in the sidebar
2. Navigate to "Library Paths" section
3. **Current Status:** Should see existing path `/manga-storage`
4. **Alternative:** Add your own test manga directory if needed

### Step 1.3: Scan for Manga
1. In Settings, find "Scan Now" button
2. Click "Scan Now" 
3. **Expected:** Toast notification appears showing scan progress
4. **Wait:** For scan to complete (should show statistics)
5. **Verify:** Success message with counts (series found, chapters created, etc.)

## Test Scenario 2: Library Navigation

### Step 2.1: View Library
1. Click "Library" in the sidebar
2. **Expected:** Grid view of manga series (if scan found manga)
3. **If Empty:** Shows "Your library is empty" message with setup instructions
4. **If Has Data:** Shows series cards with:
   - Cover placeholder (book icon)
   - Series title and author
   - Chapter count (e.g., "0 / 5 chapters")
   - Progress percentage if any chapters read

### Step 2.2: Access Series (If Available)
1. Click "View Details" on any series card
2. **Expected:** Navigate to series detail page
3. **Alternative:** If no series available, you'll need test manga files

## Test Scenario 3: Core Reader Functionality

### Step 3.1: Access Reader
**Option A - Direct URL (for testing):**
1. Navigate to: http://localhost:3000/reader/test-chapter-id
2. **Expected:** Shows "Chapter not found" error (this is correct)

**Option B - Through API (create test data):**
1. First, let's check if we have any chapters:
   ```bash
   curl -s http://localhost:8000/api/library/paths | jq .
   ```

### Step 3.2: Reader Interface
**Once you have a valid chapter ID:**
1. Navigate to: http://localhost:3000/reader/[CHAPTER_ID]
2. **Expected Reader Interface:**
   - Full-screen black background
   - Manga page displayed in center
   - Top header with series info (auto-hides after 3 seconds)
   - Bottom navigation controls (auto-hides after 3 seconds)

### Step 3.3: Navigation Controls
**Mouse Controls:**
1. **Click left side of page** → Previous page
2. **Click right side of page** → Next page  
3. **Click page** → Toggle UI visibility

**Keyboard Controls:**
1. **Press →** → Next page
2. **Press ←** → Previous page
3. **Press Space** → Next page
4. **Press Page Down** → Next page
5. **Press Page Up** → Previous page
6. **Press Home** → First page
7. **Press End** → Last page
8. **Press F** → Toggle fullscreen
9. **Press Escape** → Exit reader (go back)

**Touch Controls (on mobile/tablet):**
1. **Swipe left** → Next page
2. **Swipe right** → Previous page
3. **Swipe up** → Next page (vertical reading)
4. **Swipe down** → Previous page (vertical reading)
5. **Tap** → Toggle controls

## Test Scenario 4: Reader Features

### Step 4.1: Progress Tracking
1. Navigate through several pages
2. **Expected:** Progress bar at bottom updates
3. **Expected:** Page counter shows current position (e.g., "3 / 20")
4. **Verify:** Reading progress persists if you reload the page

### Step 4.2: Page Loading
1. Navigate between pages quickly
2. **Expected:** Loading spinner appears briefly
3. **Expected:** Pages load smoothly without errors
4. **Verify:** No broken images or 404 errors

### Step 4.3: UI Auto-Hide
1. Move mouse over reader area
2. **Expected:** Header and navigation controls appear
3. Wait 3 seconds without moving mouse
4. **Expected:** Controls fade out automatically

### Step 4.4: Error Handling
1. Try accessing invalid chapter: http://localhost:3000/reader/invalid-id
2. **Expected:** Error message displayed with "Go Back" option
3. **Expected:** Proper error page, not blank screen

## Test Scenario 5: Performance Testing

### Step 5.1: Page Navigation Speed
1. Rapidly navigate through pages (click/keyboard)
2. **Expected:** Smooth transitions, no lag
3. **Expected:** Pages load within 2 seconds each

### Step 5.2: Memory Usage
1. Open browser developer tools (F12)
2. Go to Performance/Memory tab
3. Navigate through 10-20 pages
4. **Expected:** No memory leaks or excessive growth

## Test Scenario 6: Mobile/Responsive Testing

### Step 6.1: Mobile View
1. Open browser developer tools (F12)
2. Switch to mobile device simulation
3. Navigate to reader
4. **Expected:** Touch-friendly interface
5. **Expected:** Proper scaling on small screens

### Step 6.2: Touch Gestures
1. Use touch simulation or actual mobile device
2. Test swipe gestures (left, right, up, down)
3. Test tap to toggle controls
4. **Expected:** Responsive touch interactions

## Test Scenario 7: Accessibility Testing

### Step 7.1: Keyboard Navigation
1. Use only keyboard (no mouse)
2. Tab through interface elements
3. **Expected:** Proper focus indicators
4. **Expected:** All functions accessible via keyboard

### Step 7.2: Screen Reader
1. Enable screen reader (if available)
2. Navigate reader interface
3. **Expected:** Proper ARIA labels announced
4. **Expected:** Page numbers and navigation announced

## Expected Results Summary

### ✅ Success Criteria:
- [ ] Application loads without errors
- [ ] Reader displays manga pages correctly
- [ ] All navigation methods work (mouse, keyboard, touch)
- [ ] Progress tracking functions properly
- [ ] UI auto-hide/show works correctly
- [ ] Error handling shows appropriate messages
- [ ] Performance is smooth and responsive
- [ ] Mobile/touch interface is functional
- [ ] Accessibility features work properly

### 🚨 Common Issues to Report:
- Images not loading (check console for 404s)
- Navigation not responding to input
- UI elements not appearing/disappearing correctly
- Touch gestures not working on mobile
- Performance lag or memory issues
- Accessibility problems (focus, screen reader)

## Debug Information

If you encounter issues, collect this information:

### Browser Console:
1. Open developer tools (F12)
2. Check Console tab for JavaScript errors
3. Check Network tab for failed API requests

### API Health Check:
```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/library/paths

# Test page streaming (replace with real chapter ID)
curl -I http://localhost:8000/api/chapters/CHAPTER_ID/pages/1
```

### Container Status:
```bash
docker ps | grep kiremisu
```

## Need Test Data?

If you need sample manga files for testing:
1. Create a test directory: `mkdir ~/test-manga`
2. Add some sample CBZ files or folders with images
3. Add this path in Settings → Library Paths
4. Run "Scan Now" to import the test data

This will provide actual chapters to test the reader functionality.