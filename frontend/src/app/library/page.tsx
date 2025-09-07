import { ProtectedRoute } from "@/components/auth/ProtectedRoute"

export default function LibraryPage() {
  return (
    <ProtectedRoute>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">Library</h1>
        <p className="text-muted-foreground">
          Your manga library will be displayed here.
        </p>
      </div>
    </ProtectedRoute>
  )
}