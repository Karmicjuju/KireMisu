/**
 * Manga reader page - full-screen reading experience
 */

import React from 'react';
import { MangaReader } from '@/components/reader/manga-reader';

interface ReaderPageProps {
  params: Promise<{
    chapterId: string;
  }>;
  searchParams: Promise<{
    page?: string;
  }>;
}

export default async function ReaderPage({ params, searchParams }: ReaderPageProps) {
  const { chapterId } = await params;
  const resolvedSearchParams = await searchParams;
  const initialPage = resolvedSearchParams.page ? parseInt(resolvedSearchParams.page, 10) : 1;

  return (
    <div className="h-screen overflow-hidden">
      <MangaReader chapterId={chapterId} initialPage={initialPage} className="h-full" />
    </div>
  );
}

// Generate metadata for the page
export async function generateMetadata({ params }: { params: Promise<{ chapterId: string }> }) {
  return {
    title: 'Reading Chapter - KireMisu',
    description: 'Manga reader interface',
  };
}
