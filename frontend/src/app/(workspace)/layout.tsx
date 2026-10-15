'use client';

import React from 'react';
import { WorkspaceProvider } from '@/contexts/WorkspaceContext';
import { AppShell } from '@/components/shell/AppShell';

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WorkspaceProvider>
      <AppShell>{children}</AppShell>
    </WorkspaceProvider>
  );
}
