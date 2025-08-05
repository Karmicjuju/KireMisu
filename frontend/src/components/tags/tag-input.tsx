/**
 * Tag input component with autocomplete and creation functionality
 */

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, X, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TagResponse, TagCreate, tagsApi } from '@/lib/api';
import { TagChip } from './tag-chip';

export interface TagInputProps {
  selectedTags: TagResponse[];
  onTagsChange: (tags: TagResponse[]) => void;
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  allowCreate?: boolean;
  maxTags?: number;
}

export function TagInput({
  selectedTags,
  onTagsChange,
  className,
  placeholder = 'Type to search or create tags...',
  disabled = false,
  allowCreate = true,
  maxTags,
}: TagInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<TagResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [isCreating, setIsCreating] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (query: string) => {
      if (!query.trim()) {
        setSuggestions([]);
        return;
      }

      setIsLoading(true);
      try {
        const response = await tagsApi.getTags({
          search: query,
          limit: 10,
          sort_by: 'usage',
        });
        
        // Filter out already selected tags
        const selectedTagIds = new Set(selectedTags.map(tag => tag.id));
        const filteredSuggestions = response.tags.filter(
          tag => !selectedTagIds.has(tag.id)
        );
        
        setSuggestions(filteredSuggestions);
      } catch (error) {
        console.error('Failed to search tags:', error);
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    [selectedTags]
  );

  useEffect(() => {
    if (inputValue.trim()) {
      debouncedSearch(inputValue);
      setShowSuggestions(true);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
    setHighlightedIndex(-1);
  }, [inputValue, debouncedSearch]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex(prev => 
        prev < suggestions.length - 1 + (allowCreate && canCreateNew() ? 1 : 0) ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      handleSelectSuggestion();
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setHighlightedIndex(-1);
    } else if (e.key === 'Backspace' && !inputValue && selectedTags.length > 0) {
      // Remove last tag when backspace is pressed on empty input
      handleRemoveTag(selectedTags[selectedTags.length - 1]);
    }
  };

  const canCreateNew = () => {
    const trimmedInput = inputValue.trim().toLowerCase();
    return (
      allowCreate &&
      trimmedInput &&
      !suggestions.some(tag => tag.name.toLowerCase() === trimmedInput) &&
      !selectedTags.some(tag => tag.name.toLowerCase() === trimmedInput)
    );
  };

  const handleSelectSuggestion = async () => {
    if (highlightedIndex === -1) return;

    const isCreateOption = canCreateNew() && highlightedIndex === suggestions.length;
    
    if (isCreateOption) {
      await handleCreateTag();
    } else if (suggestions[highlightedIndex]) {
      handleAddTag(suggestions[highlightedIndex]);
    }
  };

  const handleCreateTag = async () => {
    const trimmedInput = inputValue.trim();
    if (!trimmedInput) return;

    setIsCreating(true);
    try {
      const newTag = await tagsApi.createTag({
        name: trimmedInput,
      });
      handleAddTag(newTag);
    } catch (error) {
      console.error('Failed to create tag:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleAddTag = (tag: TagResponse) => {
    if (maxTags && selectedTags.length >= maxTags) return;
    if (selectedTags.some(selected => selected.id === tag.id)) return;

    onTagsChange([...selectedTags, tag]);
    setInputValue('');
    setShowSuggestions(false);
    setHighlightedIndex(-1);
    inputRef.current?.focus();
  };

  const handleRemoveTag = (tagToRemove: TagResponse) => {
    onTagsChange(selectedTags.filter(tag => tag.id !== tagToRemove.id));
  };

  const handleInputFocus = () => {
    if (inputValue.trim()) {
      setShowSuggestions(true);
    }
  };

  const handleInputBlur = () => {
    // Delay hiding suggestions to allow clicking on them
    setTimeout(() => {
      setShowSuggestions(false);
      setHighlightedIndex(-1);
    }, 200);
  };

  return (
    <div className={cn('relative', className)}>
      <div className="min-h-[40px] flex flex-wrap items-center gap-1 p-2 border border-input bg-background rounded-md focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
        {selectedTags.map((tag) => (
          <TagChip
            key={tag.id}
            tag={tag}
            size="sm"
            removable
            onRemove={handleRemoveTag}
          />
        ))}
        
        <Input
          ref={inputRef}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          onFocus={handleInputFocus}
          onBlur={handleInputBlur}
          placeholder={selectedTags.length === 0 ? placeholder : ''}
          disabled={disabled || (maxTags ? selectedTags.length >= maxTags : false)}
          className="flex-1 min-w-[120px] border-0 p-0 h-auto shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
        />
      </div>

      {showSuggestions && (suggestions.length > 0 || canCreateNew()) && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-lg max-h-60 overflow-auto"
        >
          {suggestions.map((tag, index) => (
            <div
              key={tag.id}
              className={cn(
                'flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-accent hover:text-accent-foreground',
                highlightedIndex === index && 'bg-accent text-accent-foreground'
              )}
              onClick={() => handleAddTag(tag)}
            >
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="text-xs"
                  style={tag.color ? { borderColor: tag.color, color: tag.color } : undefined}
                >
                  {tag.name}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {tag.usage_count} series
                </span>
              </div>
            </div>
          ))}

          {canCreateNew() && (
            <div
              className={cn(
                'flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent hover:text-accent-foreground border-t',
                highlightedIndex === suggestions.length && 'bg-accent text-accent-foreground'
              )}
              onClick={handleCreateTag}
            >
              <Plus className="h-4 w-4" />
              <span>Create "{inputValue.trim()}"</span>
              {isCreating && <span className="text-xs text-muted-foreground">Creating...</span>}
            </div>
          )}
        </div>
      )}

      {isLoading && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          <Search className="h-4 w-4 animate-spin" />
        </div>
      )}
    </div>
  );
}

// Simple debounce utility
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}