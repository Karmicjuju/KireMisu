'use client';

import { LibraryPaths } from '@/components/settings/library-paths';

export default function SettingsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-8 text-3xl font-bold">Settings</h1>

        <div className="space-y-8">
          <LibraryPaths />
        </div>
      </div>
    </div>
  );
}
