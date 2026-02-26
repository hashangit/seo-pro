/**
 * Authentication utilities and exports
 * Re-exports from the main auth module
 */

export * from "../auth";
export type { AuthState, WorkOSUser } from "../auth";
export { useAuth, requireAuth, AuthKitProvider } from "../auth";
