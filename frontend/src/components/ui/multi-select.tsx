"use client"

import * as React from "react"
import { X, Check, ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface MultiSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyMessage?: string
  className?: string
  disabled?: boolean
  maxItems?: number
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Select items...",
  searchPlaceholder = "Search items...",
  emptyMessage = "No items found",
  className,
  disabled = false,
  maxItems,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [searchTerm, setSearchTerm] = React.useState("")
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  // Filter options based on search term
  const filteredOptions = React.useMemo(() => {
    return options.filter(option =>
      option.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [options, searchTerm])

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false)
        setSearchTerm("")
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleUnselect = React.useCallback((item: string) => {
    onChange(selected.filter((s) => s !== item))
  }, [onChange, selected])

  const handleSelect = React.useCallback((item: string) => {
    if (selected.includes(item)) {
      handleUnselect(item)
    } else {
      if (maxItems && selected.length >= maxItems) {
        return
      }
      onChange([...selected, item])
    }
  }, [onChange, selected, handleUnselect, maxItems])

  const handleToggleDropdown = () => {
    if (!disabled) {
      setOpen(!open)
      if (!open) {
        setSearchTerm("")
      }
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="outline"
        role="combobox"
        aria-expanded={open}
        className={cn(
          "w-full justify-between min-h-[2.5rem] h-auto text-left",
          className
        )}
        disabled={disabled}
        onClick={handleToggleDropdown}
      >
        <div className="flex gap-1 flex-wrap flex-1">
          {selected.length > 0 ? (
            selected.map((item) => (
              <Badge
                variant="secondary"
                key={item}
                className="mr-1 mb-1"
              >
                {item}
                <button
                  className="ml-1 ring-offset-background rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      e.stopPropagation()
                      handleUnselect(item)
                    }
                  }}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                  }}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleUnselect(item)
                  }}
                >
                  <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                </button>
              </Badge>
            ))
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </div>
        <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
      </Button>

      {open && (
        <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-lg">
          <div className="p-2">
            <Input
              placeholder={searchPlaceholder}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8"
            />
          </div>
          <ScrollArea className="max-h-64">
            <div className="p-1">
              {filteredOptions.length === 0 ? (
                <div className="py-6 text-center text-sm text-muted-foreground">
                  {emptyMessage}
                </div>
              ) : (
                filteredOptions.map((option) => (
                  <div
                    key={option}
                    className="flex items-center space-x-2 p-2 hover:bg-accent hover:text-accent-foreground cursor-pointer rounded-sm"
                    onClick={() => handleSelect(option)}
                  >
                    <Checkbox
                      checked={selected.includes(option)}
                      onChange={() => handleSelect(option)}
                    />
                    <span className="flex-1">{option}</span>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  )
}