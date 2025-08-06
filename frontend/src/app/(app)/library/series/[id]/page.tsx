/**
 * Series detail page with comprehensive progress integration
 */

'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import useSWR from 'swr';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChapterList } from '@/components/library/chapter-list';
import { SeriesProgressSummary } from '@/components/progress/series-progress';
import { useReadingProgress, useSeriesProgress } from '@/hooks/use-reading-progress';
import {
  seriesApi,
  chaptersApi,
  type SeriesResponse,
  type ChapterResponse,
  type SeriesProgress,
} from '@/lib/api';
import {
  ArrowLeft,
  BookOpen,
  Star,
  Tag,
  Calendar,
  User,
  Globe,
  Play,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function SeriesDetailPage() {
  const params = useParams();
  const router = useRouter();
  const seriesId = params.id as string;

  const { markChapterRead } = useReadingProgress();

  // Fetch series data
  const {
    data: series,
    error: seriesError,
    isLoading: seriesLoading,
  } = useSWR<SeriesResponse>(
    seriesId ? `/api/series/${seriesId}` : null,
    () => seriesApi.getSeries(seriesId),
    {
      revalidateOnFocus: false,
    }
  );

  // Fetch chapters
  const {
    data: chapters,
    error: chaptersError,
    isLoading: chaptersLoading,
  } = useSWR<ChapterResponse[]>(
    seriesId ? `/api/series/${seriesId}/chapters` : null,
    () => seriesApi.getSeriesChapters(seriesId),
    {
      revalidateOnFocus: false,
    }
  );

  // Fetch series progress
  const { progress, loading: progressLoading, error: progressError } = useSeriesProgress(seriesId);

  const handleBack = () => {
    router.back();
  };

  const handleContinueReading = () => {
    if (!chapters || chapters.length === 0) return;

    // Find the next unread chapter or the first chapter
    const nextChapter = chapters.find(ch => !ch.is_read) || chapters[0];
    router.push(`/reader/${nextChapter.id}`);
  };

  const handleChapterMarkRead = async (chapterId: string, isRead: boolean) => {
    await markChapterRead(chapterId, isRead);
  };

  if (seriesLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-white">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p>Loading series...</p>
        </div>
      </div>
    );
  }

  if (seriesError || !series) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center text-white">
          <AlertTriangle className="h-12 w-12 text-red-400" />
          <div>
            <h2 className="text-xl font-semibold">Series not found</h2>
            <p className="text-white/70">The series you're looking for doesn't exist</p>
          </div>
          <Button onClick={handleBack} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleBack}
          className="hover:bg-white/20"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-white">{series.title_primary}</h1>
          {series.title_alternative && (
            <p className="text-lg text-white/70">{series.title_alternative}</p>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="space-y-6 lg:col-span-2">
          {/* Series Info */}
          <GlassCard className="p-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Cover placeholder */}
              <div className="flex aspect-[3/4] items-center justify-center rounded-lg bg-gradient-to-br from-slate-800 to-slate-900">
                <BookOpen className="h-16 w-16 text-white/40" />
              </div>

              {/* Metadata */}
              <div className="space-y-4">
                {series.author && (
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-white/60" />
                    <span className="text-white/90">
                      <strong>Author:</strong> {series.author}
                    </span>
                  </div>
                )}

                {series.artist && series.artist !== series.author && (
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-white/60" />
                    <span className="text-white/90">
                      <strong>Artist:</strong> {series.artist}
                    </span>
                  </div>
                )}

                {series.publication_status && (
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-white/60" />
                    <span className="text-white/90">
                      <strong>Status:</strong> {series.publication_status}
                    </span>
                  </div>
                )}

                {series.language && (
                  <div className="flex items-center gap-2 text-sm">
                    <Globe className="h-4 w-4 text-white/60" />
                    <span className="text-white/90">
                      <strong>Language:</strong> {series.language}
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-2 text-sm">
                  <BookOpen className="h-4 w-4 text-white/60" />
                  <span className="text-white/90">
                    <strong>Chapters:</strong> {series.total_chapters}
                  </span>
                </div>

                <div className="text-sm text-white/60">
                  <strong>Added:</strong>{' '}
                  {formatDistanceToNow(new Date(series.created_at), { addSuffix: true })}
                </div>
              </div>
            </div>

            {/* Description */}
            {series.description && (
              <div className="mt-6 pt-6 border-t border-white/10">
                <h3 className="mb-3 text-lg font-semibold text-white">Description</h3>
                <p className="text-white/80 leading-relaxed">{series.description}</p>
              </div>
            )}

            {/* Genres and Tags */}
            {(series.genres.length > 0 || series.tags.length > 0 || series.custom_tags.length > 0) && (
              <div className="mt-6 pt-6 border-t border-white/10 space-y-4">
                {series.genres.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-medium text-white/90">Genres</h4>
                    <div className="flex flex-wrap gap-2">
                      {series.genres.map((genre) => (
                        <Badge key={genre} variant="secondary" className="text-xs">
                          {genre}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {series.tags.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-medium text-white/90">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {series.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          <Tag className="mr-1 h-3 w-3" />
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {series.custom_tags.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-medium text-white/90">Custom Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {series.custom_tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs border-purple-500/50 text-purple-400">
                          <Star className="mr-1 h-3 w-3" />
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </GlassCard>

          {/* Chapters */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">Chapters</h2>
              {chapters && chapters.length > 0 && (
                <Button onClick={handleContinueReading}>
                  <Play className="mr-2 h-4 w-4" />
                  {progress?.next_unread_chapter ? 'Continue Reading' : 'Start Reading'}
                </Button>
              )}
            </div>

            {chaptersLoading ? (
              <GlassCard className="p-8 text-center">
                <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-slate-400" />
                <p className="text-slate-400">Loading chapters...</p>
              </GlassCard>
            ) : chaptersError ? (
              <GlassCard className="p-8 text-center">
                <AlertTriangle className="mx-auto mb-4 h-8 w-8 text-red-500" />
                <p className="text-slate-400">Failed to load chapters</p>
              </GlassCard>
            ) : chapters && chapters.length > 0 ? (
              <ChapterList
                chapters={chapters}
                seriesId={seriesId}
                showProgress={true}
                showMarkAll={true}
                variant="default"
                onChapterUpdate={(chapter) => {
                  // Handle chapter update if needed
                }}
              />
            ) : (
              <GlassCard className="p-8 text-center">
                <BookOpen className="mx-auto mb-4 h-12 w-12 text-slate-500" />
                <h3 className="mb-2 text-lg font-medium text-slate-300">No chapters found</h3>
                <p className="text-slate-500">This series doesn't have any chapters yet.</p>
              </GlassCard>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Reading Progress */}
          <GlassCard className="p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Reading Progress</h3>
            <SeriesProgressSummary
              series={series}
              progress={progress}
              loading={progressLoading}
            />
          </GlassCard>

          {/* Quick Actions */}
          <GlassCard className="p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Quick Actions</h3>
            <div className="space-y-3">
              {chapters && chapters.length > 0 && (
                <Button className="w-full" onClick={handleContinueReading}>
                  <Play className="mr-2 h-4 w-4" />
                  {progress?.next_unread_chapter ? 'Continue Reading' : 'Start Reading'}
                </Button>
              )}

              <Button variant="outline" className="w-full" disabled>
                <Star className="mr-2 h-4 w-4" />
                Add to Favorites
              </Button>

              <Button variant="outline" className="w-full" disabled>
                <Tag className="mr-2 h-4 w-4" />
                Manage Tags
              </Button>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}