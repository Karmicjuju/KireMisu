/**
 * Dashboard progress statistics components
 */

'use client';

import React from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { ProgressBar } from '@/components/ui/progress-bar';
import { cn } from '@/lib/utils';
import { 
  BookOpen, 
  TrendingUp, 
  Clock, 
  Star, 
  Target,
  Flame,
  Trophy,
  Calendar,
  Loader2, 
  AlertTriangle 
} from 'lucide-react';
import type { DashboardStats } from '@/lib/api';

export interface ProgressStatsProps {
  stats?: DashboardStats;
  loading?: boolean;
  error?: any;
  className?: string;
}

export function ProgressStats({ stats, loading, error, className }: ProgressStatsProps) {
  const formatReadingTime = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  };

  const overallProgress = stats && stats.total_chapters > 0 
    ? Math.round((stats.chapters_read / stats.total_chapters) * 100)
    : 0;

  return (
    <div className={cn('space-y-6', className)} data-testid="dashboard-stats">
      {/* Main Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Series */}
        <GlassCard className="p-6">
          <div className="flex items-center space-x-4">
            <div className="rounded-full bg-orange-500/20 p-3">
              <BookOpen className="h-6 w-6 text-orange-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-400">Total Series</p>
              <div className="flex items-center gap-2">
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : error ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <p className="text-2xl font-bold" data-testid="total-series">
                    {stats?.total_series ?? 0}
                  </p>
                )}
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Chapters Progress */}
        <GlassCard className="p-6">
          <div className="flex items-center space-x-4">
            <div className="rounded-full bg-blue-500/20 p-3">
              <TrendingUp className="h-6 w-6 text-blue-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-400">Chapters Read</p>
              <div className="flex items-center gap-2">
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : error ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <>
                    <p className="text-2xl font-bold" data-testid="read-chapters">
                      {stats?.chapters_read ?? 0}
                    </p>
                    {stats && stats.total_chapters > 0 && (
                      <span className="text-sm text-slate-400" data-testid="total-chapters">
                        / {stats.total_chapters}
                      </span>
                    )}
                  </>
                )}
              </div>
              {stats && stats.total_chapters > 0 && (
                <div className="mt-2">
                  <ProgressBar
                    value={stats.chapters_read}
                    max={stats.total_chapters}
                    size="sm"
                    variant="subtle"
                    colorScheme="info"
                    data-testid="chapters-progress-bar"
                  />
                </div>
              )}
            </div>
          </div>
        </GlassCard>

        {/* Reading Time */}
        <GlassCard className="p-6">
          <div className="flex items-center space-x-4">
            <div className="rounded-full bg-green-500/20 p-3">
              <Clock className="h-6 w-6 text-green-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-400">Reading Time</p>
              <div className="flex items-center gap-2">
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : error ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <p className="text-2xl font-bold" data-testid="reading-time">
                    {formatReadingTime(stats?.reading_time_hours ?? 0)}
                  </p>
                )}
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Favorites */}
        <GlassCard className="p-6">
          <div className="flex items-center space-x-4">
            <div className="rounded-full bg-purple-500/20 p-3">
              <Star className="h-6 w-6 text-purple-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-400">Favorites</p>
              <div className="flex items-center gap-2">
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : error ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <p className="text-2xl font-bold" data-testid="favorites-count">
                    {stats?.favorites_count ?? 0}
                  </p>
                )}
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Overall Progress Card */}
      {stats && stats.total_chapters > 0 && (
        <GlassCard className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-gradient-to-r from-orange-500 to-red-500 p-3">
                  <Target className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Overall Progress</h3>
                  <p className="text-sm text-slate-400">Your manga reading journey</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-white" data-testid="overall-progress">
                  {overallProgress}%
                </p>
                <p className="text-sm text-slate-400">Complete</p>
              </div>
            </div>

            <ProgressBar
              value={stats.chapters_read}
              max={stats.total_chapters}
              size="lg"
              colorScheme="primary"
              showValue={false}
              animated={true}
              className="mt-4"
              data-testid="overall-progress-bar"
            />

            <div className="grid grid-cols-3 gap-4 pt-2" data-testid="series-breakdown">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-500">
                  {stats.total_series > 0 ? 
                    Math.round((stats.chapters_read / stats.total_chapters) * stats.total_series) : 0}
                </p>
                <p className="text-xs text-slate-400">Completed:</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-orange-500">
                  {stats.total_series > 0 ? 
                    Math.max(0, stats.total_series - Math.round((stats.chapters_read / stats.total_chapters) * stats.total_series)) : 0}
                </p>
                <p className="text-xs text-slate-400">In Progress:</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-400">
                  {Math.max(0, stats.total_series - stats.chapters_read)}
                </p>
                <p className="text-xs text-slate-400">Unread:</p>
              </div>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}

export interface ReadingStreakProps {
  stats?: DashboardStats;
  loading?: boolean;
  error?: any;
  className?: string;
}

export function ReadingStreak({ stats, loading, error, className }: ReadingStreakProps) {
  // Calculate reading streak from recent activity
  const calculateStreak = () => {
    if (!stats?.recent_activity) return 0;
    
    const today = new Date();
    let streak = 0;
    const activityDates = new Set<string>();
    
    stats.recent_activity
      .filter(activity => activity.type === 'chapter_read')
      .forEach(activity => {
        const activityDate = new Date(activity.timestamp).toDateString();
        activityDates.add(activityDate);
      });
    
    // Count consecutive days with reading activity
    for (let i = 0; i < 30; i++) {
      const checkDate = new Date(today);
      checkDate.setDate(today.getDate() - i);
      
      if (activityDates.has(checkDate.toDateString())) {
        streak++;
      } else if (i > 0) {
        break;
      }
    }
    
    return streak;
  };

  const streak = calculateStreak();

  return (
    <GlassCard className={cn('p-6', className)} data-testid="reading-streak">
      <div className="flex items-center space-x-4">
        <div className="rounded-full bg-gradient-to-r from-orange-500 to-red-500 p-3">
          <Flame className="h-6 w-6 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-white">Reading Streak</h3>
          <div className="flex items-baseline gap-2">
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
            ) : error ? (
              <AlertTriangle className="h-5 w-5 text-red-500" />
            ) : (
              <>
                <span className="text-3xl font-bold text-white">{streak}</span>
                <span className="text-sm text-slate-400">
                  day{streak !== 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            {streak > 0 ? 'Keep it up!' : 'Start your streak today!'}
          </p>
        </div>
        {streak >= 7 && (
          <div className="text-yellow-500">
            <Trophy className="h-8 w-8" />
          </div>
        )}
      </div>
    </GlassCard>
  );
}