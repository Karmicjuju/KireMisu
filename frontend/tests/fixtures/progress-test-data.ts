/**
 * Reading Progress Test Fixtures and Utilities
 * 
 * This module provides realistic test data and utilities for testing
 * the R-2 reading progress features across different scenarios.
 */

import { faker } from '@faker-js/faker';

// Core data types matching the API schemas
export interface TestSeries {
  id: string;
  title_primary: string;
  title_alternative?: string;
  author?: string;
  artist?: string;
  genres: string[];
  status: 'ongoing' | 'completed' | 'hiatus' | 'cancelled';
  total_chapters: number;
  read_chapters: number;
  cover_art?: string;
  description?: string;
  published_year?: number;
  language: string;
  file_path: string;
  created_at: string;
  updated_at: string;
}

export interface TestChapter {
  id: string;
  series_id: string;
  chapter_number: number;
  volume_number?: number;
  title?: string;
  file_path: string;
  file_size: number;
  page_count: number;
  is_read: boolean;
  last_read_page: number;
  read_at?: string;
  started_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TestDashboardStats {
  total_series: number;
  total_chapters: number;
  chapters_read: number;
  overall_progress_percentage: number;
  series_stats: {
    completed: number;
    in_progress: number;
    unread: number;
  };
  recent_reads: Array<{
    chapter_id: string;
    series_title: string;
    chapter_title: string;
    read_at: string;
  }>;
  reading_streak_days: number;
  reading_time_hours: number;
  favorites_count: number;
  recent_activity?: Array<{
    type: 'chapter_read' | 'series_added' | 'series_completed';
    timestamp: string;
    metadata: Record<string, any>;
  }>;
}

// Test data generators
export class ProgressTestDataGenerator {
  private static getRandomGenres(): string[] {
    const allGenres = [
      'Action', 'Adventure', 'Comedy', 'Drama', 'Fantasy', 'Horror',
      'Mystery', 'Romance', 'Sci-Fi', 'Slice of Life', 'Sports', 'Thriller',
      'Supernatural', 'Historical', 'Psychological', 'Martial Arts'
    ];
    const count = faker.number.int({ min: 1, max: 4 });
    return faker.helpers.arrayElements(allGenres, count);
  }

  static generateSeries(overrides: Partial<TestSeries> = {}): TestSeries {
    const totalChapters = faker.number.int({ min: 5, max: 200 });
    const readChapters = faker.number.int({ min: 0, max: totalChapters });
    
    return {
      id: faker.string.uuid(),
      title_primary: faker.lorem.words({ min: 1, max: 4 }),
      title_alternative: faker.datatype.boolean() ? faker.lorem.words({ min: 1, max: 3 }) : undefined,
      author: faker.person.fullName(),
      artist: faker.datatype.boolean() ? faker.person.fullName() : undefined,
      genres: this.getRandomGenres(),
      status: faker.helpers.arrayElement(['ongoing', 'completed', 'hiatus', 'cancelled']),
      total_chapters: totalChapters,
      read_chapters: readChapters,
      cover_art: faker.datatype.boolean() ? faker.image.url() : undefined,
      description: faker.lorem.paragraphs(2),
      published_year: faker.number.int({ min: 1990, max: 2024 }),
      language: 'en',
      file_path: `/manga/${faker.lorem.slug()}`,
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
      ...overrides,
    };
  }

  static generateChapter(seriesId: string, chapterNumber: number, overrides: Partial<TestChapter> = {}): TestChapter {
    const pageCount = faker.number.int({ min: 15, max: 30 });
    const isRead = faker.datatype.boolean();
    const lastReadPage = isRead 
      ? pageCount - 1 
      : faker.number.int({ min: 0, max: pageCount - 1 });

    return {
      id: faker.string.uuid(),
      series_id: seriesId,
      chapter_number: chapterNumber,
      volume_number: Math.ceil(chapterNumber / 10),
      title: faker.datatype.boolean() ? faker.lorem.words({ min: 1, max: 5 }) : undefined,
      file_path: `/manga/series-${seriesId}/chapter-${chapterNumber}.cbz`,
      file_size: faker.number.int({ min: 10000000, max: 100000000 }),
      page_count: pageCount,
      is_read: isRead,
      last_read_page: lastReadPage,
      read_at: isRead ? faker.date.recent().toISOString() : undefined,
      started_at: lastReadPage > 0 ? faker.date.recent().toISOString() : undefined,
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
      ...overrides,
    };
  }

  static generateLibrary(seriesCount: number): { series: TestSeries[], chapters: TestChapter[] } {
    const series: TestSeries[] = [];
    const chapters: TestChapter[] = [];

    for (let i = 0; i < seriesCount; i++) {
      const seriesItem = this.generateSeries();
      series.push(seriesItem);

      // Generate chapters for this series
      for (let j = 1; j <= seriesItem.total_chapters; j++) {
        const chapter = this.generateChapter(seriesItem.id, j);
        chapters.push(chapter);
      }

      // Update read chapters count to match actual read chapters
      const actualReadChapters = chapters.filter(ch => 
        ch.series_id === seriesItem.id && ch.is_read
      ).length;
      seriesItem.read_chapters = actualReadChapters;
    }

    return { series, chapters };
  }

  static generateDashboardStats(series: TestSeries[], chapters: TestChapter[]): TestDashboardStats {
    const totalSeries = series.length;
    const totalChapters = chapters.length;
    const chaptersRead = chapters.filter(ch => ch.is_read).length;
    const overallProgressPercentage = totalChapters > 0 ? (chaptersRead / totalChapters) * 100 : 0;

    // Calculate series stats
    const completedSeries = series.filter(s => s.read_chapters === s.total_chapters).length;
    const unreadSeries = series.filter(s => s.read_chapters === 0).length;
    const inProgressSeries = totalSeries - completedSeries - unreadSeries;

    // Generate recent reads
    const readChapters = chapters.filter(ch => ch.is_read && ch.read_at);
    const recentReads = readChapters
      .sort((a, b) => new Date(b.read_at!).getTime() - new Date(a.read_at!).getTime())
      .slice(0, 10)
      .map(ch => {
        const chapterSeries = series.find(s => s.id === ch.series_id)!;
        return {
          chapter_id: ch.id,
          series_title: chapterSeries.title_primary,
          chapter_title: `Chapter ${ch.chapter_number}${ch.title ? ` - ${ch.title}` : ''}`,
          read_at: ch.read_at!,
        };
      });

    // Calculate reading streak
    const readingDates = readChapters
      .map(ch => new Date(ch.read_at!).toDateString())
      .filter((date, index, dates) => dates.indexOf(date) === index)
      .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());

    let streak = 0;
    const today = new Date().toDateString();
    
    for (let i = 0; i < readingDates.length; i++) {
      const date = new Date(readingDates[i]);
      const expectedDate = new Date();
      expectedDate.setDate(expectedDate.getDate() - i);
      
      if (date.toDateString() === expectedDate.toDateString()) {
        streak++;
      } else {
        break;
      }
    }

    return {
      total_series: totalSeries,
      total_chapters: totalChapters,
      chapters_read: chaptersRead,
      overall_progress_percentage: overallProgressPercentage,
      series_stats: {
        completed: completedSeries,
        in_progress: inProgressSeries,
        unread: unreadSeries,
      },
      recent_reads: recentReads,
      reading_streak_days: streak,
      reading_time_hours: faker.number.int({ min: 10, max: 500 }),
      favorites_count: faker.number.int({ min: 0, max: Math.floor(totalSeries / 3) }),
    };
  }
}

// Predefined test scenarios
export const TestScenarios = {
  // Small library for quick testing
  SMALL_LIBRARY: () => {
    const { series, chapters } = ProgressTestDataGenerator.generateLibrary(5);
    return {
      series,
      chapters,
      stats: ProgressTestDataGenerator.generateDashboardStats(series, chapters),
    };
  },

  // Medium library for realistic testing
  MEDIUM_LIBRARY: () => {
    const { series, chapters } = ProgressTestDataGenerator.generateLibrary(25);
    return {
      series,
      chapters,
      stats: ProgressTestDataGenerator.generateDashboardStats(series, chapters),
    };
  },

  // Large library for performance testing
  LARGE_LIBRARY: () => {
    const { series, chapters } = ProgressTestDataGenerator.generateLibrary(100);
    return {
      series,
      chapters,
      stats: ProgressTestDataGenerator.generateDashboardStats(series, chapters),
    };
  },

  // Empty library
  EMPTY_LIBRARY: () => ({
    series: [],
    chapters: [],
    stats: {
      total_series: 0,
      total_chapters: 0,
      chapters_read: 0,
      overall_progress_percentage: 0,
      series_stats: { completed: 0, in_progress: 0, unread: 0 },
      recent_reads: [],
      reading_streak_days: 0,
      reading_time_hours: 0,
      favorites_count: 0,
    } as TestDashboardStats,
  }),

  // Completed library (everything read)
  COMPLETED_LIBRARY: () => {
    const { series, chapters } = ProgressTestDataGenerator.generateLibrary(10);
    
    // Mark all chapters as read
    chapters.forEach(chapter => {
      chapter.is_read = true;
      chapter.last_read_page = chapter.page_count - 1;
      chapter.read_at = faker.date.recent().toISOString();
    });

    // Update series read counts
    series.forEach(seriesItem => {
      seriesItem.read_chapters = seriesItem.total_chapters;
    });

    return {
      series,
      chapters,
      stats: ProgressTestDataGenerator.generateDashboardStats(series, chapters),
    };
  },

  // Fresh library (nothing read)
  FRESH_LIBRARY: () => {
    const { series, chapters } = ProgressTestDataGenerator.generateLibrary(15);
    
    // Mark all chapters as unread
    chapters.forEach(chapter => {
      chapter.is_read = false;
      chapter.last_read_page = 0;
      chapter.read_at = undefined;
      chapter.started_at = undefined;
    });

    // Update series read counts
    series.forEach(seriesItem => {
      seriesItem.read_chapters = 0;
    });

    return {
      series,
      chapters,
      stats: ProgressTestDataGenerator.generateDashboardStats(series, chapters),
    };
  },

  // Mixed progress library (realistic usage)
  MIXED_PROGRESS_LIBRARY: () => {
    const { series, chapters } = ProgressTestDataGenerator.generateLibrary(20);
    
    // Create realistic reading patterns
    series.forEach((seriesItem, index) => {
      const seriesChapters = chapters.filter(ch => ch.series_id === seriesItem.id);
      
      if (index < 5) {
        // Completed series
        seriesChapters.forEach(chapter => {
          chapter.is_read = true;
          chapter.last_read_page = chapter.page_count - 1;
          chapter.read_at = faker.date.past().toISOString();
        });
        seriesItem.read_chapters = seriesItem.total_chapters;
      } else if (index < 12) {
        // In-progress series
        const readCount = faker.number.int({ min: 1, max: seriesItem.total_chapters - 1 });
        seriesChapters.slice(0, readCount).forEach(chapter => {
          chapter.is_read = true;
          chapter.last_read_page = chapter.page_count - 1;
          chapter.read_at = faker.date.recent().toISOString();
        });
        
        // Add partial progress to next chapter
        if (seriesChapters[readCount]) {
          seriesChapters[readCount].last_read_page = faker.number.int({ 
            min: 1, 
            max: seriesChapters[readCount].page_count - 2 
          });
          seriesChapters[readCount].started_at = faker.date.recent().toISOString();
        }
        
        seriesItem.read_chapters = readCount;
      } else {
        // Unread series
        seriesChapters.forEach(chapter => {
          chapter.is_read = false;
          chapter.last_read_page = 0;
        });
        seriesItem.read_chapters = 0;
      }
    });

    return {
      series,
      chapters,
      stats: ProgressTestDataGenerator.generateDashboardStats(series, chapters),
    };
  },
};

// Test utilities
export class ProgressTestUtils {
  static mockApiResponse(data: any, delay = 0) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          ok: true,
          json: async () => data,
          status: 200,
        });
      }, delay);
    });
  }

  static mockApiError(status = 500, message = 'Internal Server Error') {
    return Promise.resolve({
      ok: false,
      json: async () => ({ error: message }),
      status,
    });
  }

  static calculateSeriesProgress(series: TestSeries): number {
    return series.total_chapters > 0 
      ? Math.round((series.read_chapters / series.total_chapters) * 100)
      : 0;
  }

  static calculateChapterProgress(chapter: TestChapter): number {
    return chapter.page_count > 0
      ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
      : 0;
  }

  static getChaptersBySeriesId(chapters: TestChapter[], seriesId: string): TestChapter[] {
    return chapters.filter(ch => ch.series_id === seriesId)
                  .sort((a, b) => a.chapter_number - b.chapter_number);
  }

  static toggleChapterReadStatus(chapter: TestChapter): TestChapter {
    const newStatus = !chapter.is_read;
    return {
      ...chapter,
      is_read: newStatus,
      last_read_page: newStatus ? chapter.page_count - 1 : 0,
      read_at: newStatus ? new Date().toISOString() : undefined,
      started_at: newStatus ? (chapter.started_at || new Date().toISOString()) : undefined,
    };
  }

  static updateSeriesReadCount(series: TestSeries, chapters: TestChapter[]): TestSeries {
    const seriesChapters = chapters.filter(ch => ch.series_id === series.id);
    const readCount = seriesChapters.filter(ch => ch.is_read).length;
    
    return {
      ...series,
      read_chapters: readCount,
    };
  }

  static async waitForProgressUpdate(timeout = 1000): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, timeout));
  }

  static validateProgressConsistency(
    series: TestSeries[], 
    chapters: TestChapter[], 
    stats: TestDashboardStats
  ): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Check total counts
    if (stats.total_series !== series.length) {
      errors.push(`Total series mismatch: expected ${series.length}, got ${stats.total_series}`);
    }

    if (stats.total_chapters !== chapters.length) {
      errors.push(`Total chapters mismatch: expected ${chapters.length}, got ${stats.total_chapters}`);
    }

    // Check read chapters count
    const actualReadChapters = chapters.filter(ch => ch.is_read).length;
    if (stats.chapters_read !== actualReadChapters) {
      errors.push(`Read chapters mismatch: expected ${actualReadChapters}, got ${stats.chapters_read}`);
    }

    // Check overall progress percentage
    const expectedProgress = chapters.length > 0 ? (actualReadChapters / chapters.length) * 100 : 0;
    if (Math.abs(stats.overall_progress_percentage - expectedProgress) > 1) {
      errors.push(`Overall progress mismatch: expected ~${expectedProgress}%, got ${stats.overall_progress_percentage}%`);
    }

    // Check series stats
    const completedSeries = series.filter(s => s.read_chapters === s.total_chapters).length;
    const unreadSeries = series.filter(s => s.read_chapters === 0).length;
    const inProgressSeries = series.length - completedSeries - unreadSeries;

    if (stats.series_stats.completed !== completedSeries) {
      errors.push(`Completed series mismatch: expected ${completedSeries}, got ${stats.series_stats.completed}`);
    }

    if (stats.series_stats.unread !== unreadSeries) {
      errors.push(`Unread series mismatch: expected ${unreadSeries}, got ${stats.series_stats.unread}`);
    }

    if (stats.series_stats.in_progress !== inProgressSeries) {
      errors.push(`In-progress series mismatch: expected ${inProgressSeries}, got ${stats.series_stats.in_progress}`);
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }
}

// Export everything for easy access
export default {
  TestScenarios,
  ProgressTestDataGenerator,
  ProgressTestUtils,
};