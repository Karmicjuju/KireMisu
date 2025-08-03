export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex">
        <div className="text-center">
          <h1 className="mb-4 text-4xl font-bold">KireMisu</h1>
          <p className="mb-8 text-xl text-muted-foreground">
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
