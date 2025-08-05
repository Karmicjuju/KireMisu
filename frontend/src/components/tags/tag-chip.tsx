/**
 * Tag chip component for displaying individual tags
 */

'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TagResponse } from '@/lib/api';

export interface TagChipProps {
  tag: TagResponse;
  className?: string;
  size?: 'sm' | 'default' | 'lg';
  variant?: 'default' | 'secondary' | 'outline' | 'destructive';
  showCount?: boolean;
  removable?: boolean;
  onClick?: (tag: TagResponse) => void;
  onRemove?: (tag: TagResponse) => void;
}

export function TagChip({
  tag,
  className,
  size = 'default',
  variant = 'default',
  showCount = false,
  removable = false,
  onClick,
  onRemove,
}: TagChipProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onClick?.(tag);
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onRemove?.(tag);
  };

  const badgeStyle = tag.color
    ? {
        backgroundColor: `${tag.color}20`,
        borderColor: tag.color,
        color: tag.color,
      }
    : undefined;

  const content = (
    <>
      <span className="truncate">
        {tag.name}
        {showCount && (
          <span className="ml-1 text-xs opacity-70">({tag.usage_count})</span>
        )}
      </span>
      {removable && (
        <Button
          variant="ghost"
          size="sm"
          className="ml-1 h-auto p-0.5 hover:bg-transparent"
          onClick={handleRemove}
          aria-label={`Remove ${tag.name} tag`}
        >
          <X className="h-3 w-3" />
        </Button>
      )}
    </>
  );

  if (onClick && !removable) {
    return (
      <Badge
        variant={variant}
        className={cn(
          'cursor-pointer transition-colors hover:opacity-80',
          size === 'sm' && 'text-xs px-2 py-0.5',
          size === 'lg' && 'text-sm px-3 py-1',
          className
        )}
        style={badgeStyle}
        onClick={handleClick}
      >
        {content}
      </Badge>
    );
  }

  return (
    <Badge
      variant={variant}
      className={cn(
        'inline-flex items-center gap-1',
        size === 'sm' && 'text-xs px-2 py-0.5',
        size === 'lg' && 'text-sm px-3 py-1',
        onClick && 'cursor-pointer transition-colors hover:opacity-80',
        className
      )}
      style={badgeStyle}
      onClick={onClick ? handleClick : undefined}
    >
      {content}
    </Badge>
  );
}

export interface TagChipListProps {
  tags: TagResponse[];
  className?: string;
  chipProps?: Omit<TagChipProps, 'tag'>;
  maxVisible?: number;
  showMore?: boolean;
}

export function TagChipList({
  tags,
  className,
  chipProps = {},
  maxVisible,
  showMore = true,
}: TagChipListProps) {
  const visibleTags = maxVisible ? tags.slice(0, maxVisible) : tags;
  const hiddenCount = maxVisible ? Math.max(0, tags.length - maxVisible) : 0;

  if (tags.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-1', className)}>
      {visibleTags.map((tag) => (
        <TagChip key={tag.id} tag={tag} {...chipProps} />
      ))}
      {hiddenCount > 0 && showMore && (
        <Badge variant="outline" className="text-xs">
          +{hiddenCount}
        </Badge>
      )}
    </div>
  );
}