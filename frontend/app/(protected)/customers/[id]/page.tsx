import CustomerDetailClient from './CustomerDetailClient';

export function generateStaticParams() {
  return [{ id: '_' }];
}

export default function CustomerDetailPage() {
  return <CustomerDetailClient />;
}
