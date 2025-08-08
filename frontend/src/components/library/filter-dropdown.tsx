'use client';

import { useState } from 'react';
import { Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { FilterState } from '@/lib/library-utils';

interface FilterDropdownProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  availableGenres: string[];
  availableAuthors: string[];
  className?: string;
}

const STATUS_OPTIONS = [
  { value: 'unread', label: 'Unread', description: 'No chapters read' },
  { value: 'reading', label: 'In Progress', description: 'Some chapters read' },
  { value: 'completed', label: 'Completed', description: 'All chapters read' },
];

const RECENTLY_ADDED_OPTIONS = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Last Week' },
  { value: 'month', label: 'Last Month' },
  { value: '3months', label: 'Last 3 Months' },
];

export function FilterDropdown({ 
  filters, 
  onFiltersChange, 
  availableGenres, 
  availableAuthors,
  className 
}: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  const activeFilterCount = 
    filters.status.length + 
    filters.genres.length + 
    filters.authors.length + 
    (filters.recentlyAdded ? 1 : 0);

  const handleStatusToggle = (status: string) => {
    const newStatus = filters.status.includes(status)
      ? filters.status.filter(s => s !== status)
      : [...filters.status, status];
    
    onFiltersChange({ ...filters, status: newStatus });
  };

  const handleGenreToggle = (genre: string) => {
    const newGenres = filters.genres.includes(genre)
      ? filters.genres.filter(g => g !== genre)
      : [...filters.genres, genre];
    
    onFiltersChange({ ...filters, genres: newGenres });
  };

  const handleAuthorToggle = (author: string) => {
    const newAuthors = filters.authors.includes(author)
      ? filters.authors.filter(a => a !== author)
      : [...filters.authors, author];
    
    onFiltersChange({ ...filters, authors: newAuthors });
  };

  const handleRecentlyAddedChange = (value: string | null) => {
    onFiltersChange({ ...filters, recentlyAdded: value });
  };

  const clearAllFilters = () => {
    onFiltersChange({
      status: [],
      genres: [],
      recentlyAdded: null,
      authors: [],
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button 
          variant="outline" 
          size="sm" 
          className={className}
        >
          <Filter className="mr-2 h-4 w-4" />
          Filter
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-2 h-5 min-w-[20px] rounded-full px-1.5 text-xs">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Filter Library</DialogTitle>
            {activeFilterCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="h-auto p-1 text-xs"
              >
                <X className="mr-1 h-3 w-3" />
                Clear All
              </Button>
            )}
          </div>
        </DialogHeader>
        
        <div className="space-y-4">

          {/* Reading Status */}
          <div className="space-y-2">
            <h4 className="font-medium leading-none">Reading Status</h4>
            <div className="grid grid-cols-1 gap-2">
              {STATUS_OPTIONS.map((option) => (
                <label 
                  key={option.value}
                  className="flex items-start space-x-2 cursor-pointer p-2 rounded hover:bg-accent"
                >
                  <input
                    type="checkbox"
                    checked={filters.status.includes(option.value)}
                    onChange={() => handleStatusToggle(option.value)}
                    className="mt-1 h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{option.label}</div>
                    <div className="text-xs text-muted-foreground">{option.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Recently Added */}
          <Separator />
          <div className="space-y-2">
            <h4 className="font-medium leading-none">Recently Added</h4>
            <div className="space-y-1">
              <label className="flex items-center space-x-2 cursor-pointer p-1 rounded hover:bg-accent">
                <input
                  type="radio"
                  name="recentlyAdded"
                  checked={!filters.recentlyAdded}
                  onChange={() => handleRecentlyAddedChange(null)}
                  className="h-4 w-4 text-primary focus:ring-primary"
                />
                <span className="text-sm">Any Time</span>
              </label>
              {RECENTLY_ADDED_OPTIONS.map((option) => (
                <label 
                  key={option.value}
                  className="flex items-center space-x-2 cursor-pointer p-1 rounded hover:bg-accent"
                >
                  <input
                    type="radio"
                    name="recentlyAdded"
                    checked={filters.recentlyAdded === option.value}
                    onChange={() => handleRecentlyAddedChange(option.value)}
                    className="h-4 w-4 text-primary focus:ring-primary"
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Genres */}
          {availableGenres.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h4 className="font-medium leading-none">Genres ({availableGenres.length})</h4>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {availableGenres.slice(0, 10).map((genre) => (
                    <label 
                      key={genre}
                      className="flex items-center space-x-2 cursor-pointer p-1 rounded hover:bg-accent"
                    >
                      <input
                        type="checkbox"
                        checked={filters.genres.includes(genre)}
                        onChange={() => handleGenreToggle(genre)}
                        className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                      />
                      <span className="text-sm">{genre}</span>
                    </label>
                  ))}
                  {availableGenres.length > 10 && (
                    <div className="px-1 py-1 text-xs text-muted-foreground">
                      +{availableGenres.length - 10} more genres
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Authors */}
          {availableAuthors.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h4 className="font-medium leading-none">Authors ({availableAuthors.length})</h4>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {availableAuthors.slice(0, 10).map((author) => (
                    <label 
                      key={author}
                      className="flex items-center space-x-2 cursor-pointer p-1 rounded hover:bg-accent"
                    >
                      <input
                        type="checkbox"
                        checked={filters.authors.includes(author)}
                        onChange={() => handleAuthorToggle(author)}
                        className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                      />
                      <span className="text-sm">{author}</span>
                    </label>
                  ))}
                  {availableAuthors.length > 10 && (
                    <div className="px-1 py-1 text-xs text-muted-foreground">
                      +{availableAuthors.length - 10} more authors
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}