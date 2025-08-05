/**
 * Series detail page with tag management
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { Badge } from '@/components/ui/badge';
import { ProgressBar } from '@/components/ui/progress-bar';
import { SeriesTagEditor } from '@/components/tags';
import { SeriesResponse, ChapterResponse, seriesApi } from '@/lib/api';
import { 
  ArrowLeft, 
  Book, 
  BookOpen, 
  Play, 
  User, 
  Calendar,
  FileText,
  Languages
} from 'lucide-react';

export default function SeriesDetailPage() {
  const params = useParams();
  const seriesId = params.seriesId as string;
  
  const [series, setSeries] = useState<SeriesResponse | null>(null);
  const [chapters, setChapters] = useState<ChapterResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (seriesId) {
      loadSeriesData();
    }
  }, [seriesId]);

  const loadSeriesData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [seriesData, chaptersData] = await Promise.all([
        seriesApi.getSeries(seriesId),
        seriesApi.getSeriesChapters(seriesId, { limit: 50 }),
      ]);
      
      setSeries(seriesData);
      setChapters(chaptersData);
    } catch (err) {
      console.error('Failed to load series data:', err);
      setError('Failed to load series data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTagsUpdated = (updatedTags: any[]) => {
    if (series) {
      setSeries({
        ...series,
        user_tags: updatedTags,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-700 rounded w-1/4"></div>
          <div className="h-64 bg-gray-700 rounded"></div>
          <div className="h-48 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !series) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <Book className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h2 className="text-xl font-semibold mb-2">Series Not Found</h2>
          <p className="text-muted-foreground mb-4">
            {error || 'The requested series could not be found.'}
          </p>
          <Button asChild>
            <Link href="/library">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Library
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  const progressPercentage = series.total_chapters > 0 
    ? Math.round((series.read_chapters / series.total_chapters) * 100) 
    : 0;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Navigation */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" asChild>
          <Link href="/library">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Library
          </Link>
        </Button>
      </div>

      {/* Series Header */}
      <GlassCard className="p-6">
        <div className="grid md:grid-cols-[200px_1fr] gap-6">
          {/* Cover Image Placeholder */}
          <div className="aspect-[3/4] bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg flex items-center justify-center">
            <Book className="h-16 w-16 text-white/40" />
          </div>

          {/* Series Info */}
          <div className="space-y-4">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">{series.title_primary}</h1>
              {series.title_alternative && (
                <p className="text-lg text-white/70">{series.title_alternative}</p>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {series.author && (
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span>{series.author}</span>
                </div>
              )}
              
              <div className="flex items-center gap-2">
                <Languages className="h-4 w-4 text-muted-foreground" />
                <span className="uppercase">{series.language}</span>
              </div>

              {series.publication_status && (
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="capitalize">{series.publication_status}</span>
                </div>
              )}

              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
                <span>{series.total_chapters} chapters</span>
              </div>
            </div>

            {/* Reading Progress */}
            {series.total_chapters > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Reading Progress</span>
                  <span>{progressPercentage}% Complete</span>
                </div>
                <ProgressBar
                  value={series.read_chapters}
                  max={series.total_chapters}
                  size="default"
                  colorScheme={progressPercentage === 100 ? 'success' : 'primary'}
                  showValue={true}
                />
              </div>
            )}

            {/* Genres */}
            {series.genres.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {series.genres.map((genre) => (
                  <Badge key={genre} variant="outline">
                    {genre}
                  </Badge>
                ))}
              </div>
            )}

            {/* Description */}
            {series.description && (
              <div className="space-y-2">
                <h3 className="font-semibold flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Description
                </h3>
                <p className="text-white/80 leading-relaxed">{series.description}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              {chapters.length > 0 && (
                <Button size="lg" asChild>
                  <Link href={`/reader/${chapters[0].id}`}>
                    <Play className="mr-2 h-4 w-4" />
                    {series.read_chapters > 0 ? 'Continue Reading' : 'Start Reading'}
                  </Link>
                </Button>
              )}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Tag Editor */}
      <SeriesTagEditor
        seriesId={seriesId}
        initialTags={series.user_tags}
        onTagsUpdated={handleTagsUpdated}
      />

      {/* Chapters List */}
      <GlassCard className="p-6">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Chapters ({chapters.length})
          </h2>
          
          {chapters.length > 0 ? (
            <div className="grid gap-2">
              {chapters.map((chapter) => (
                <div
                  key={chapter.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-medium">
                      {Math.floor(chapter.chapter_number)}
                    </div>
                    
                    <div>
                      <div className="font-medium">
                        Chapter {chapter.chapter_number}
                        {chapter.volume_number && ` • Volume ${chapter.volume_number}`}
                      </div>
                      {chapter.title && (
                        <div className="text-sm text-white/60">{chapter.title}</div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {chapter.is_read && (
                      <Badge variant="secondary" className="text-xs">
                        Read
                      </Badge>
                    )}
                    
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/reader/${chapter.id}`}>
                        <Play className="h-3 w-3 mr-1" />
                        Read
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No chapters found</p>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
}