import { GlassCard } from '@/components/ui/glass-card';
import { BookOpen, Grid3X3, List, Search, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function Library() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Library</h1>
          <p className="text-slate-400">Browse and organize your manga collection</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm">
            <Grid3X3 className="mr-2 h-4 w-4" />
            Grid
          </Button>
          <Button variant="ghost" size="sm">
            <List className="mr-2 h-4 w-4" />
            List
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search your library..."
            className="border-slate-700/50 bg-slate-900/50 pl-10 focus:border-orange-500/50 focus:ring-orange-500/20"
          />
        </div>
        <Button variant="outline" className="flex-shrink-0">
          <Filter className="mr-2 h-4 w-4" />
          Filters
        </Button>
      </div>

      {/* Empty State */}
      <GlassCard className="p-12 text-center">
        <BookOpen className="mx-auto mb-6 h-16 w-16 text-slate-500" />
        <h2 className="mb-4 text-2xl font-semibold text-slate-300">Your library is empty</h2>
        <p className="mx-auto mb-6 max-w-md text-slate-500">
          Add some library paths in Settings and scan your manga collection to get started. You can
          also discover new series from MangaDx.
        </p>
        <div className="flex flex-col justify-center gap-3 sm:flex-row">
          <Button className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
            <BookOpen className="mr-2 h-4 w-4" />
            Go to Settings
          </Button>
          <Button variant="outline">
            <Search className="mr-2 h-4 w-4" />
            Discover Manga
          </Button>
        </div>
      </GlassCard>
    </div>
  );
}
