/**
 * Series tag editor component for managing tags assigned to a series
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { Separator } from '@/components/ui/separator';
import { TagInput } from './tag-input';
import { TagChipList } from './tag-chip';
import { cn } from '@/lib/utils';
import { TagResponse, tagsApi } from '@/lib/api';
import { Edit, Save, X, Tags } from 'lucide-react';

export interface SeriesTagEditorProps {
  seriesId: string;
  initialTags?: TagResponse[];
  className?: string;
  onTagsUpdated?: (tags: TagResponse[]) => void;
}

export function SeriesTagEditor({
  seriesId,
  initialTags = [],
  className,
  onTagsUpdated,
}: SeriesTagEditorProps) {
  const [tags, setTags] = useState<TagResponse[]>(initialTags);
  const [editingTags, setEditingTags] = useState<TagResponse[]>(initialTags);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Load initial tags if not provided
  useEffect(() => {
    if (initialTags.length === 0) {
      loadSeriesTags();
    }
  }, [seriesId]);

  const loadSeriesTags = async () => {
    setIsLoading(true);
    try {
      const seriesTags = await tagsApi.getSeriesTags(seriesId);
      setTags(seriesTags);
      setEditingTags(seriesTags);
    } catch (error) {
      console.error('Failed to load series tags:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartEditing = () => {
    setEditingTags([...tags]);
    setIsEditing(true);
  };

  const handleCancelEditing = () => {
    setEditingTags([...tags]);
    setIsEditing(false);
  };

  const handleSaveTags = async () => {
    setSaving(true);
    try {
      const tagIds = editingTags.map(tag => tag.id);
      const updatedTags = await tagsApi.assignTagsToSeries(seriesId, { tag_ids: tagIds });
      
      setTags(updatedTags);
      setEditingTags(updatedTags);
      setIsEditing(false);
      onTagsUpdated?.(updatedTags);
    } catch (error) {
      console.error('Failed to save tags:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveTag = (tagToRemove: TagResponse) => {
    if (!isEditing) return;
    setEditingTags(prev => prev.filter(tag => tag.id !== tagToRemove.id));
  };

  const hasChanges = () => {
    if (tags.length !== editingTags.length) return true;
    const currentIds = new Set(tags.map(tag => tag.id));
    return editingTags.some(tag => !currentIds.has(tag.id));
  };

  if (isLoading) {
    return (
      <GlassCard className={cn('p-4', className)}>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Tags className="h-4 w-4 animate-pulse" />
          Loading tags...
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn('p-4', className)}>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tags className="h-5 w-5" />
            <h3 className="font-semibold">Tags</h3>
            {tags.length > 0 && (
              <span className="text-sm text-muted-foreground">({tags.length})</span>
            )}
          </div>
          
          {!isEditing ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartEditing}
              className="gap-2"
            >
              <Edit className="h-4 w-4" />
              Edit Tags
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancelEditing}
                disabled={isSaving}
                className="gap-2"
              >
                <X className="h-4 w-4" />
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveTags}
                disabled={isSaving || !hasChanges()}
                className="gap-2"
              >
                <Save className="h-4 w-4" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          )}
        </div>

        <Separator />

        {isEditing ? (
          <div className="space-y-3">
            <TagInput
              selectedTags={editingTags}
              onTagsChange={setEditingTags}
              placeholder="Search or create tags to organize this series..."
              allowCreate={true}
            />
            
            {hasChanges() && (
              <div className="text-sm text-muted-foreground">
                Changes will be saved when you click "Save"
              </div>
            )}
          </div>
        ) : (
          <div>
            {tags.length > 0 ? (
              <TagChipList
                tags={tags}
                chipProps={{
                  size: 'default',
                  variant: 'secondary',
                  showCount: true,
                }}
              />
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Tags className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No tags assigned</p>
                <p className="text-xs">Click "Edit Tags" to add some tags to organize this series</p>
              </div>
            )}
          </div>
        )}
      </div>
    </GlassCard>
  );
}