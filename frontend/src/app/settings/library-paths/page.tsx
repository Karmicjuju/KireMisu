"use client"

import { useState, useEffect } from "react"
import { Plus, Edit, Trash2, FolderOpen, RefreshCw, HardDrive, CheckCircle, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { FileBrowserDialog } from "@/components/file-browser/file-browser-dialog"
import { 
  getLibraryPaths, 
  createLibraryPath, 
  updateLibraryPath, 
  deleteLibraryPath,
  validatePath,
  getStorageInfo
} from "@/lib/api"
import { 
  LibraryPathResponse, 
  LibraryPathCreate, 
  StorageInfo,
  PathValidationResult 
} from "@/lib/types"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { cn } from "@/lib/utils"

const libraryPathSchema = z.object({
  name: z.string().min(1, "Name is required"),
  path: z.string().min(1, "Path is required"),
  is_active: z.boolean().default(true),
  priority: z.number().default(0),
})

type LibraryPathFormValues = z.infer<typeof libraryPathSchema>

export default function LibraryPathsPage() {
  const [libraryPaths, setLibraryPaths] = useState<LibraryPathResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [showFileBrowser, setShowFileBrowser] = useState(false)
  const [editingPath, setEditingPath] = useState<LibraryPathResponse | null>(null)
  const [validationResults, setValidationResults] = useState<Map<number, PathValidationResult>>(new Map())
  const [storageInfo, setStorageInfo] = useState<Map<number, StorageInfo>>(new Map())

  const form = useForm<LibraryPathFormValues>({
    resolver: zodResolver(libraryPathSchema),
    defaultValues: {
      name: "",
      path: "",
      is_active: true,
      priority: 0,
    },
  })

  const loadLibraryPaths = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const paths = await getLibraryPaths(true) // Include inactive paths
      setLibraryPaths(paths)
      
      // Load validation status and storage info for each path
      const validationMap = new Map<number, PathValidationResult>()
      const storageMap = new Map<number, StorageInfo>()
      
      await Promise.allSettled(
        paths.map(async (path) => {
          try {
            const validation = await validatePath(path.path)
            validationMap.set(path.id, validation)
            
            if (validation.is_valid) {
              const storage = await getStorageInfo(path.id)
              storageMap.set(path.id, storage)
            }
          } catch (error) {
            console.error(`Failed to validate path ${path.id}:`, error)
          }
        })
      )
      
      setValidationResults(validationMap)
      setStorageInfo(storageMap)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load library paths")
    } finally {
      setLoading(false)
    }
  }

  const handleAddPath = async (data: LibraryPathFormValues) => {
    try {
      await createLibraryPath(data)
      await loadLibraryPaths()
      setShowAddDialog(false)
      form.reset()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create library path")
    }
  }

  const handleEditPath = async (data: LibraryPathFormValues) => {
    if (!editingPath) return
    
    try {
      await updateLibraryPath(editingPath.id, {
        name: data.name,
        is_active: data.is_active,
        priority: data.priority
      })
      await loadLibraryPaths()
      setEditingPath(null)
      form.reset()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update library path")
    }
  }

  const handleDeletePath = async (pathId: number) => {
    if (!confirm("Are you sure you want to delete this library path? This action cannot be undone.")) {
      return
    }
    
    try {
      await deleteLibraryPath(pathId)
      await loadLibraryPaths()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete library path")
    }
  }

  const handlePathSelect = (selectedPath: string) => {
    form.setValue("path", selectedPath)
    if (!form.getValues("name")) {
      // Auto-generate name from path
      const pathSegments = selectedPath.split(/[/\\]/).filter(Boolean)
      const folderName = pathSegments[pathSegments.length - 1] || "Library"
      form.setValue("name", folderName)
    }
  }

  const openAddDialog = () => {
    form.reset({
      name: "",
      path: "",
      is_active: true,
      priority: 0,
    })
    setShowAddDialog(true)
  }

  const openEditDialog = (path: LibraryPathResponse) => {
    form.reset({
      name: path.name,
      path: path.path, // Path shouldn't be editable
      is_active: path.is_active,
      priority: path.priority,
    })
    setEditingPath(path)
  }

  const formatBytes = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${Math.round(size * 100) / 100} ${units[unitIndex]}`
  }

  useEffect(() => {
    loadLibraryPaths()
  }, [])

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Library Paths</h1>
          <p className="text-muted-foreground">
            Manage your manga library storage locations
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadLibraryPaths} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button onClick={openAddDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Add Library Path
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 border border-destructive/50 bg-destructive/5 rounded-md">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Loading library paths...</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {libraryPaths.length === 0 ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <div className="text-center">
                  <HardDrive className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-semibold mb-2">No library paths configured</h3>
                  <p className="text-muted-foreground mb-4">
                    Add your first library path to start managing your manga collection
                  </p>
                  <Button onClick={openAddDialog}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Library Path
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            libraryPaths.map((path) => {
              const validation = validationResults.get(path.id)
              const storage = storageInfo.get(path.id)
              
              return (
                <Card key={path.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CardTitle className="flex items-center gap-2">
                          <HardDrive className="h-5 w-5" />
                          {path.name}
                        </CardTitle>
                        <div className="flex gap-2">
                          {path.is_active ? (
                            <Badge variant="default">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                          <Badge variant="outline">Priority: {path.priority}</Badge>
                          {validation && (
                            <Badge 
                              variant={validation.is_valid ? "default" : "destructive"}
                              className="flex items-center gap-1"
                            >
                              {validation.is_valid ? (
                                <CheckCircle className="h-3 w-3" />
                              ) : (
                                <XCircle className="h-3 w-3" />
                              )}
                              {validation.is_valid ? "Valid" : "Invalid"}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEditDialog(path)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => handleDeletePath(path.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium">Path</Label>
                      <div className="font-mono text-sm bg-muted p-2 rounded mt-1">
                        {path.path}
                      </div>
                    </div>
                    
                    {validation && !validation.is_valid && validation.error_message && (
                      <div className="p-3 bg-destructive/5 border border-destructive/20 rounded">
                        <p className="text-sm text-destructive">{validation.error_message}</p>
                      </div>
                    )}
                    
                    {storage && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <Label>Total Space</Label>
                          <p className="font-medium">{formatBytes(storage.total_space)}</p>
                        </div>
                        <div>
                          <Label>Used Space</Label>
                          <p className="font-medium">{formatBytes(storage.used_space)}</p>
                        </div>
                        <div>
                          <Label>Free Space</Label>
                          <p className="font-medium">{formatBytes(storage.free_space)}</p>
                        </div>
                        <div>
                          <Label>Usage</Label>
                          <p className="font-medium">{storage.usage_percentage.toFixed(1)}%</p>
                        </div>
                      </div>
                    )}
                    
                    <div className="flex text-xs text-muted-foreground gap-4">
                      <span>Created: {new Date(path.created_at).toLocaleDateString()}</span>
                      <span>Updated: {new Date(path.updated_at).toLocaleDateString()}</span>
                    </div>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={showAddDialog || editingPath !== null} onOpenChange={(open) => {
        if (!open) {
          setShowAddDialog(false)
          setEditingPath(null)
          form.reset()
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingPath ? "Edit Library Path" : "Add Library Path"}
            </DialogTitle>
          </DialogHeader>
          
          <Form {...form}>
            <form onSubmit={form.handleSubmit(editingPath ? handleEditPath : handleAddPath)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="My Manga Library" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="path"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Path</FormLabel>
                    <div className="flex gap-2">
                      <FormControl>
                        <Input 
                          {...field} 
                          placeholder="/path/to/manga/library" 
                          disabled={editingPath !== null} // Don't allow editing path
                        />
                      </FormControl>
                      {!editingPath && (
                        <Button 
                          type="button" 
                          variant="outline" 
                          size="sm"
                          onClick={() => setShowFileBrowser(true)}
                        >
                          <FolderOpen className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority</FormLabel>
                      <FormControl>
                        <Input 
                          {...field} 
                          type="number" 
                          min="0"
                          onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="is_active"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0 pt-6">
                      <FormControl>
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={field.onChange}
                          className="rounded"
                        />
                      </FormControl>
                      <FormLabel className="text-sm font-normal">
                        Active
                      </FormLabel>
                    </FormItem>
                  )}
                />
              </div>
              
              <DialogFooter>
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => {
                    setShowAddDialog(false)
                    setEditingPath(null)
                    form.reset()
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit">
                  {editingPath ? "Update" : "Add"} Library Path
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* File Browser Dialog */}
      <FileBrowserDialog
        open={showFileBrowser}
        onOpenChange={setShowFileBrowser}
        onSelectPath={handlePathSelect}
        initialPath="/"
      />
    </div>
  )
}