import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold tracking-tight">KireMisu</h1>
        <p className="text-xl text-muted-foreground">
          Self-hosted manga library management system
        </p>
        
        <div className="space-y-4 pt-8">
          <h2 className="text-2xl font-semibold">
            Welcome to KireMisu
          </h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            Your personal manga collection awaits. Sign in to access your library.
          </p>
          
          <div className="flex gap-4 justify-center pt-4">
            <Button size="lg">Get Started</Button>
            <Button variant="outline" size="lg">Learn More</Button>
          </div>
        </div>
      </div>
    </main>
  )
}