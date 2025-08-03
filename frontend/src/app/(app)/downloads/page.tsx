import { GlassCard } from '@/components/ui/glass-card';
import { Download, Pause, Play, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Downloads() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Downloads</h1>
          <p className="text-slate-400">Manage your manga downloads and queue</p>
        </div>
        <Button className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
          <Download className="mr-2 h-4 w-4" />
          Add Download
        </Button>
      </div>

      {/* Download Queue */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Active Downloads</h2>
        <GlassCard className="p-8 text-center">
          <Download className="mx-auto mb-4 h-12 w-12 text-slate-500" />
          <h3 className="mb-2 text-lg font-medium text-slate-300">No active downloads</h3>
          <p className="text-sm text-slate-500">
            Download manga from MangaDx or add chapters to your queue
          </p>
        </GlassCard>
      </div>

      {/* Download History */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Recent Downloads</h2>
        <GlassCard className="p-8 text-center">
          <Download className="mx-auto mb-4 h-12 w-12 text-slate-500" />
          <h3 className="mb-2 text-lg font-medium text-slate-300">No download history</h3>
          <p className="text-sm text-slate-500">Your completed downloads will appear here</p>
        </GlassCard>
      </div>
    </div>
  );
}
