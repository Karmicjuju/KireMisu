import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { NavigationLayout } from '@/components/navigation/NavigationLayout'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { AuthProvider } from '@/components/providers/AuthProvider'

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
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange={false}
        >
          <AuthProvider>
            <NavigationLayout>{children}</NavigationLayout>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}