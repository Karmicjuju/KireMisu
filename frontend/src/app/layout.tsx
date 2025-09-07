import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { NavigationLayout } from '@/components/navigation/NavigationLayout'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'KireMisu',
  description: 'Self-hosted manga library management system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <NavigationLayout>{children}</NavigationLayout>
      </body>
    </html>
  )
}