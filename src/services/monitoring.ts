/**
 * Production-Ready Monitoring and Error Tracking Setup
 * 
 * Integrates Sentry for error tracking and analytics for user behavior
 */

import React from 'react';
import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

interface MonitoringConfig {
  sentryDsn?: string;
  environment: string;
  version: string;
  enableAnalytics: boolean;
  enableErrorTracking: boolean;
  debugMode: boolean;
}

class MonitoringService {
  private config: MonitoringConfig;
  private initialized = false;

  constructor() {
    this.config = {
      sentryDsn: (import.meta as any).env?.VITE_SENTRY_DSN,
      environment: (import.meta as any).env?.VITE_NODE_ENV || 'development',
      version: (import.meta as any).env?.VITE_APP_VERSION || '1.0.0',
      enableAnalytics: (import.meta as any).env?.VITE_ENABLE_ANALYTICS === 'true',
      enableErrorTracking: (import.meta as any).env?.VITE_ENABLE_ERROR_TRACKING === 'true',
      debugMode: (import.meta as any).env?.VITE_ENABLE_DEBUG_MODE === 'true'
    };
  }

  /**
   * Initialize monitoring services
   */
  initialize(): void {
    if (this.initialized) return;

    // Initialize Sentry for error tracking
    if (this.config.enableErrorTracking && this.config.sentryDsn) {
      Sentry.init({
        dsn: this.config.sentryDsn,
        environment: this.config.environment,
        release: this.config.version,
        integrations: [
          new BrowserTracing({
            // Performance monitoring
            tracePropagationTargets: ["localhost", /^https:\/\/api\.gameforge\.app/],
          }),
          new Sentry.Replay({
            // Session replay for debugging
            maskAllText: true,
            blockAllMedia: true,
          }),
        ],
        tracesSampleRate: this.config.environment === 'production' ? 0.1 : 1.0,
        replaysSessionSampleRate: this.config.environment === 'production' ? 0.01 : 0.1,
        replaysOnErrorSampleRate: 1.0,
        beforeSend: (event: any) => {
          // Filter out development errors in production
          if (this.config.environment === 'production' && event.exception) {
            const error = event.exception.values?.[0];
            if (error?.value?.includes('ChunkLoadError') || 
                error?.value?.includes('Loading chunk')) {
              return null; // Don't send chunk loading errors
            }
          }
          return event;
        },
      });
    }

    // Initialize analytics (PostHog example)
    if (this.config.enableAnalytics) {
      this.initializeAnalytics();
    }

    this.initialized = true;
    this.logInfo('Monitoring services initialized', { config: this.config });
  }

  /**
   * Set user context for error tracking
   */
  setUser(user: { id: string; email: string; name: string; roles: string[] }): void {
    if (this.config.enableErrorTracking) {
      Sentry.setUser({
        id: user.id,
        email: user.email,
        username: user.name,
        roles: user.roles.join(',')
      });
    }

    if (this.config.enableAnalytics && (window as any).posthog) {
      (window as any).posthog.identify(user.id, {
        email: user.email,
        name: user.name,
        roles: user.roles
      });
    }
  }

  /**
   * Clear user context on logout
   */
  clearUser(): void {
    if (this.config.enableErrorTracking) {
      Sentry.setUser(null);
    }

    if (this.config.enableAnalytics && (window as any).posthog) {
      (window as any).posthog.reset();
    }
  }

  /**
   * Track custom events
   */
  trackEvent(eventName: string, properties?: Record<string, any>): void {
    if (this.config.enableAnalytics && (window as any).posthog) {
      (window as any).posthog.capture(eventName, properties);
    }

    if (this.config.debugMode) {
      console.log('📊 Event tracked:', eventName, properties);
    }
  }

  /**
   * Track page views
   */
  trackPageView(path: string, title?: string): void {
    if (this.config.enableAnalytics && (window as any).posthog) {
      (window as any).posthog.capture('$pageview', {
        $current_url: window.location.href,
        path,
        title
      });
    }

    if (this.config.debugMode) {
      console.log('📄 Page view tracked:', path, title);
    }
  }

  /**
   * Log errors manually
   */
  logError(error: Error, context?: Record<string, any>): void {
    if (this.config.enableErrorTracking) {
      Sentry.withScope((scope: any) => {
        if (context) {
          Object.keys(context).forEach(key => {
            scope.setContext(key, context[key]);
          });
        }
        Sentry.captureException(error);
      });
    }

    if (this.config.debugMode) {
      console.error('🔥 Error logged:', error, context);
    }
  }

  /**
   * Log info messages
   */
  logInfo(message: string, data?: Record<string, any>): void {
    if (this.config.enableErrorTracking) {
      Sentry.addBreadcrumb({
        message,
        data,
        level: 'info',
        timestamp: Date.now() / 1000,
      });
    }

    if (this.config.debugMode) {
      console.log('ℹ️ Info logged:', message, data);
    }
  }

  /**
   * Start performance transaction
   */
  startTransaction(name: string, operation?: string): any {
    if (this.config.enableErrorTracking) {
      return Sentry.startTransaction({ name, op: operation });
    }
    return null;
  }

  /**
   * Initialize analytics service (PostHog example)
   */
  private initializeAnalytics(): void {
    const posthogKey = (import.meta as any).env?.VITE_POSTHOG_KEY;
    
    if (!posthogKey) {
      console.warn('PostHog key not configured');
      return;
    }

    // Load PostHog script
    const script = document.createElement('script');
    script.innerHTML = `
      !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]);var n=t;if("undefined"!=typeof e)n=t[e]=function(){n.push([e].concat(Array.prototype.slice.call(arguments,0)))};n.push([e])}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
      posthog.init('${posthogKey}', {
        api_host: 'https://app.posthog.com',
        autocapture: false, // Disable automatic event capture for privacy
        capture_pageview: false, // We'll handle page views manually
        disable_session_recording: ${this.config.environment === 'production'}, // Disable in production for privacy
        loaded: function(posthog) {
          if ('${this.config.environment}' === 'development') {
            posthog.debug();
          }
        }
      });
    `;
    document.head.appendChild(script);
  }
}

// Export singleton instance
export const monitoring = new MonitoringService();

// React Error Boundary HOC
export const withErrorBoundary = (Component: React.ComponentType): React.ComponentType => {
  return Sentry.withErrorBoundary(Component, {
    fallback: ({ error, resetError }: any) => 
      React.createElement('div', { className: 'error-boundary' },
        React.createElement('h2', null, 'Something went wrong'),
        React.createElement('p', null, error.message),
        React.createElement('button', { onClick: resetError }, 'Try again')
      ),
    beforeCapture: (scope: any, error: any, errorInfo: any) => {
      scope.setTag('errorBoundary', true);
      scope.setContext('errorInfo', errorInfo);
    },
  });
};