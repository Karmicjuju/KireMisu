"use client"

import { useState, useEffect } from "react"
import { Folder, ChevronRight, ArrowUp, HardDrive } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { browseDirectory } from "@/lib/api"
import { 
  DirectoryBrowseResponse, 
  DirectoryItem, 
  FileBrowserProps 
} from "@/lib/types"
import { cn } from "@/lib/utils"

export function FileBrowserDialog({
  open,
  onOpenChange,
  onSelectPath,
  initialPath = "/"
}: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState(initialPath)
  const [selectedPath, setSelectedPath] = useState("")
  const [browseData, setBrowseData] = useState<DirectoryBrowseResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pathInput, setPathInput] = useState(initialPath)

  const loadDirectory = async (path: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await browseDirectory(path)
      setBrowseData(data)
      setCurrentPath(data.current_path)
      setPathInput(data.current_path)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load directory")
      setBrowseData(null)
    } finally {
      setLoading(false)
    }
  }

  const navigateToPath = (path: string) => {
    loadDirectory(path)
    setSelectedPath("")
  }

  const handleItemClick = (item: DirectoryItem) => {
    if (item.is_directory) {
      navigateToPath(item.path)
    } else {
      setSelectedPath(item.path)
    }
  }

  const handleDirectorySelect = (item: DirectoryItem) => {
    if (item.is_directory) {
      setSelectedPath(item.path)
    }
  }

  const handlePathInputSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (pathInput !== currentPath) {
      navigateToPath(pathInput)
    }
  }

  const handleSelectPath = () => {
    const pathToSelect = selectedPath || currentPath
    onSelectPath(pathToSelect)
    onOpenChange(false)
  }

  useEffect(() => {
    if (open) {
      loadDirectory(initialPath)
    }
  }, [open, initialPath])

  const formatFileSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${Math.round(size * 100) / 100} ${units[unitIndex]}`
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            Choose a Folder
          </DialogTitle>
          <DialogDescription>
            Browse and select a folder to add as a library path.
          </DialogDescription>
        </DialogHeader>

        {/* Path Input */}
        <form onSubmit={handlePathInputSubmit} className="flex gap-2">
          <Input
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            placeholder="Start typing or select path"
            className="flex-1"
          />
          <Button type="submit" variant="outline" size="sm">
            Go
          </Button>
        </form>

        <p className="text-sm text-muted-foreground">
          Select a folder to enter it. Don't see your folder? Try checking / first.
        </p>

        <Separator />

        {/* Directory Browser */}
        <div className="flex-1 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-muted-foreground">Loading...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-destructive">{error}</div>
            </div>
          ) : browseData ? (
            <ScrollArea className="h-80 border rounded-md">
              <div className="space-y-1 p-2">
                {/* Parent Directory */}
                {browseData.parent_path && (
                  <>
                    <div
                      className={cn(
                        "flex items-center gap-2 p-2 rounded-md cursor-pointer hover:bg-accent",
                        selectedPath === browseData.parent_path && "bg-accent"
                      )}
                      onClick={() => handleDirectorySelect({ 
                        name: "..", 
                        path: browseData.parent_path!, 
                        is_directory: true 
                      })}
                      onDoubleClick={() => navigateToPath(browseData.parent_path!)}
                    >
                      <ArrowUp className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">..</span>
                    </div>
                    <Separator />
                  </>
                )}

                {/* Directory Items */}
                {browseData.items.map((item, index) => (
                  <div
                    key={`${item.path}-${index}`}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded-md cursor-pointer hover:bg-accent group",
                      selectedPath === item.path && "bg-accent"
                    )}
                    onClick={() => handleDirectorySelect(item)}
                    onDoubleClick={() => handleItemClick(item)}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {item.is_directory ? (
                        <Folder className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      ) : (
                        <div className="h-4 w-4 flex-shrink-0" />
                      )}
                      <span className="text-sm truncate">{item.name}</span>
                      {item.is_directory && (
                        <ChevronRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100" />
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted-foreground flex-shrink-0">
                      {!item.is_directory && item.size && (
                        <Badge variant="outline" className="text-xs">
                          {formatFileSize(item.size)}
                        </Badge>
                      )}
                      {item.modified_at && (
                        <span className="hidden sm:inline">
                          {formatDate(item.modified_at)}
                        </span>
                      )}
                    </div>
                  </div>
                ))}

                {browseData.items.length === 0 && (
                  <div className="flex items-center justify-center h-32 text-muted-foreground">
                    <div className="text-center">
                      <Folder className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">This folder is empty</p>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          ) : null}
        </div>

        <Separator />

        {/* Selected Path Display */}
        {selectedPath && (
          <div className="text-sm">
            <span className="text-muted-foreground">Selected: </span>
            <span className="font-mono bg-muted px-2 py-1 rounded">
              {selectedPath}
            </span>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSelectPath}
            disabled={!selectedPath && !currentPath}
          >
            Select Folder
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}