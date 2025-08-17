# KireMisu UI Design System

## Design Principles
- **Manga-First**: Emphasize cover art and visual hierarchy
- **Reading-Optimized**: Dark mode default, distraction-free reader
- **Modern Glassmorphism**: Subtle transparency effects with backdrop blur
- **Responsive**: Works on desktop, tablet, and mobile

## Color System
```css
/* Primary Brand */
--orange-primary: #f97316;     /* Main brand color */
--orange-secondary: #ea580c;   /* Hover states */
--red-accent: #dc2626;         /* Notifications, alerts */

/* Dark Theme (Default) */
--slate-950: #020617;          /* Deep background */
--slate-900: #0f172a;          /* Card backgrounds */
--slate-800: #1e293b;          /* Interactive elements */
--slate-700: #334155;          /* Borders */
--slate-400: #94a3b8;          /* Secondary text */
--slate-300: #cbd5e1;          /* Primary text */
```

## Component Library

### Button Variants
```typescript
// Primary action button
<Button variant="default">Download</Button>

// Secondary actions  
<Button variant="outline">Edit</Button>

// Minimal actions
<Button variant="ghost">Cancel</Button>

// Glass effect for overlays
<Button variant="glass">Settings</Button>
```

### Card Components
```typescript
// Standard content card
<Card className="p-6" gradient>
  <h3>Series Title</h3>
  <p>Description...</p>
</Card>

// Interactive series card
<Card onClick={handleClick} className="hover:scale-[1.02]">
  <img src={cover} />
  <div className="p-4">...</div>
</Card>
```

## Layout Patterns

### Dashboard Grid
- 4-column stats cards on desktop
- 2-column on tablet  
- 1-column on mobile
- Auto-adjusting gap spacing

### Library Grid
- 6 covers per row on desktop (1200px+)
- 4 covers per row on tablet (768px+)  
- 2 covers per row on mobile
- Masonry layout for varying aspect ratios

### Reader Layout
- Full-screen immersive experience
- Overlay controls that auto-hide
- Keyboard navigation priority
- Touch-friendly on mobile

## Interactive States

### Hover Effects
- Subtle scale transform (102%)
- Color temperature shift
- Shadow elevation increase
- Smooth 300ms transitions

### Focus States
- Orange outline ring for accessibility
- Clear focus indicators on all interactive elements
- Keyboard navigation support

### Loading States
- Skeleton screens for content areas
- Spinner overlays for actions
- Progressive image loading with blur-up

## Accessibility Features
- WCAG 2.1 AA compliance
- Keyboard navigation for all features
- Screen reader optimization
- High contrast mode support
- Reduced motion preferences

## Implementation Examples

### Series Cover Component
```typescript
const SeriesCover = ({ series, size = "default" }) => (
  <div className="relative group cursor-pointer">
    <img 
      src={series.cover}
      className="w-full h-64 object-cover rounded-xl group-hover:scale-110 transition-transform duration-500"
    />
    
    {/* Gradient overlay */}
    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
    
    {/* Progress indicator */}
    <div className="absolute bottom-3 left-3 right-3">
      <div className="w-full bg-slate-700 rounded-full h-2">
        <div 
          className="bg-gradient-to-r from-orange-500 to-orange-600 h-2 rounded-full"
          style={{ width: `${series.progress}%` }}
        />
      </div>
    </div>
  </div>
);
```

### Reader Controls
```typescript
const ReaderControls = ({ onNext, onPrev, onToggleUI }) => (
  <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 flex items-center gap-3 bg-slate-900/80 backdrop-blur-md rounded-2xl p-3 border border-slate-700/30">
    <Button variant="glass" onClick={onPrev}>
      <ChevronLeft size={20} />
    </Button>
    
    <Button variant="glass" onClick={onToggleUI}>
      <Settings size={20} />
    </Button>
    
    <Button variant="glass" onClick={onNext}>
      <ChevronRight size={20} />
    </Button>
  </div>
);
```

## Performance Considerations
- Use `transform` for animations (GPU accelerated)
- Lazy load images with intersection observer
- Virtual scrolling for large lists
- Optimize re-renders with React.memo
- Cache computed styles with CSS custom properties

For complete UI implementation reference, see `/docs/examples/ui-mock.tsx`
