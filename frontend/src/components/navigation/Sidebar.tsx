"use client"

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  BookOpen, 
  Settings, 
  User, 
  Menu,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

interface NavigationItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  position: 'top' | 'bottom'
}

const navigationItems: NavigationItem[] = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, position: 'top' },
  { name: 'Library', href: '/library', icon: BookOpen, position: 'top' },
  { name: 'Settings', href: '/settings', icon: Settings, position: 'bottom' },
  { name: 'User Profile', href: '/profile', icon: User, position: 'bottom' },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const pathname = usePathname()

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (mobile) {
        setIsCollapsed(true)
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const topItems = navigationItems.filter(item => item.position === 'top')
  const bottomItems = navigationItems.filter(item => item.position === 'bottom')

  const NavContent = () => (
    <div className="flex h-full flex-col bg-card border-r border-border">
      {/* Header with toggle */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-border">
        {!isCollapsed && (
          <span className="text-lg font-semibold text-card-foreground">KireMisu</span>
        )}
        {!isMobile && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="h-8 w-8 text-muted-foreground hover:text-card-foreground hover:bg-muted"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        )}
      </div>

      {/* Navigation content */}
      <div className="flex flex-1 flex-col justify-between p-4">
        {/* Top navigation items */}
        <nav className="space-y-2">
          {topItems.map((item) => {
            const isActive = pathname === item.href
            const IconComponent = item.icon
            
            const linkContent = (
              <Link
                href={item.href}
                className={cn(
                  "flex items-center rounded-lg text-sm font-medium transition-all hover:bg-muted",
                  isCollapsed ? "px-2 py-3" : "px-3 py-2",
                  isActive 
                    ? "bg-primary text-primary-foreground hover:bg-primary/90" 
                    : "text-muted-foreground hover:text-card-foreground",
                  isCollapsed ? "justify-center" : "justify-start"
                )}
              >
                <IconComponent className={cn(isCollapsed ? "h-6 w-6" : "h-5 w-5", !isCollapsed && "mr-3")} />
                {!isCollapsed && <span>{item.name}</span>}
              </Link>
            )

            if (isCollapsed && !isMobile) {
              return (
                <TooltipProvider key={item.name}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      {linkContent}
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>{item.name}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )
            }

            return <div key={item.name}>{linkContent}</div>
          })}
        </nav>

        {/* Bottom navigation items */}
        <nav className="space-y-2">
          {bottomItems.map((item) => {
            const isActive = pathname === item.href
            const IconComponent = item.icon
            
            const linkContent = (
              <Link
                href={item.href}
                className={cn(
                  "flex items-center rounded-lg text-sm font-medium transition-all hover:bg-muted",
                  isCollapsed ? "px-2 py-3" : "px-3 py-2",
                  isActive 
                    ? "bg-primary text-primary-foreground hover:bg-primary/90" 
                    : "text-muted-foreground hover:text-card-foreground",
                  isCollapsed ? "justify-center" : "justify-start"
                )}
              >
                <IconComponent className={cn(isCollapsed ? "h-6 w-6" : "h-5 w-5", !isCollapsed && "mr-3")} />
                {!isCollapsed && <span>{item.name}</span>}
              </Link>
            )

            if (isCollapsed && !isMobile) {
              return (
                <TooltipProvider key={item.name}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      {linkContent}
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>{item.name}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )
            }

            return <div key={item.name}>{linkContent}</div>
          })}
        </nav>
      </div>
    </div>
  )

  if (isMobile) {
    return (
      <Sheet>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="fixed left-4 top-4 z-40 h-10 w-10 bg-card text-card-foreground hover:bg-muted md:hidden"
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <NavContent />
        </SheetContent>
      </Sheet>
    )
  }

  return (
    <div className={cn(
      "hidden md:flex md:flex-col md:fixed md:inset-y-0 md:left-0 md:z-50 transition-all duration-300",
      isCollapsed ? "md:w-18" : "md:w-60",
      className
    )}>
      <NavContent />
    </div>
  )
}