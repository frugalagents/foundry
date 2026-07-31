import type { Metadata } from 'next';
import { ArchitectureWorkspaceLive } from '@/components/architecture-workspace/ArchitectureWorkspaceLive';

export const metadata: Metadata = {
  title: 'Architecture Workspace | Platform Advisor',
  description: 'Architecture-first coding agent platform workspace.',
};

export default function ArchitecturePage() {
  return <ArchitectureWorkspaceLive />;
}
