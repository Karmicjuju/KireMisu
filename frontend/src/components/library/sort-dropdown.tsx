'use client';

import { useState } from 'react';
import { Check, SortAsc } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { SortState } from '@/lib/library-utils';

interface SortDropdownProps {
  sort: SortState;
  onSortChange: (sort: SortState) => void;
  className?: string;
}

const SORT_OPTIONS = [
  {
    field: 'title',
    label: 'Title',
    options: [
      { direction: 'asc' as const, label: 'A → Z', description: 'Alphabetical order' },
      { direction: 'desc' as const, label: 'Z → A', description: 'Reverse alphabetical' },
    ],
  },
  {
    field: 'author',
    label: 'Author',
    options: [
      { direction: 'asc' as const, label: 'A → Z', description: 'By author name' },
      { direction: 'desc' as const, label: 'Z → A', description: 'Reverse author name' },
    ],
  },
  {
    field: 'created_at',
    label: 'Date Added',
    options: [
      { direction: 'desc' as const, label: 'Newest First', description: 'Recently added first' },
      { direction: 'asc' as const, label: 'Oldest First', description: 'Oldest added first' },
    ],
  },
  {
    field: 'updated_at',
    label: 'Last Updated',
    options: [
      { direction: 'desc' as const, label: 'Recently Updated', description: 'Latest updates first' },
      { direction: 'asc' as const, label: 'Least Recent', description: 'Oldest updates first' },
    ],
  },
  {
    field: 'progress',
    label: 'Reading Progress',
    options: [
      { direction: 'desc' as const, label: 'Most Progress', description: 'Higher progress first' },
      { direction: 'asc' as const, label: 'Least Progress', description: 'Lower progress first' },
    ],
  },
  {
    field: 'total_chapters',
    label: 'Chapter Count',
    options: [
      { direction: 'desc' as const, label: 'Most Chapters', description: 'Longest series first' },
      { direction: 'asc' as const, label: 'Fewest Chapters', description: 'Shortest series first' },
    ],
  },
];

export function SortDropdown({ sort, onSortChange, className }: SortDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  const currentOption = SORT_OPTIONS.find(opt => opt.field === sort.field);
  const currentSort = currentOption?.options.find(opt => opt.direction === sort.direction);

  const handleSortChange = (field: string, direction: 'asc' | 'desc') => {
    onSortChange({ field, direction });
    setIsOpen(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button 
          variant="outline" 
          size="sm" 
          className={className}
        >
          <SortAsc className="mr-2 h-4 w-4" />
          Sort
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Sort Library</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">

          {SORT_OPTIONS.map((group, groupIndex) => (
            <div key={group.field}>
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">
                  {group.label}
                </h4>
                <div className="space-y-1">
                  {group.options.map((option) => {
                    const isSelected = sort.field === group.field && sort.direction === option.direction;
                    return (
                      <label 
                        key={`${group.field}-${option.direction}`}
                        className="flex items-start space-x-2 cursor-pointer p-2 rounded hover:bg-accent"
                      >
                        <input
                          type="radio"
                          name="sort"
                          checked={isSelected}
                          onChange={() => handleSortChange(group.field, option.direction)}
                          className="mt-1 h-4 w-4 text-primary focus:ring-primary"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-sm">{option.label}</div>
                          <div className="text-xs text-muted-foreground">
                            {option.description}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
              {groupIndex < SORT_OPTIONS.length - 1 && <Separator className="my-3" />}
            </div>
          ))}

          
          <Separator />
          
          {/* Current selection summary */}
          <div className="p-2 bg-accent/50 rounded">
            <div className="text-xs text-muted-foreground">
              Currently sorting by:{' '}
              <span className="font-medium text-foreground">
                {currentOption?.label} ({currentSort?.label})
              </span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}