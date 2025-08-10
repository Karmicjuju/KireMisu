'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Settings, RotateCcw, Save, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

export interface PollingSettings {
  /** Initial polling interval when starting up (seconds) */
  initialInterval: number;
  /** Active polling interval when downloads are running (seconds) */
  activeInterval: number;
  /** Maximum polling interval when idle (seconds) */
  maxInterval: number;
  /** Maximum consecutive errors before backing off */
  maxConsecutiveErrors: number;
}

const DEFAULT_SETTINGS: PollingSettings = {
  initialInterval: 120,    // 2 minutes - less aggressive
  activeInterval: 60,      // 1 minute when active - less frequent
  maxInterval: 600,        // 10 minutes - longer idle intervals
  maxConsecutiveErrors: 3,
};

const VALIDATION_RULES = {
  initialInterval: { min: 10, max: 600, name: 'Initial Interval' },
  activeInterval: { min: 5, max: 300, name: 'Active Interval' },
  maxInterval: { min: 60, max: 1800, name: 'Maximum Interval' },
  maxConsecutiveErrors: { min: 1, max: 10, name: 'Max Consecutive Errors' },
};

interface ValidationError {
  field: keyof PollingSettings;
  message: string;
}

function validateSettings(settings: PollingSettings): ValidationError[] {
  const errors: ValidationError[] = [];

  // Validate individual field ranges
  (Object.keys(VALIDATION_RULES) as Array<keyof PollingSettings>).forEach((field) => {
    const rule = VALIDATION_RULES[field];
    const value = settings[field];
    
    if (value < rule.min || value > rule.max) {
      errors.push({
        field,
        message: `${rule.name} must be between ${rule.min} and ${rule.max}`,
      });
    }
  });

  // Cross-field validation
  if (settings.activeInterval > settings.initialInterval) {
    errors.push({
      field: 'activeInterval',
      message: 'Active interval should not be greater than initial interval',
    });
  }

  if (settings.initialInterval > settings.maxInterval) {
    errors.push({
      field: 'initialInterval',
      message: 'Initial interval should not be greater than maximum interval',
    });
  }

  return errors;
}

function formatTimeDisplay(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const remainingMinutes = Math.floor((seconds % 3600) / 60);
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  }
}

export function PollingSettings() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [settings, setSettings] = useState<PollingSettings>(DEFAULT_SETTINGS);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const { toast } = useToast();

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const savedSettings = localStorage.getItem('kiremisu-polling-settings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        // Merge with defaults to handle missing fields
        const mergedSettings = { ...DEFAULT_SETTINGS, ...parsed };
        setSettings(mergedSettings);
      }
    } catch (error) {
      console.warn('Failed to load polling settings from localStorage:', error);
      toast({
        title: 'Settings Load Warning',
        description: 'Could not load saved settings. Using defaults.',
        variant: 'destructive',
      });
    }
  }, [toast]);

  // Validate settings whenever they change
  useEffect(() => {
    const errors = validateSettings(settings);
    setValidationErrors(errors);
  }, [settings]);

  const updateSetting = useCallback((field: keyof PollingSettings, value: number) => {
    setSettings(prev => ({ ...prev, [field]: value }));
    setIsDirty(true);
  }, []);

  const handleSave = async () => {
    if (validationErrors.length > 0) {
      toast({
        title: 'Validation Error',
        description: 'Please fix validation errors before saving.',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      localStorage.setItem('kiremisu-polling-settings', JSON.stringify(settings));
      setIsDirty(false);
      
      // Dispatch custom event to notify other components
      window.dispatchEvent(new CustomEvent('polling-settings-updated', {
        detail: settings,
      }));

      toast({
        title: 'Settings Saved',
        description: 'Polling settings have been updated successfully.',
      });
    } catch (error) {
      toast({
        title: 'Save Error',
        description: 'Failed to save settings. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    setIsDirty(true);
    toast({
      title: 'Settings Reset',
      description: 'Polling settings have been reset to defaults.',
    });
  };

  const getFieldError = (field: keyof PollingSettings): string | undefined => {
    return validationErrors.find((error) => error.field === field)?.message;
  };

  return (
    <div className="space-y-6">
      {/* Collapsible Header */}
      <div 
        className="flex items-center justify-between cursor-pointer rounded-lg border border-border bg-card p-4 hover:bg-orange-500/10 hover:border-orange-500/20 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            )}
            <Settings className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold">
              Download Polling Settings
            </h2>
            <p className="text-sm text-muted-foreground">
              Configure how frequently KireMisu checks for download updates
            </p>
          </div>
        </div>
        {/* Show status indicators when collapsed */}
        {!isExpanded && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>Initial: {formatTimeDisplay(settings.initialInterval)}</span>
            <span>•</span>
            <span>Active: {formatTimeDisplay(settings.activeInterval)}</span>
            {isDirty && (
              <>
                <span>•</span>
                <div className="w-2 h-2 rounded-full bg-orange-500" title="Unsaved changes" />
              </>
            )}
          </div>
        )}
      </div>
      
      {/* Collapsible Content */}
      {isExpanded && (
        <div className="space-y-6 pl-6">
          <div className="flex items-center justify-end gap-2">
            <Button
              onClick={handleReset}
              variant="outline"
              size="sm"
              disabled={isSaving}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Reset
            </Button>
            <Button
              onClick={handleSave}
              size="sm"
              disabled={!isDirty || validationErrors.length > 0 || isSaving}
            >
              <Save className="mr-2 h-4 w-4" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>

          {validationErrors.length > 0 && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
              <div className="flex items-center gap-2 text-destructive mb-2">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-medium">Validation Errors</span>
              </div>
              <ul className="text-sm text-destructive space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index}>• {error.message}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            {/* Initial Polling Interval */}
            <div className="space-y-3">
              <div>
                <label htmlFor="initialInterval" className="text-sm font-medium">
                  Initial Polling Interval
                </label>
                <p className="text-xs text-muted-foreground">
                  Default interval when starting up ({formatTimeDisplay(settings.initialInterval)})
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Input
                    id="initialInterval"
                    type="number"
                    min={VALIDATION_RULES.initialInterval.min}
                    max={VALIDATION_RULES.initialInterval.max}
                    value={settings.initialInterval}
                    onChange={(e) => updateSetting('initialInterval', parseInt(e.target.value) || 0)}
                    className={cn(
                      'w-24',
                      getFieldError('initialInterval') && 'border-destructive'
                    )}
                  />
                  <span className="text-sm text-muted-foreground">seconds</span>
                </div>
                {getFieldError('initialInterval') && (
                  <p className="text-xs text-destructive">{getFieldError('initialInterval')}</p>
                )}
              </div>
            </div>

            {/* Active Polling Interval */}
            <div className="space-y-3">
              <div>
                <label htmlFor="activeInterval" className="text-sm font-medium">
                  Active Polling Interval
                </label>
                <p className="text-xs text-muted-foreground">
                  Faster interval when downloads are running ({formatTimeDisplay(settings.activeInterval)})
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Input
                    id="activeInterval"
                    type="number"
                    min={VALIDATION_RULES.activeInterval.min}
                    max={VALIDATION_RULES.activeInterval.max}
                    value={settings.activeInterval}
                    onChange={(e) => updateSetting('activeInterval', parseInt(e.target.value) || 0)}
                    className={cn(
                      'w-24',
                      getFieldError('activeInterval') && 'border-destructive'
                    )}
                  />
                  <span className="text-sm text-muted-foreground">seconds</span>
                </div>
                {getFieldError('activeInterval') && (
                  <p className="text-xs text-destructive">{getFieldError('activeInterval')}</p>
                )}
              </div>
            </div>

            {/* Maximum Polling Interval */}
            <div className="space-y-3">
              <div>
                <label htmlFor="maxInterval" className="text-sm font-medium">
                  Maximum Polling Interval
                </label>
                <p className="text-xs text-muted-foreground">
                  Slowest interval when idle for long periods ({formatTimeDisplay(settings.maxInterval)})
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Input
                    id="maxInterval"
                    type="number"
                    min={VALIDATION_RULES.maxInterval.min}
                    max={VALIDATION_RULES.maxInterval.max}
                    value={settings.maxInterval}
                    onChange={(e) => updateSetting('maxInterval', parseInt(e.target.value) || 0)}
                    className={cn(
                      'w-24',
                      getFieldError('maxInterval') && 'border-destructive'
                    )}
                  />
                  <span className="text-sm text-muted-foreground">seconds</span>
                </div>
                {getFieldError('maxInterval') && (
                  <p className="text-xs text-destructive">{getFieldError('maxInterval')}</p>
                )}
              </div>
            </div>

            {/* Max Consecutive Errors */}
            <div className="space-y-3">
              <div>
                <label htmlFor="maxConsecutiveErrors" className="text-sm font-medium">
                  Max Consecutive Errors
                </label>
                <p className="text-xs text-muted-foreground">
                  Number of errors before backing off ({settings.maxConsecutiveErrors} errors)
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Input
                    id="maxConsecutiveErrors"
                    type="number"
                    min={VALIDATION_RULES.maxConsecutiveErrors.min}
                    max={VALIDATION_RULES.maxConsecutiveErrors.max}
                    value={settings.maxConsecutiveErrors}
                    onChange={(e) => updateSetting('maxConsecutiveErrors', parseInt(e.target.value) || 0)}
                    className={cn(
                      'w-24',
                      getFieldError('maxConsecutiveErrors') && 'border-destructive'
                    )}
                  />
                  <span className="text-sm text-muted-foreground">errors</span>
                </div>
                {getFieldError('maxConsecutiveErrors') && (
                  <p className="text-xs text-destructive">{getFieldError('maxConsecutiveErrors')}</p>
                )}
              </div>
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <h4 className="font-medium text-foreground">How Polling Works</h4>
            <div className="text-sm text-muted-foreground space-y-1">
              <p><strong>Adaptive Polling Strategy</strong></p>
              <p>KireMisu uses an adaptive polling system that adjusts the frequency based on download activity:</p>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li><strong>Active downloads:</strong> Uses the active interval ({formatTimeDisplay(settings.activeInterval)}) for real-time updates</li>
                <li><strong>No activity:</strong> Gradually increases interval up to maximum ({formatTimeDisplay(settings.maxInterval)}) to save resources</li>
                <li><strong>Errors:</strong> After {settings.maxConsecutiveErrors} consecutive errors, polling pauses temporarily</li>
              </ul>
            </div>
          </div>
          
          <div className="space-y-2">
            <h4 className="font-medium text-foreground">Recommended Settings</h4>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg border bg-card p-3">
                <div className="font-medium text-foreground mb-1">Light Usage</div>
                <div className="text-xs">
                  Initial: 2m • Active: 1m • Max: 10m • Errors: 3
                </div>
              </div>
              <div className="rounded-lg border bg-card p-3">
                <div className="font-medium text-foreground mb-1">Heavy Usage</div>
                <div className="text-xs">
                  Initial: 30s • Active: 15s • Max: 5m • Errors: 5
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Hook to get current polling settings from localStorage
 */
export function usePollingSettings(): PollingSettings {
  const [settings, setSettings] = useState<PollingSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    // Load initial settings
    try {
      const savedSettings = localStorage.getItem('kiremisu-polling-settings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      }
    } catch (error) {
      console.warn('Failed to load polling settings:', error);
    }

    // Listen for settings updates
    const handleSettingsUpdate = (event: CustomEvent) => {
      setSettings(event.detail);
    };

    window.addEventListener('polling-settings-updated', handleSettingsUpdate as EventListener);

    return () => {
      window.removeEventListener('polling-settings-updated', handleSettingsUpdate as EventListener);
    };
  }, []);

  return settings;
}