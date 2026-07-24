/**
 * Factory for creating appropriate collectors based on configuration
 */

import { BaseCollector } from './BaseCollector'
import { LegacyCollector } from './LegacyCollector'
import { MinimalCollector } from './MinimalCollector'
import { CustomCollector } from './CustomCollector'

export enum CollectorType {
  LEGACY = 'legacy',
  MINIMAL = 'minimal',
  CUSTOM = 'custom'
}

export interface CollectorConfig {
  customFunction?: Function
  shouldGridReturn?: Function
  /** DataReturnMode as sent by Python, e.g. 'MINIMAL' or 'FILTERED'. */
  dataReturnMode?: string
}

/**
 * Determine and create the appropriate collector based on configuration
 */
export function determineCollector(config: CollectorConfig = {}): BaseCollector {
  // If a custom collector function is provided, use CustomCollector
  if (config.customFunction &&
      config.customFunction !== null &&
      typeof config.customFunction === 'function') {
    return new CustomCollector(config.customFunction)
  }

  // MINIMAL asks for a small payload, so it gets its own lean collector
  // instead of the full legacy walk.
  if (config.dataReturnMode === 'MINIMAL') {
    return new MinimalCollector()
  }

  // Otherwise, use LegacyCollector for backward compatibility
  return new LegacyCollector()
}

/**
 * Validate collector configuration
 */
export function validateCollectorConfig(config: CollectorConfig): { valid: boolean; error?: string } {
  if (config.customFunction !== undefined && config.customFunction !== null) {
    if (typeof config.customFunction !== 'function') {
      return {
        valid: false,
        error: 'customFunction must be a valid function'
      }
    }
  }

  if (config.shouldGridReturn !== undefined && config.shouldGridReturn !== null) {
    if (typeof config.shouldGridReturn !== 'function') {
      return {
        valid: false,
        error: 'shouldGridReturn must be a valid function'
      }
    }
  }

  return { valid: true }
}

/**
 * Get collector information for debugging
 */
export function getCollectorInfo(collector: BaseCollector): {
  type: string
  details: any
} {
  const info = {
    type: collector.getCollectorType(),
    details: {}
  }

  if (collector instanceof CustomCollector) {
    info.details = collector.getFunctionInfo()
  } else if (collector instanceof MinimalCollector) {
    info.details = { description: 'Returns displayed and selected rows only' }
  } else if (collector instanceof LegacyCollector) {
    info.details = { description: 'Uses original getGridReturnValue logic' }
  }

  return info
}