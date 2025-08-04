# KireMisu Manga Reader Components

This directory contains all the components for the manga reading experience in KireMisu.

## Components

### `MangaReader`

The main reader component that orchestrates the entire reading experience.

**Features:**

- Full-screen reading mode
- Keyboard navigation (arrow keys, space, page up/down, home, end, F for fullscreen, escape to exit)
- Touch/swipe gestures for mobile devices
- Automatic reading progress tracking
- Page preloading for smooth experience
- Loading states and error handling
- Accessibility features (ARIA labels, focus management)

**Props:**

- `chapterId`: UUID of the chapter to read
- `initialPage`: Starting page number (default: 1)
- `className`: Additional CSS classes

### `MangaPage`

Individual page component with optimized image loading.

**Features:**

- Next.js Image optimization
- Loading states with spinner
- Error handling with retry capability
- Lazy loading for performance
- Responsive sizing

### `PageNavigation`

Bottom navigation bar with page controls.

**Features:**

- Page counter with direct page input
- Previous/next navigation buttons
- First/last page quick navigation
- Progress bar
- Settings and close buttons
- Glass morphism design

### Hooks

#### `useKeyboardNavigation`

Custom hook for handling keyboard shortcuts in the reader.

**Supported Keys:**

- `→` / `Space` / `Page Down` / `↓`: Next page
- `←` / `Page Up` / `↑`: Previous page
- `Home`: First page
- `End`: Last page
- `F`: Toggle fullscreen
- `Escape`: Exit reader

#### `useTouchNavigation`

Custom hook for handling touch gestures on mobile devices.

**Supported Gestures:**

- Swipe left: Next page
- Swipe right: Previous page
- Swipe up: Next page (vertical mode)
- Swipe down: Previous page (vertical mode)
- Tap: Toggle controls

## Usage

```tsx
import { MangaReader } from '@/components/reader';

export default function ReaderPage({ params }: { params: { chapterId: string } }) {
  return <MangaReader chapterId={params.chapterId} initialPage={1} />;
}
```

## API Integration

The reader components integrate with the following API endpoints:

- `GET /api/chapters/{chapterId}` - Get chapter details
- `GET /api/chapters/{chapterId}/pages` - Get page information
- `GET /api/chapters/{chapterId}/pages/{pageNumber}` - Stream page image
- `PATCH /api/chapters/{chapterId}/progress` - Update reading progress

## Performance Features

1. **Image Preloading**: Adjacent pages are preloaded for instant navigation
2. **Lazy Loading**: Images are loaded only when needed
3. **SWR Caching**: API responses are cached to reduce network requests
4. **Optimized Images**: Next.js Image component handles optimization
5. **Virtual Scrolling**: For large chapter lists (planned)

## Accessibility Features

1. **Keyboard Navigation**: Full keyboard support for navigation
2. **ARIA Labels**: Screen reader support
3. **Focus Management**: Proper focus handling
4. **High Contrast**: Support for high contrast themes
5. **Screen Reader**: Proper semantic markup

## Mobile Features

1. **Touch Gestures**: Swipe navigation
2. **Responsive Design**: Adapts to different screen sizes
3. **Touch-Friendly Controls**: Large touch targets
4. **Prevent Scroll**: Prevents page scrolling during reading

## Theme Integration

All components integrate with the KireMisu design system:

- Glass morphism cards
- Dark theme support
- Consistent spacing and typography
- Orange accent colors
- Smooth animations and transitions
