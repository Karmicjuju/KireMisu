'use client';

import useSWR from 'swr';
import { GlassCard } from '@/components/ui/glass-card';
import { Book, BookOpen, Clock, TrendingUp } from 'lucide-react';
import { seriesApi, type SeriesResponse } from '@/lib/api';

export function LibraryStats() {
  // Fetch series list with SWR
  const { data: seriesList } = useSWR<SeriesResponse[]>(
    'series-list',
    () => seriesApi.getSeriesList(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  );

  // Calculate stats from actual data
  const stats = seriesList ? {
    total: seriesList.length,
    unread: seriesList.filter(s => s.read_chapters === 0).length,
    inProgress: seriesList.filter(s => s.read_chapters > 0 && s.read_chapters < s.total_chapters).length,
    completed: seriesList.filter(s => s.read_chapters === s.total_chapters && s.total_chapters > 0).length,
  } : { total: 0, unread: 0, inProgress: 0, completed: 0 };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <GlassCard className="p-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-500/20 rounded-md">
            <Book className="h-3.5 w-3.5 text-blue-500" />
          </div>
          <div>
            <div className="text-lg font-bold">{stats.total}</div>
            <div className="text-xs text-muted-foreground">Total Series</div>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-orange-500/20 rounded-md">
            <Clock className="h-3.5 w-3.5 text-orange-500" />
          </div>
          <div>
            <div className="text-lg font-bold">{stats.inProgress}</div>
            <div className="text-xs text-muted-foreground">In Progress</div>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-green-500/20 rounded-md">
            <TrendingUp className="h-3.5 w-3.5 text-green-500" />
          </div>
          <div>
            <div className="text-lg font-bold">{stats.completed}</div>
            <div className="text-xs text-muted-foreground">Completed</div>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-gray-500/20 rounded-md">
            <BookOpen className="h-3.5 w-3.5 text-gray-500" />
          </div>
          <div>
            <div className="text-lg font-bold">{stats.unread}</div>
            <div className="text-xs text-muted-foreground">Unread</div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}