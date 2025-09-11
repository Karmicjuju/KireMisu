"use client"

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import Link from "next/link"
import { 
  HardDrive, 
  Bell, 
  Palette, 
  Shield, 
  Download,
  ChevronRight,
  Database,
  Key,
  Globe
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface SettingsSection {
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  status?: "active" | "coming-soon" | "beta"
  isNew?: boolean
}

const settingsSections: SettingsSection[] = [
  {
    title: "Library Paths",
    description: "Manage your manga library storage locations and scanning preferences",
    href: "/settings/library-paths",
    icon: HardDrive,
    status: "active",
    isNew: true
  },
  {
    title: "Notifications",
    description: "Configure alerts for new chapters and library updates",
    href: "/settings/notifications",
    icon: Bell,
    status: "coming-soon"
  },
  {
    title: "Appearance",
    description: "Customize themes, layout density, and reading preferences",
    href: "/settings/appearance",
    icon: Palette,
    status: "coming-soon"
  },
  {
    title: "Security",
    description: "Manage passwords, two-factor authentication, and session settings",
    href: "/settings/security",
    icon: Shield,
    status: "coming-soon"
  },
  {
    title: "API Keys",
    description: "Generate and manage API keys for external integrations",
    href: "/settings/api-keys",
    icon: Key,
    status: "coming-soon"
  },
  {
    title: "MangaDex Integration",
    description: "Configure MangaDex API settings and download preferences",
    href: "/settings/mangadx",
    icon: Globe,
    status: "coming-soon"
  },
  {
    title: "Data & Backup",
    description: "Export library data, create backups, and restore settings",
    href: "/settings/backup",
    icon: Database,
    status: "coming-soon"
  },
  {
    title: "Download Manager",
    description: "Configure download queues, bandwidth limits, and storage optimization",
    href: "/settings/downloads",
    icon: Download,
    status: "coming-soon"
  }
]

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header Section */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
          <p className="text-lg text-muted-foreground">
            Customize your KireMisu experience and manage your manga library
          </p>
        </div>

        {/* Settings Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
          {settingsSections.map((section) => {
            const Icon = section.icon
            const isDisabled = section.status === "coming-soon"
            
            return (
              <Card 
                key={section.href}
                className={`relative transition-all duration-200 hover:shadow-md ${
                  isDisabled 
                    ? "opacity-60 cursor-not-allowed" 
                    : "hover:shadow-lg hover:border-primary/50 cursor-pointer"
                }`}
              >
                {isDisabled ? (
                  <div className="p-6">
                    <CardHeader className="pb-4 px-0">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="p-2 bg-muted rounded-lg">
                            <Icon className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <div className="space-y-1">
                            <CardTitle className="text-lg font-semibold flex items-center gap-2">
                              {section.title}
                              {section.status === "coming-soon" && (
                                <span className="px-2 py-1 text-xs font-medium bg-secondary text-secondary-foreground rounded-full">
                                  Coming Soon
                                </span>
                              )}
                              {section.status === "beta" && (
                                <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                  Beta
                                </span>
                              )}
                            </CardTitle>
                            <CardDescription className="text-sm">
                              {section.description}
                            </CardDescription>
                          </div>
                        </div>
                        <ChevronRight className="h-5 w-5 text-muted-foreground/50" />
                      </div>
                    </CardHeader>
                  </div>
                ) : (
                  <Link href={section.href} className="block">
                    <div className="p-6">
                      <CardHeader className="pb-4 px-0">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 bg-primary/10 rounded-lg">
                              <Icon className="h-5 w-5 text-primary" />
                            </div>
                            <div className="space-y-1">
                              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                                {section.title}
                                {section.isNew && (
                                  <span className="px-2 py-1 text-xs font-medium bg-emerald-100 text-emerald-800 rounded-full">
                                    New
                                  </span>
                                )}
                                {section.status === "beta" && (
                                  <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                    Beta
                                  </span>
                                )}
                              </CardTitle>
                              <CardDescription className="text-sm">
                                {section.description}
                              </CardDescription>
                            </div>
                          </div>
                          <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
                        </div>
                      </CardHeader>
                    </div>
                  </Link>
                )}
                
                {/* New feature indicator */}
                {section.isNew && (
                  <div className="absolute top-2 right-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                  </div>
                )}
              </Card>
            )
          })}
        </div>

        {/* Quick Actions Footer */}
        <Card className="bg-muted/30">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <h3 className="font-semibold text-foreground">Need Help?</h3>
                <p className="text-sm text-muted-foreground">
                  Check our documentation or get support from the community
                </p>
              </div>
              <div className="flex space-x-2">
                <Button variant="outline" size="sm">
                  Documentation
                </Button>
                <Button variant="outline" size="sm">
                  Community
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}