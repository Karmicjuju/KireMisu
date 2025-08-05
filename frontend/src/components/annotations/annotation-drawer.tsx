/**
 * Annotation drawer component for displaying and managing chapter annotations
 */

'use client';

import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  AnnotationResponse,
  ChapterAnnotationsResponse,
  annotationsApi,
  AnnotationCreate,
  AnnotationUpdate,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { AnnotationForm } from './annotation-form';
import { AnnotationMarker } from './annotation-marker';
import {
  X,
  Plus,
  MessageSquare,
  Bookmark,
  Highlighter,
  Filter,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { toast } from '@/hooks/use-toast';

export interface AnnotationDrawerProps {
  chapterId: string;
  isOpen: boolean;
  onClose: () => void;
  onAnnotationSelect?: (annotation: AnnotationResponse) => void;
  onAnnotationCreate?: () => void;
  className?: string;
}

type AnnotationType = 'note' | 'bookmark' | 'highlight';

const ANNOTATION_ICONS = {
  note: MessageSquare,
  bookmark: Bookmark,
  highlight: Highlighter,
} as const;

const ANNOTATION_COLORS = {
  note: '#3b82f6',
  bookmark: '#f59e0b',
  highlight: '#eab308',
} as const;

export function AnnotationDrawer({
  chapterId,
  isOpen,
  onClose,
  onAnnotationSelect,
  onAnnotationCreate,
  className,
}: AnnotationDrawerProps) {
  const [annotations, setAnnotations] = useState<ChapterAnnotationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnnotation, setSelectedAnnotation] = useState<AnnotationResponse | null>(null);
  const [editingAnnotation, setEditingAnnotation] = useState<AnnotationResponse | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [filterType, setFilterType] = useState<AnnotationType | 'all'>('all');
  const [expandedPages, setExpandedPages] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  // Load annotations when drawer opens
  useEffect(() => {
    if (isOpen && chapterId) {
      loadAnnotations();
    }
  }, [isOpen, chapterId]);

  const loadAnnotations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await annotationsApi.getChapterAnnotations(chapterId);
      setAnnotations(data);
      
      // Auto-expand pages with annotations
      const pagesWithAnnotations = new Set(
        Object.keys(data.annotations_by_page).map(page => parseInt(page, 10))
      );
      setExpandedPages(pagesWithAnnotations);
    } catch (err) {
      console.error('Failed to load annotations:', err);
      setError('Failed to load annotations');
      toast({
        title: 'Error',
        description: 'Failed to load annotations',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAnnotation = async (data: AnnotationCreate) => {
    try {
      setSubmitting(true);
      await annotationsApi.createAnnotation(data);
      await loadAnnotations();
      setShowForm(false);
      toast({
        title: 'Success',
        description: 'Annotation created successfully',
      });
      onAnnotationCreate?.();
    } catch (err) {
      console.error('Failed to create annotation:', err);
      toast({
        title: 'Error',
        description: 'Failed to create annotation',
        variant: 'destructive',
      });
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateAnnotation = async (annotationId: string, data: AnnotationUpdate) => {
    try {
      setSubmitting(true);
      await annotationsApi.updateAnnotation(annotationId, data);
      await loadAnnotations();
      setEditingAnnotation(null);
      toast({
        title: 'Success',
        description: 'Annotation updated successfully',
      });
    } catch (err) {
      console.error('Failed to update annotation:', err);
      toast({
        title: 'Error',
        description: 'Failed to update annotation',
        variant: 'destructive',
      });
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteAnnotation = async (annotationId: string) => {
    if (!confirm('Are you sure you want to delete this annotation?')) return;

    try {
      await annotationsApi.deleteAnnotation(annotationId);
      await loadAnnotations();
      setSelectedAnnotation(null);
      toast({
        title: 'Success',
        description: 'Annotation deleted successfully',
      });
    } catch (err) {
      console.error('Failed to delete annotation:', err);
      toast({
        title: 'Error',
        description: 'Failed to delete annotation',
        variant: 'destructive',
      });
    }
  };

  const handleAnnotationClick = (annotation: AnnotationResponse) => {
    setSelectedAnnotation(annotation);
    onAnnotationSelect?.(annotation);
  };

  const togglePageExpansion = (pageNumber: number) => {
    setExpandedPages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(pageNumber)) {
        newSet.delete(pageNumber);
      } else {
        newSet.add(pageNumber);
      }
      return newSet;
    });
  };

  const filteredAnnotations = annotations?.annotations.filter(
    annotation => filterType === 'all' || annotation.annotation_type === filterType
  ) || [];

  const filteredAnnotationsByPage = Object.entries(annotations?.annotations_by_page || {})
    .reduce((acc, [page, pageAnnotations]) => {
      const filtered = pageAnnotations.filter(
        annotation => filterType === 'all' || annotation.annotation_type === filterType
      );
      if (filtered.length > 0) {
        acc[parseInt(page, 10)] = filtered;
      }
      return acc;
    }, {} as Record<number, AnnotationResponse[]>);

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className={cn(
        'fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50',
        'transform transition-transform duration-300 ease-in-out',
        'flex flex-col',
        className
      )}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Annotations</h2>
            {annotations && (
              <p className="text-sm text-gray-600">
                {annotations.chapter_title} • {filteredAnnotations.length} total
              </p>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Actions Bar */}
        <div className="flex items-center gap-2 p-3 border-b bg-gray-50">
          <Button
            size="sm"
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Note
          </Button>

          {/* Filter */}
          <div className="flex items-center gap-1 ml-auto">
            <Filter className="h-4 w-4 text-gray-500" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as AnnotationType | 'all')}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value="all">All</option>
              <option value="note">Notes</option>
              <option value="bookmark">Bookmarks</option>
              <option value="highlight">Highlights</option>
            </select>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center p-8">
              <div className="text-gray-500">Loading annotations...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center p-8">
              <div className="text-red-500">{error}</div>
            </div>
          ) : filteredAnnotations.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-gray-500">
              <MessageSquare className="h-12 w-12 mb-4 text-gray-300" />
              <p className="text-center">
                {filterType === 'all' 
                  ? 'No annotations yet. Click "Add Note" to create your first annotation.'
                  : `No ${filterType}s found.`
                }
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {/* Group by page */}
              {Object.entries(filteredAnnotationsByPage)
                .sort(([a], [b]) => parseInt(a, 10) - parseInt(b, 10))
                .map(([page, pageAnnotations]) => {
                  const pageNumber = parseInt(page, 10);
                  const isExpanded = expandedPages.has(pageNumber);

                  return (
                    <div key={page} className="p-4">
                      {/* Page header */}
                      <button
                        onClick={() => togglePageExpansion(pageNumber)}
                        className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 mb-3"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        Page {pageNumber} ({pageAnnotations.length})
                      </button>

                      {/* Page annotations */}
                      {isExpanded && (
                        <div className="space-y-3 ml-6">
                          {pageAnnotations.map((annotation) => {
                            const Icon = ANNOTATION_ICONS[annotation.annotation_type];
                            const isSelected = selectedAnnotation?.id === annotation.id;

                            return (
                              <div
                                key={annotation.id}
                                className={cn(
                                  'p-3 rounded-lg border cursor-pointer transition-colors',
                                  isSelected
                                    ? 'border-blue-500 bg-blue-50'
                                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                )}
                                onClick={() => handleAnnotationClick(annotation)}
                              >
                                <div className="flex items-start gap-3">
                                  <div
                                    className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                                    style={{
                                      backgroundColor: annotation.color || ANNOTATION_COLORS[annotation.annotation_type],
                                    }}
                                  >
                                    <Icon className="h-3 w-3 text-white" />
                                  </div>
                                  
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm text-gray-900 mb-1">
                                      {annotation.content}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                      {new Date(annotation.created_at).toLocaleDateString()}
                                      {annotation.position_x !== undefined && annotation.position_y !== undefined && (
                                        <span className="ml-2">
                                          • Position: ({(annotation.position_x * 100).toFixed(0)}%, {(annotation.position_y * 100).toFixed(0)}%)
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>

                                {/* Action buttons */}
                                {isSelected && (
                                  <div className="flex gap-2 mt-3 pt-2 border-t">
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setEditingAnnotation(annotation);
                                      }}
                                    >
                                      Edit
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleDeleteAnnotation(annotation.id);
                                      }}
                                      className="text-red-600 hover:text-red-700"
                                    >
                                      Delete
                                    </Button>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      </div>

      {/* Form Modal */}
      {(showForm || editingAnnotation) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-60 flex items-center justify-center p-4">
          <AnnotationForm
            chapterId={chapterId}
            annotation={editingAnnotation || undefined}
            onSubmit={editingAnnotation
              ? (data) => handleUpdateAnnotation(editingAnnotation.id, data as AnnotationUpdate)
              : (data) => handleCreateAnnotation(data as AnnotationCreate)
            }
            onCancel={() => {
              setShowForm(false);
              setEditingAnnotation(null);
            }}
            isSubmitting={submitting}
          />
        </div>
      )}
    </>
  );
}