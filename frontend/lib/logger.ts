/**
 * Centralized Logger Utility
 *
 * Provides consistent logging across the frontend with:
 * - Environment-aware logging (dev vs production)
 * - Structured context for easier debugging
 * - Future-ready for error monitoring integration (Sentry, etc.)
 * - Works on both client and server side
 */

const isDev = process.env.NODE_ENV !== "production";
const isClient = typeof window !== "undefined";

/**
 * Format a log message with context
 */
function formatMessage(context: string, message: string): string {
  return `[${context}] ${message}`;
}

/**
 * Centralized logger for the frontend
 *
 * Usage:
 *   import { logger } from '@/lib/logger';
 *   logger.error('Auth', error);
 *   logger.warn('Config', 'Missing environment variable');
 */
export const logger = {
  /**
   * Log an error with context
   * In development: logs to console (client and server)
   * In production: could send to error monitoring service
   */
  error: (context: string, error: unknown) => {
    // Always log errors in development (client and server)
    if (isDev) {
      console.error(formatMessage(context, "Error"), error);
    }
    // Future: Send to error monitoring service (Sentry, LogRocket, etc.)
    // if (!isDev) {
    //   sendToErrorMonitoring(context, error);
    // }
  },

  /**
   * Log a warning with context
   * Logs in development mode (client and server)
   */
  warn: (context: string, message: string) => {
    if (isDev) {
      console.warn(formatMessage(context, message));
    }
  },

  /**
   * Log an info message with context
   * Only logs in development mode on client
   */
  info: (context: string, message: string) => {
    if (isDev && isClient) {
      console.log(formatMessage(context, message));
    }
  },

  /**
   * Log a debug message with context
   * Only logs in development mode on client
   */
  debug: (context: string, message: string, data?: unknown) => {
    if (isDev && isClient) {
      if (data !== undefined) {
        console.debug(formatMessage(context, message), data);
      } else {
        console.debug(formatMessage(context, message));
      }
    }
  },
};

/**
 * Context constants for common logging scenarios
 */
export const LogContext = {
  AUTH: "Auth",
  API: "API",
  USER: "User",
  CONFIG: "Config",
  AUDIT: "Audit",
  CREDITS: "Credits",
  ANALYSIS: "Analysis",
  ERROR_BOUNDARY: "ErrorBoundary",
} as const;

export type LogContextType = (typeof LogContext)[keyof typeof LogContext];
