'use client';

import { useState } from 'react';
import { Search, Loader2, X, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { GlassCard } from '@/components/ui/glass-card';
import { SearchResults } from './search-results';
import { useMangaDxSearch, useMangaDxImport } from '@/hooks/use-mangadx';
import { MangaDxSearchRequest } from '@/lib/api';

interface MangaDxSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess?: () => void;
}

export function MangaDxSearchDialog({ 
  open, 
  onOpenChange,
  onImportSuccess 
}: MangaDxSearchDialogProps) {
  const [searchForm, setSearchForm] = useState({
    title: '',
    author: '',
  });

  const { 
    results, 
    total, 
    hasMore, 
    loading: searchLoading, 
    error: searchError, 
    search, 
    clearResults 
  } = useMangaDxSearch();

  const { 
    importLoading, 
    downloadLoading, 
    importManga, 
    createDownload 
  } = useMangaDxImport({
    onImportSuccess: () => {
      onImportSuccess?.();
      onOpenChange(false);
      clearResults();
    },
  });

  const handleSearch = async () => {
    if (!searchForm.title.trim() && !searchForm.author.trim()) {
      return;
    }

    const request: MangaDxSearchRequest = {
      title: searchForm.title.trim() || undefined,
      author: searchForm.author.trim() || undefined,
      limit: 20,
      offset: 0,
    };

    await search(request);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleClearSearch = () => {
    setSearchForm({ title: '', author: '' });
    clearResults();
  };

  const handleImport = async (mangaId: string) => {
    await importManga({
      mangadx_id: mangaId,
      import_cover_art: true,
      import_chapters: false,
      overwrite_existing: false,
    });
  };

  const handleDownload = async (mangaId: string) => {
    await createDownload({
      manga_id: mangaId,
      download_type: 'series',
      priority: 5,
    });
  };

  const hasResults = results.length > 0;
  const hasSearched = searchLoading || hasResults || searchError;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[90vh] w-[95vw] sm:w-full flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Discover Manga from MangaDx
          </DialogTitle>
          <DialogDescription>
            Search for manga on MangaDx and add them to your library
          </DialogDescription>
        </DialogHeader>

        {/* Search Form */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search by title..."
                value={searchForm.title}
                onChange={(e) => setSearchForm(prev => ({ ...prev, title: e.target.value }))}
                onKeyPress={handleKeyPress}
                disabled={searchLoading}
              />
            </div>
            <div className="flex-1">
              <Input
                placeholder="Search by author..."
                value={searchForm.author}
                onChange={(e) => setSearchForm(prev => ({ ...prev, author: e.target.value }))}
                onKeyPress={handleKeyPress}
                disabled={searchLoading}
              />
            </div>
            <div className="flex gap-2 sm:flex-shrink-0">
              <Button 
                onClick={handleSearch} 
                disabled={searchLoading || (!searchForm.title.trim() && !searchForm.author.trim())}
                className="flex-1 sm:flex-none bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
              >
                {searchLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                <span className="ml-2 sm:inline">Search</span>
              </Button>
              {(hasSearched || searchForm.title || searchForm.author) && (
                <Button 
                  variant="outline" 
                  onClick={handleClearSearch}
                  disabled={searchLoading}
                  className="flex-1 sm:flex-none"
                >
                  <X className="h-4 w-4" />
                  <span className="ml-2 sm:inline">Clear</span>
                </Button>
              )}
            </div>
          </div>

          {/* Search Status */}
          {searchLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="text-center">
                <Loader2 className="mx-auto mb-2 h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Searching MangaDx...</p>
              </div>
            </div>
          )}

          {searchError && (
            <GlassCard className="p-4 border-destructive">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm font-medium">Search failed</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">{searchError}</p>
            </GlassCard>
          )}

          {hasResults && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Found {total} results{hasMore ? ' (showing first 20)' : ''}
              </p>
            </div>
          )}
        </div>

        {/* Search Results */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {hasResults && (
            <SearchResults
              results={results}
              onImport={handleImport}
              onDownload={handleDownload}
              importLoading={importLoading}
              downloadLoading={downloadLoading}
            />
          )}

          {/* Empty State */}
          {!hasSearched && (
            <div className="flex items-center justify-center h-full min-h-[300px]">
              <div className="text-center">
                <Search className="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
                <h3 className="mb-2 text-lg font-semibold">Search for Manga</h3>
                <p className="text-muted-foreground max-w-md">
                  Enter a manga title or author name to search MangaDx and discover new series to add to your library.
                </p>
              </div>
            </div>
          )}

          {/* No Results */}
          {hasSearched && !searchLoading && !hasResults && !searchError && (
            <div className="flex items-center justify-center h-full min-h-[300px]">
              <div className="text-center">
                <Search className="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
                <h3 className="mb-2 text-lg font-semibold">No Results Found</h3>
                <p className="text-muted-foreground max-w-md">
                  No manga found matching your search criteria. Try different keywords or check your spelling.
                </p>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}