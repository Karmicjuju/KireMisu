'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { 
  Plus, 
  Settings, 
  Search, 
  RefreshCw,
  ScanLine,
  Filter 
} from 'lucide-react';
import Link from 'next/link';
import { MangaDxSearchDialog } from '@/components/mangadx';

export function QuickActions() {
  const [showMangaDxDialog, setShowMangaDxDialog] = useState(false);

  const handleImportSuccess = () => {
    // Will be handled by global state refresh
    setShowMangaDxDialog(false);
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowMangaDxDialog(true)}
          className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white border-0"
        >
          <Search className="mr-2 h-4 w-4" />
          Discover
        </Button>
        <Button variant="outline" size="sm">
          <ScanLine className="mr-2 h-4 w-4" />
          Scan Library
        </Button>
        <Button variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/settings">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Link>
        </Button>
      </div>

      <MangaDxSearchDialog
        open={showMangaDxDialog}
        onOpenChange={setShowMangaDxDialog}
        onImportSuccess={handleImportSuccess}
      />
    </>
  );
}