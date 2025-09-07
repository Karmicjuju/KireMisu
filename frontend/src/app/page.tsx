import { Button } from "@/components/ui/button"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"

export default function Home() {
  return (
    <ProtectedRoute>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-lg font-semibold text-card-foreground mb-2">Welcome to KireMisu</h2>
            <p className="text-muted-foreground">
              Your self-hosted manga library management system
            </p>
            <div className="mt-4">
              <Button size="sm">Get Started</Button>
            </div>
          </div>
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-lg font-semibold text-card-foreground mb-2">Library Stats</h2>
            <p className="text-muted-foreground">
              Library statistics will be displayed here
            </p>
          </div>
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-lg font-semibold text-card-foreground mb-2">Recent Activity</h2>
            <p className="text-muted-foreground">
              Recent reading activity will be shown here
            </p>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}