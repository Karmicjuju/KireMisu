/**
 * Reader layout - full-screen without sidebar/header
 */

'use client';

import React from 'react';

export default function ReaderLayout({ children }: { children: React.ReactNode }) {
  return <div className="h-screen w-screen overflow-hidden bg-slate-950">{children}</div>;
}
