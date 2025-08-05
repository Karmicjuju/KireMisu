/**
 * Annotation form component for creating and editing annotations
 */

'use client';

import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { AnnotationCreate, AnnotationUpdate, AnnotationResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { MessageSquare, Bookmark, Highlighter, X } from 'lucide-react';

export interface AnnotationFormProps {
  chapterId: string;
  pageNumber?: number;
  position?: { x: number; y: number };
  annotation?: AnnotationResponse; // For editing existing annotations
  onSubmit: (data: AnnotationCreate | AnnotationUpdate) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
  className?: string;
}

const ANNOTATION_TYPES = [
  { value: 'note', label: 'Note', icon: MessageSquare, color: '#3b82f6' },
  { value: 'bookmark', label: 'Bookmark', icon: Bookmark, color: '#f59e0b' },
  { value: 'highlight', label: 'Highlight', icon: Highlighter, color: '#eab308' },
] as const;

const PRESET_COLORS = [
  '#3b82f6', // blue-500
  '#ef4444', // red-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#6b7280', // gray-500
  '#000000', // black
];

export function AnnotationForm({
  chapterId,
  pageNumber,
  position,
  annotation,
  onSubmit,
  onCancel,
  isSubmitting = false,
  className,
}: AnnotationFormProps) {
  const [content, setContent] = useState(annotation?.content || '');
  const [annotationType, setAnnotationType] = useState<'note' | 'bookmark' | 'highlight'>(
    annotation?.annotation_type || 'note'
  );
  const [color, setColor] = useState(annotation?.color || PRESET_COLORS[0]);
  const [customColor, setCustomColor] = useState('');
  const [showColorPicker, setShowColorPicker] = useState(false);

  const isEditing = !!annotation;

  useEffect(() => {
    if (annotation) {
      setContent(annotation.content);
      setAnnotationType(annotation.annotation_type);
      setColor(annotation.color || PRESET_COLORS[0]);
    }
  }, [annotation]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!content.trim()) return;

    const finalColor = customColor || color;

    if (isEditing) {
      // Update existing annotation
      const updateData: AnnotationUpdate = {
        content: content.trim(),
        annotation_type: annotationType,
        color: finalColor,
      };

      // Include position if changed
      if (position) {
        updateData.position_x = position.x;
        updateData.position_y = position.y;
      }

      await onSubmit(updateData);
    } else {
      // Create new annotation
      const createData: AnnotationCreate = {
        chapter_id: chapterId,
        content: content.trim(),
        annotation_type: annotationType,
        page_number: pageNumber,
        position_x: position?.x,
        position_y: position?.y,
        color: finalColor,
      };

      await onSubmit(createData);
    }
  };

  const handleCustomColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setCustomColor(value);
    setColor(value);
  };

  const selectedType = ANNOTATION_TYPES.find(type => type.value === annotationType)!;

  return (
    <div className={cn(
      'bg-white rounded-lg shadow-xl border p-4 w-80 max-w-full',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {isEditing ? 'Edit Annotation' : 'Add Annotation'}
        </h3>
        <Button
          variant="ghost"
          size="icon"
          onClick={onCancel}
          className="h-8 w-8 text-gray-500 hover:text-gray-700"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Annotation Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Type
          </label>
          <div className="flex gap-2">
            {ANNOTATION_TYPES.map((type) => {
              const Icon = type.icon;
              const isSelected = type.value === annotationType;
              
              return (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setAnnotationType(type.value)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-md border transition-colors',
                    isSelected
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-sm">{type.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div>
          <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
            Content
          </label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={`Enter your ${annotationType}...`}
            className={cn(
              'w-full px-3 py-2 border border-gray-300 rounded-md',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
              'resize-none'
            )}
            rows={3}
            maxLength={2000}
            required
          />
          <div className="text-xs text-gray-500 mt-1">
            {content.length}/2000 characters
          </div>
        </div>

        {/* Color Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Color
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {PRESET_COLORS.map((presetColor) => (
              <button
                key={presetColor}
                type="button"
                onClick={() => {
                  setColor(presetColor);
                  setCustomColor('');
                }}
                className={cn(
                  'w-8 h-8 rounded-full border-2 transition-all',
                  color === presetColor
                    ? 'border-gray-900 scale-110'
                    : 'border-gray-300 hover:border-gray-600'
                )}
                style={{ backgroundColor: presetColor }}
                title={presetColor}
              />
            ))}
            <button
              type="button"
              onClick={() => setShowColorPicker(!showColorPicker)}
              className={cn(
                'w-8 h-8 rounded-full border-2 border-dashed transition-all',
                showColorPicker
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-600'
              )}
              title="Custom color"
            >
              <span className="text-xs">+</span>
            </button>
          </div>

          {showColorPicker && (
            <div className="flex gap-2 items-center">
              <Input
                type="color"
                value={customColor || color}
                onChange={handleCustomColorChange}
                className="w-12 h-8"
              />
              <Input
                type="text"
                value={customColor || color}
                onChange={(e) => handleCustomColorChange(e)}
                placeholder="#000000"
                className="flex-1 text-sm"
                pattern="^#[0-9A-Fa-f]{6}$"
              />
            </div>
          )}
        </div>

        {/* Page and Position Info */}
        {(pageNumber || position) && (
          <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
            {pageNumber && <div>Page: {pageNumber}</div>}
            {position && (
              <div>
                Position: ({(position.x * 100).toFixed(1)}%, {(position.y * 100).toFixed(1)}%)
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            type="submit"
            disabled={!content.trim() || isSubmitting}
            className="flex-1"
          >
            {isSubmitting ? 'Saving...' : (isEditing ? 'Update' : 'Create')}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}