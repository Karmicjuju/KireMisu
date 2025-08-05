/**
 * Annotation marker component for displaying annotation indicators on manga pages
 */

'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { AnnotationResponse } from '@/lib/api';
import { MessageSquare, Bookmark, Highlighter } from 'lucide-react';

export interface AnnotationMarkerProps {
  annotation: AnnotationResponse;
  onClick?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  className?: string;
  isSelected?: boolean;
}

const ANNOTATION_ICONS = {
  note: MessageSquare,
  bookmark: Bookmark,
  highlight: Highlighter,
} as const;

const ANNOTATION_COLORS = {
  note: '#3b82f6',    // blue-500
  bookmark: '#f59e0b', // amber-500
  highlight: '#eab308', // yellow-500
} as const;

export function AnnotationMarker({
  annotation,
  onClick,
  onEdit,
  onDelete,
  className,
  isSelected = false,
}: AnnotationMarkerProps) {
  const Icon = ANNOTATION_ICONS[annotation.annotation_type];
  const defaultColor = ANNOTATION_COLORS[annotation.annotation_type];
  const color = annotation.color || defaultColor;

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onClick?.();
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onEdit?.();
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDelete?.();
  };

  return (
    <div
      className={cn(
        'absolute z-10 group cursor-pointer transition-all duration-200',
        'hover:scale-110 active:scale-95',
        isSelected && 'ring-2 ring-white ring-opacity-60',
        className
      )}
      style={{
        left: `${(annotation.position_x || 0) * 100}%`,
        top: `${(annotation.position_y || 0) * 100}%`,
        transform: 'translate(-50%, -50%)',
      }}
      onClick={handleClick}
      title={annotation.content}
    >
      {/* Marker icon */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center',
          'shadow-lg border-2 border-white',
          'transition-all duration-200',
          isSelected ? 'scale-110' : 'hover:scale-105'
        )}
        style={{ backgroundColor: color }}
      >
        <Icon className="w-4 h-4 text-white" />
      </div>

      {/* Tooltip/preview on hover */}
      <div className={cn(
        'absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2',
        'bg-gray-900 text-white text-sm rounded-lg px-3 py-2 shadow-lg',
        'opacity-0 group-hover:opacity-100 transition-opacity duration-200',
        'pointer-events-none whitespace-nowrap max-w-xs',
        'z-20'
      )}>
        <div className="font-medium capitalize mb-1">
          {annotation.annotation_type}
        </div>
        <div className="text-gray-300 text-xs mb-2">
          {annotation.page_number ? `Page ${annotation.page_number}` : 'No page specified'}
        </div>
        <div className="text-sm leading-relaxed">
          {annotation.content.length > 100
            ? `${annotation.content.substring(0, 100)}...`
            : annotation.content
          }
        </div>
        
        {/* Arrow pointing down */}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2">
          <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
        </div>
      </div>

      {/* Action buttons (visible when selected or hovered) */}
      {(isSelected || onEdit || onDelete) && (
        <div className={cn(
          'absolute top-full left-1/2 transform -translate-x-1/2 mt-1',
          'flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200',
          isSelected && 'opacity-100'
        )}>
          {onEdit && (
            <button
              onClick={handleEdit}
              className={cn(
                'w-6 h-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full',
                'flex items-center justify-center text-xs',
                'transition-colors duration-200 shadow-md'
              )}
              title="Edit annotation"
            >
              ✎
            </button>
          )}
          {onDelete && (
            <button
              onClick={handleDelete}
              className={cn(
                'w-6 h-6 bg-red-600 hover:bg-red-700 text-white rounded-full',
                'flex items-center justify-center text-xs',
                'transition-colors duration-200 shadow-md'
              )}
              title="Delete annotation"
            >
              ✕
            </button>
          )}
        </div>
      )}
    </div>
  );
}