'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useParams } from 'next/navigation';
import useSWR from 'swr';
import api from '@/lib/api';
import { Loader2 } from 'lucide-react';

interface Chapter {
  id: string;
  chapter_number: number;
  volume_number?: number;
  is_read: boolean;
  title?: string;
}

async function getSeriesChapters(seriesId: string): Promise<Chapter[]> {
  const response = await api.get<Chapter[]>(`/api/series/${seriesId}/chapters`);
  return response.data;
}

export default function ContinueReading() {
  const params = useParams();
  const router = useRouter();
  const seriesId = params?.id as string;

  const { data: chapters, error, isLoading } = useSWR(
    seriesId ? `/api/series/${seriesId}/chapters` : null,
    () => getSeriesChapters(seriesId),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  useEffect(() => {
    if (!chapters || chapters.length === 0) return;

    // Find the first unread chapter
    const firstUnreadChapter = chapters.find(chapter => !chapter.is_read);
    
    if (firstUnreadChapter) {
      // Continue with first unread chapter
      router.replace(`/reader/${firstUnreadChapter.id}`);
    } else {
      // All chapters are read, start from the beginning or go to the last chapter
      const firstChapter = chapters[0];
      if (firstChapter) {
        router.replace(`/reader/${firstChapter.id}`);
      } else {
        // No chapters available, go back to series page
        router.replace(`/library/series/${seriesId}`);
      }
    }
  }, [chapters, router, seriesId]);

  useEffect(() => {
    if (error) {
      console.error('Failed to load chapters for continue reading:', error);
      // Redirect back to series page on error
      router.replace(`/library/series/${seriesId}`);
    }
  }, [error, router, seriesId]);

  // Show loading spinner while determining next chapter
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto" />
        <p className="mt-4 text-muted-foreground">
          Finding your next chapter...
        </p>
      </div>
    </div>
  );
}