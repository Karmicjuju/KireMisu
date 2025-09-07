import { ProtectedRoute } from "@/components/auth/ProtectedRoute"

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">User Profile</h1>
        <p className="text-muted-foreground">
          User profile settings and information will be displayed here.
        </p>
      </div>
    </ProtectedRoute>
  )
}