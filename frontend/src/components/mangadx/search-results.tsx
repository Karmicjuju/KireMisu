'use client';

import { useState } from 'react';
import { Download, Plus, Loader2, Book, Calendar, Tag, User, Palette } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MangaDxMangaInfo } from '@/lib/api';

interface SearchResultsProps {
  results: MangaDxMangaInfo[];
  onImport: (mangaId: string) => Promise<void>;
  onDownload: (mangaId: string) => Promise<void>;
  importLoading: boolean;
  downloadLoading: boolean;
}

export function SearchResults({ 
  results, 
  onImport, 
  onDownload, 
  importLoading, 
  downloadLoading 
}: SearchResultsProps) {
  const [loadingStates, setLoadingStates] = useState<Record<string, 'import' | 'download' | null>>({});

  const handleImport = async (mangaId: string) => {
    setLoadingStates(prev => ({ ...prev, [mangaId]: 'import' }));
    try {
      await onImport(mangaId);
    } finally {
      setLoadingStates(prev => ({ ...prev, [mangaId]: null }));
    }
  };

  const handleDownload = async (mangaId: string) => {
    setLoadingStates(prev => ({ ...prev, [mangaId]: 'download' }));
    try {
      await onDownload(mangaId);
    } finally {
      setLoadingStates(prev => ({ ...prev, [mangaId]: null }));
    }
  };

  const getTitle = (manga: MangaDxMangaInfo): string => {
    return manga.title || 'Unknown Title';
  };

  const getDescription = (manga: MangaDxMangaInfo): string => {
    return manga.description || 'No description available.';
  };

  const getAuthors = (manga: MangaDxMangaInfo): string[] => {
    return manga.author ? [manga.author] : [];
  };

  const getArtists = (manga: MangaDxMangaInfo): string[] => {
    return manga.artist ? [manga.artist] : [];
  };

  const getGenres = (manga: MangaDxMangaInfo): string[] => {
    return manga.genres.slice(0, 5); // Show only first 5 genres
  };

  const formatStatus = (status: string): string => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-500 border-green-500/30';
      case 'ongoing':
        return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
      case 'hiatus':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'cancelled':
        return 'bg-red-500/20 text-red-500 border-red-500/30';
      default:
        return 'bg-gray-500/20 text-gray-500 border-gray-500/30';
    }
  };

  const getContentRatingColor = (rating: string): string => {
    switch (rating) {
      case 'safe':
        return 'bg-green-500/20 text-green-500 border-green-500/30';
      case 'suggestive':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'erotica':
      case 'pornographic':
        return 'bg-red-500/20 text-red-500 border-red-500/30';
      default:
        return 'bg-gray-500/20 text-gray-500 border-gray-500/30';
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="grid gap-4 pr-4 pb-4">
        {results.map((manga) => {
          const title = getTitle(manga);
          const description = getDescription(manga);
          const authors = getAuthors(manga);
          const artists = getArtists(manga);
          const genres = getGenres(manga);
          const currentLoadingState = loadingStates[manga.id];

          return (
            <GlassCard key={manga.id} className="p-4">
              <div className="flex flex-col lg:flex-row gap-4">
                {/* Cover Image */}
                <div className="flex-shrink-0 w-20 h-28 bg-muted rounded-md overflow-hidden mx-auto sm:mx-0">
                  {manga.cover_art_url ? (
                    <img
                      src={manga.cover_art_url}
                      alt={`${title} cover`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Book className="h-8 w-8 text-muted-foreground" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg leading-tight mb-1 truncate">
                        {title}
                      </h3>
                      
                      {/* Metadata Row */}
                      <div className="flex items-center flex-wrap gap-3 mb-2 text-sm text-muted-foreground">
                        {manga.publication_year && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>{manga.publication_year}</span>
                          </div>
                        )}
                        <Badge className={getStatusColor(manga.status)}>
                          {formatStatus(manga.status)}
                        </Badge>
                        <Badge className={getContentRatingColor(manga.content_rating)}>
                          {manga.content_rating.toUpperCase()}
                        </Badge>
                      </div>

                      {/* Authors and Artists */}
                      {(authors.length > 0 || artists.length > 0) && (
                        <div className="flex items-center flex-wrap gap-4 mb-2 text-sm text-muted-foreground">
                          {authors.length > 0 && (
                            <div className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              <span>{authors.join(', ')}</span>
                            </div>
                          )}
                          {artists.length > 0 && authors !== artists && (
                            <div className="flex items-center gap-1">
                              <Palette className="h-3 w-3" />
                              <span>{artists.join(', ')}</span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Genres */}
                      {genres.length > 0 && (
                        <div className="flex items-center gap-2 mb-2">
                          <Tag className="h-3 w-3 text-muted-foreground" />
                          <div className="flex flex-wrap gap-1">
                            {genres.map((genre, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {genre}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Description */}
                      <p className="text-sm text-muted-foreground line-clamp-3">
                        {description}
                      </p>
                    </div>

                    {/* Action Buttons - Responsive Layout */}
                    <div className="flex flex-col sm:flex-row lg:flex-col gap-2 w-full sm:w-auto lg:w-auto shrink-0 lg:min-w-[130px]">
                      <Button
                        size="sm"
                        onClick={() => handleImport(manga.id)}
                        disabled={importLoading || currentLoadingState === 'import'}
                        className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 whitespace-nowrap"
                      >
                        {currentLoadingState === 'import' ? (
                          <Loader2 className="h-3 w-3 animate-spin mr-2" />
                        ) : (
                          <Plus className="h-3 w-3 mr-2" />
                        )}
                        Add to Library
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownload(manga.id)}
                        disabled={downloadLoading || currentLoadingState === 'download'}
                        className="w-full whitespace-nowrap"
                      >
                        {currentLoadingState === 'download' ? (
                          <Loader2 className="h-3 w-3 animate-spin mr-2" />
                        ) : (
                          <Download className="h-3 w-3 mr-2" />
                        )}
                        Download
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>
    </ScrollArea>
  );
}