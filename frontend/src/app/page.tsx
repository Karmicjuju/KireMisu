export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">KireMisu</h1>
          <p className="text-xl text-muted-foreground mb-8">
            Self-hosted manga reader and library management system
          </p>
          <div className="space-y-2 text-left">
            <p className="text-sm">🚧 Under Development</p>
            <p className="text-sm">📚 Manga Library Management</p>
            <p className="text-sm">🔍 MangaDx Integration</p>
            <p className="text-sm">📖 Advanced Reading Experience</p>
            <p className="text-sm">🏷️ Custom Tagging & Organization</p>
          </div>
        </div>
      </div>
    </main>
  );
}