import SessionPageClient from './SessionPageClient';

export function generateStaticParams() {
  return [{ id: '_', sid: '_' }];
}

export default function SessionPage() {
  return <SessionPageClient />;
}
