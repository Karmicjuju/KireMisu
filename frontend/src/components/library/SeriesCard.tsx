'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Series {
  id: number
  title: string
  description?: string
  author?: string
  artist?: string
  status?: string
  cover_path?: string
  metadata_json?: Record<string, any>
  created_at?: string
  updated_at?: string
}

interface SeriesCardProps {
  series: Series
  viewMode?: 'grid' | 'list'
  onSelect?: (series: Series) => void
  isSelected?: boolean
  className?: string
}

export function SeriesCard({ 
  series, 
  viewMode = 'grid',
  onSelect,
  isSelected = false,
  className 
}: SeriesCardProps) {
  const [imageError, setImageError] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  const handleImageError = () => {
    setImageError(true)
  }

  const handleCardClick = (e: React.MouseEvent) => {
    // Only handle selection if onSelect is provided and it's not a link click
    if (onSelect && !(e.target as HTMLElement).closest('a, button')) {
      e.preventDefault()
      onSelect(series)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (onSelect && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault()
      onSelect(series)
    }
  }

  if (viewMode === 'list') {
    return (
      <Card 
        className={cn(
          'flex flex-row h-32 cursor-pointer transition-all duration-200 hover:shadow-md',
          'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          isSelected && 'ring-2 ring-primary',
          className
        )}
        tabIndex={onSelect ? 0 : -1}
        onClick={handleCardClick}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="flex-shrink-0 w-24 relative">
          {series.cover_path && !imageError ? (
            <Image
              src={series.cover_path}
              alt={`Cover for ${series.title}`}
              fill
              className="object-cover rounded-l-lg"
              sizes="96px"
              onError={handleImageError}
            />
          ) : (
            <div className="w-full h-full bg-muted flex items-center justify-center rounded-l-lg">
              <span className="text-muted-foreground text-xs">No Cover</span>
            </div>
          )}
        </div>
        
        <CardContent className="flex-1 p-4">
          <div className="space-y-2">
            <Link href={`/library/series/${series.id}`} className="group">
              <h3 className={cn(
                'font-semibold text-foreground group-hover:text-primary transition-colors',
                'line-clamp-2'
              )}>
                {series.title}
              </h3>
            </Link>
            
            <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
              {series.author && (
                <span>by {series.author}</span>
              )}
              {series.status && (
                <Badge variant="secondary" className="text-xs">
                  {series.status}
                </Badge>
              )}
            </div>
            
            {series.description && (
              <p className="text-sm text-muted-foreground line-clamp-2">
                {series.description}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  // Grid view (default)
  return (
    <Card 
      className={cn(
        'group cursor-pointer transition-all duration-200 hover:shadow-lg hover:-translate-y-1',
        'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
        isSelected && 'ring-2 ring-primary',
        className
      )}
      tabIndex={onSelect ? 0 : -1}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="relative aspect-[3/4] overflow-hidden rounded-t-lg">
        {series.cover_path && !imageError ? (
          <Image
            src={series.cover_path}
            alt={`Cover for ${series.title}`}
            fill
            className={cn(
              'object-cover transition-transform duration-300',
              isHovered && 'scale-105'
            )}
            sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
            onError={handleImageError}
          />
        ) : (
          <div className="w-full h-full bg-muted flex items-center justify-center">
            <span className="text-muted-foreground">No Cover</span>
          </div>
        )}
        
        {/* Overlay on hover */}
        <div className={cn(
          'absolute inset-0 bg-black/60 opacity-0 transition-opacity duration-300 flex items-center justify-center',
          isHovered && 'opacity-100'
        )}>
          <Button asChild variant="secondary" size="sm">
            <Link href={`/library/series/${series.id}`}>
              View Details
            </Link>
          </Button>
        </div>
        
        {series.status && (
          <Badge 
            variant="secondary"
            className="absolute top-2 right-2 text-xs"
          >
            {series.status}
          </Badge>
        )}
      </div>
      
      <CardContent className="p-3 space-y-2">
        <Link href={`/library/series/${series.id}`} className="group">
          <h3 className={cn(
            'font-medium text-foreground group-hover:text-primary transition-colors',
            'line-clamp-2 leading-5'
          )}>
            {series.title}
          </h3>
        </Link>
        
        {series.author && (
          <p className="text-sm text-muted-foreground line-clamp-1">
            by {series.author}
          </p>
        )}
      </CardContent>
      
      <CardFooter className="p-3 pt-0">
        <Button 
          asChild 
          variant="outline" 
          size="sm" 
          className="w-full opacity-0 group-hover:opacity-100 transition-opacity duration-200"
        >
          <Link href={`/library/series/${series.id}`}>
            Read Now
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}