import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Enterprise AI Foundry',
  description: 'Agent-first platform for Coding, Product, and Fabric solutions',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  )
}
