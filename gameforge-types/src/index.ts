/**
 * Shared API Types and Contracts for GameForge
 * 
 * This package contains all shared TypeScript types, interfaces, and API contracts
 * used by both the frontend and backend to ensure type safety and consistency.
 */

// Re-export all types
export * from './api/auth';
export * from './api/projects';
export * from './api/assets';
export * from './api/models';
export * from './api/permissions';
export * from './api/common';

// Version information
export const API_VERSION = 'v1';
export const TYPES_VERSION = '1.0.0';