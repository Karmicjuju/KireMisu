'use client';

import React, { useState, useEffect } from 'react';
import { Folder, FolderOpen, ArrowLeft, Home, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';

interface DirectoryItem {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number;
  modified?: number;
}

interface DirectoryListing {
  current_path: string;
  parent_path?: string;
  items: DirectoryItem[];
}

interface DirectoryPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
  initialPath?: string;
  title?: string;
}

export function DirectoryPicker({
  isOpen,
  onClose,
  onSelect,
  initialPath = '/app',
  title = 'Select Directory'
}: DirectoryPickerProps) {
  const { toast } = useToast();
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [selectedPath, setSelectedPath] = useState('');
  const [directoryListing, setDirectoryListing] = useState<DirectoryListing | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load directory contents
  const loadDirectory = async (path: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/filesystem/browse?path=${encodeURIComponent(path)}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load directory');
      }
      
      const data: DirectoryListing = await response.json();
      setDirectoryListing(data);
      setCurrentPath(data.current_path);
      setSelectedPath(data.current_path);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load directory';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Load initial directory when dialog opens
  useEffect(() => {
    if (isOpen) {
      loadDirectory(initialPath);
    }
  }, [isOpen, initialPath]);

  // Navigate to directory
  const navigateToDirectory = (path: string) => {
    loadDirectory(path);
  };

  // Navigate to parent directory
  const navigateToParent = () => {
    if (directoryListing?.parent_path) {
      navigateToDirectory(directoryListing.parent_path);
    }
  };

  // Navigate to home directory
  const navigateToHome = () => {
    navigateToDirectory('/app');
  };

  // Handle manual path input
  const handlePathInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const path = (e.target as HTMLInputElement).value;
      if (path) {
        navigateToDirectory(path);
      }
    }
  };

  // Generate breadcrumb path segments
  const getBreadcrumbs = () => {
    if (!currentPath) return [];
    
    const segments = currentPath.split('/').filter(Boolean);
    const breadcrumbs = [{ name: 'Root', path: '/' }];
    
    let accumulatedPath = '';
    for (const segment of segments) {
      accumulatedPath += '/' + segment;
      breadcrumbs.push({
        name: segment,
        path: accumulatedPath
      });
    }
    
    return breadcrumbs;
  };

  // Handle confirm selection
  const handleConfirm = () => {
    if (selectedPath) {
      onSelect(selectedPath);
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl h-[600px] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        <div className="flex-1 flex flex-col space-y-4 min-h-0 p-1">
          {/* Navigation Bar */}
          <div className="flex items-center space-x-2 flex-shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={navigateToHome}
              disabled={isLoading}
            >
              <Home className="h-4 w-4" />
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={navigateToParent}
              disabled={isLoading || !directoryListing?.parent_path}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            
            <div className="flex-1">
              <Input
                value={currentPath}
                onChange={(e) => setCurrentPath(e.target.value)}
                onKeyDown={handlePathInput}
                placeholder="Enter directory path..."
                className="font-mono text-sm focus:ring-1 focus:ring-primary/50"
              />
            </div>
          </div>

          {/* Breadcrumbs */}
          <div className="flex items-center space-x-1 text-sm text-muted-foreground flex-shrink-0">
            {getBreadcrumbs().map((crumb, index) => (
              <React.Fragment key={crumb.path}>
                {index > 0 && <ChevronRight className="h-3 w-3" />}
                <button
                  onClick={() => navigateToDirectory(crumb.path)}
                  className="hover:text-foreground transition-colors"
                  disabled={isLoading}
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
          </div>

          {/* Directory Contents */}
          <div className="flex-1 border rounded-lg min-h-0">
            <ScrollArea className="h-[300px]">
              <div className="p-2">
                {isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="text-muted-foreground">Loading...</div>
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="text-destructive">Error: {error}</div>
                  </div>
                ) : !directoryListing?.items.length ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="text-muted-foreground">Directory is empty</div>
                  </div>
                ) : (
                  <>
                    {directoryListing.items
                      .filter(item => item.is_directory) // Only show directories
                      .map((item) => (
                        <div
                          key={item.path}
                          className={`flex items-center space-x-3 p-2 rounded-lg cursor-pointer hover:bg-accent transition-colors ${
                            selectedPath === item.path ? 'bg-accent' : ''
                          }`}
                          onClick={() => setSelectedPath(item.path)}
                          onDoubleClick={() => navigateToDirectory(item.path)}
                        >
                          <div className="flex-shrink-0">
                            {selectedPath === item.path ? (
                              <FolderOpen className="h-5 w-5 text-blue-500" />
                            ) : (
                              <Folder className="h-5 w-5 text-blue-500" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{item.name}</div>
                          </div>
                        </div>
                      ))}
                  </>
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Selected Path Display */}
          {selectedPath && (
            <div className="p-3 bg-muted rounded-lg flex-shrink-0">
              <div className="text-sm text-muted-foreground">Selected path:</div>
              <div className="font-mono text-sm font-medium">{selectedPath}</div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirm} 
            disabled={!selectedPath || isLoading}
          >
            Select Directory
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}