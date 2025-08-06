/**
 * Recent reading activity components
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { 
  BookOpen, 
  Star, 
  TrendingUp, 
  Clock,
  ArrowRight,
  Calendar,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { DashboardStats, RecentActivity } from '@/lib/api';

export interface RecentReadsProps {
  stats?: DashboardStats;
  loading?: boolean;
  error?: any;
  className?: string;
  maxItems?: number;
}

export function RecentReads({ 
  stats, 
  loading, 
  error, 
  className,
  maxItems = 5 
}: RecentReadsProps) {
  const recentActivity = stats?.recent_activity?.slice(0, maxItems) || [];

  const getActivityIcon = (type: RecentActivity['type']) => {
    switch (type) {
      case 'chapter_read':
        return <BookOpen className="h-4 w-4 text-orange-500" />;
      case 'series_added':
        return <Star className="h-4 w-4 text-purple-500" />;
      case 'progress_updated':
        return <TrendingUp className="h-4 w-4 text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-slate-500" />;
    }
  };

  const getActivityColor = (type: RecentActivity['type']) => {
    switch (type) {
      case 'chapter_read':
        return 'bg-orange-500/20';
      case 'series_added':
        return 'bg-purple-500/20';
      case 'progress_updated':
        return 'bg-blue-500/20';
      default:
        return 'bg-slate-500/20';
    }
  };

  if (loading) {
    return (
      <GlassCard className={cn('p-6', className)} data-testid="recent-reads">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
          <span className="ml-2 text-slate-400">Loading recent activity...</span>
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard className={cn('p-6', className)} data-testid="recent-reads">
        <div className="flex items-center justify-center py-8 text-red-500">
          <AlertTriangle className="h-8 w-8" />
          <span className="ml-2">Failed to load recent activity</span>
        </div>
      </GlassCard>
    );
  }

  if (!recentActivity.length) {
    return (
      <GlassCard className={cn('p-6', className)} data-testid="recent-reads">
        <div className="text-center py-8">
          <BookOpen className="mx-auto h-12 w-12 text-slate-500 mb-4" />
          <h3 className="text-lg font-medium text-slate-300 mb-2">No recent activity</h3>
          <p className="text-sm text-slate-500 mb-4">
            Start reading to see your activity here
          </p>
          <Button asChild size="sm">
            <Link href="/library">Browse Library</Link>
          </Button>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn('p-6', className)} data-testid="recent-reads">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
          <Button asChild variant="ghost" size="sm">
            <Link href="/library" className="text-slate-400 hover:text-white">
              View All
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </div>

        <div className="space-y-3">
          {recentActivity.map((activity, index) => (
            <div 
              key={activity.id || index} 
              className="recent-read flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-3 transition-colors hover:bg-white/10"
            >
              <div className={cn('rounded-full p-2', getActivityColor(activity.type))}>
                {getActivityIcon(activity.type)}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-white font-medium">
                      {activity.title}
                    </p>
                    {activity.subtitle && (
                      <p className="truncate text-xs text-white/60 mt-1">
                        {activity.subtitle}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0 text-right">
                    <p className="text-xs text-white/40">
                      {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </div>

              {(activity.series_id || activity.chapter_id) && (
                <Button 
                  asChild 
                  size="sm" 
                  variant="ghost" 
                  className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Link 
                    href={
                      activity.chapter_id 
                        ? `/reader/${activity.chapter_id}` 
                        : `/library/series/${activity.series_id}`
                    }
                    className="p-2"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              )}
            </div>
          ))}
        </div>

        {stats && stats.recent_activity && stats.recent_activity.length > maxItems && (
          <div className="pt-4 border-t border-white/10">
            <Button asChild variant="outline" size="sm" className="w-full">
              <Link href="/activity">
                View All Activity ({stats.recent_activity.length} items)
              </Link>
            </Button>
          </div>
        )}
      </div>
    </GlassCard>
  );
}

export interface ReadingCalendarProps {
  stats?: DashboardStats;
  loading?: boolean;
  error?: any;
  className?: string;
}

export function ReadingCalendar({ stats, loading, error, className }: ReadingCalendarProps) {
  // Generate reading activity heatmap data
  const generateHeatmapData = () => {
    if (!stats?.recent_activity) return [];
    
    const today = new Date();
    const data = [];
    
    // Generate last 30 days
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      
      const dayActivity = stats.recent_activity.filter(activity => {
        const activityDate = new Date(activity.timestamp);
        return activityDate.toDateString() === date.toDateString() &&
               activity.type === 'chapter_read';
      });
      
      data.push({
        date: date.toISOString().split('T')[0],
        count: dayActivity.length,
        level: Math.min(4, Math.floor(dayActivity.length / 2)),
      });
    }
    
    return data;
  };

  const heatmapData = generateHeatmapData();

  const getIntensityClass = (level: number) => {
    switch (level) {
      case 0: return 'bg-slate-800/50';
      case 1: return 'bg-orange-500/20';
      case 2: return 'bg-orange-500/40';
      case 3: return 'bg-orange-500/60';
      case 4: return 'bg-orange-500/80';
      default: return 'bg-slate-800/50';
    }
  };

  if (loading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <span className="ml-2 text-slate-400">Loading activity...</span>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn('p-6', className)}>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-slate-400" />
          <h3 className="text-lg font-semibold text-white">Reading Activity</h3>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-slate-400">Last 30 days</p>
          
          <div className="grid grid-cols-10 gap-1">
            {heatmapData.map((day, index) => (
              <div
                key={day.date}
                className={cn(
                  'aspect-square rounded-sm transition-all hover:scale-110',
                  getIntensityClass(day.level)
                )}
                title={`${day.date}: ${day.count} chapters read`}
              />
            ))}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Less</span>
            <div className="flex gap-1">
              {[0, 1, 2, 3, 4].map(level => (
                <div
                  key={level}
                  className={cn('w-3 h-3 rounded-sm', getIntensityClass(level))}
                />
              ))}
            </div>
            <span>More</span>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}