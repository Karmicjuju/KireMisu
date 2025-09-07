import { ProtectedRoute } from "@/components/auth/ProtectedRoute"

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">Settings</h1>
        <p className="text-muted-foreground">
          Application settings will be configured here.
        </p>
      </div>
    </ProtectedRoute>
  )
}