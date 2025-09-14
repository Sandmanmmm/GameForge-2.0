/**
 * Consent Management API Service
 * 
 * Handles all API interactions for user consent management including
 * granting consents, retrieving consent status, and managing consent history.
 */

import { gameforgeAPI } from './api';

export interface ConsentDecision {
  consent_type: string;
  consent_value: boolean;
  purpose_description: string;
  version: string;
  notes?: string;
}

export interface ConsentRecord {
  id: string;
  user_id: string;
  consent_type: string;
  consent_value: boolean;
  purpose_description: string;
  granted_at: string;
  version: string;
  is_current: boolean;
  consent_method: string;
  notes?: string;
}

export interface ConsentSummary {
  user_id: string;
  consents: ConsentRecord[];
  total_consents: number;
  granted_count: number;
  denied_count: number;
  last_updated?: string;
}

export interface BulkConsentRequest {
  consents: ConsentDecision[];
}

export class ConsentAPI {
  /**
   * Grant or deny a single consent
   */
  static async grantConsent(decision: ConsentDecision): Promise<ConsentRecord> {
    const response = await gameforgeAPI.post<ConsentRecord>('/users/consent', decision);
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to record consent');
    }
    
    return response.data!;
  }

  /**
   * Grant or deny multiple consents in bulk (typically during signup)
   */
  static async grantBulkConsent(bulkRequest: BulkConsentRequest): Promise<ConsentSummary> {
    const response = await gameforgeAPI.post<ConsentSummary>('/users/consent/bulk', bulkRequest);
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to record bulk consents');
    }
    
    return response.data!;
  }

  /**
   * Get all current consent decisions for the authenticated user
   */
  static async getUserConsents(): Promise<ConsentSummary> {
    const response = await gameforgeAPI.get<ConsentSummary>('/users/consent');
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to retrieve consent information');
    }
    
    return response.data!;
  }

  /**
   * Get consent decision for a specific consent type
   */
  static async getConsentByType(consentType: string): Promise<ConsentRecord> {
    const response = await gameforgeAPI.get<ConsentRecord>(`/users/consent/${consentType}`);
    
    if (!response.success) {
      throw new Error(response.error?.message || `Failed to retrieve consent for ${consentType}`);
    }
    
    return response.data!;
  }

  /**
   * Get the full history of consent decisions for a specific type
   */
  static async getConsentHistory(consentType: string): Promise<ConsentRecord[]> {
    const response = await gameforgeAPI.get<ConsentRecord[]>(`/users/consent/${consentType}/history`);
    
    if (!response.success) {
      throw new Error(response.error?.message || `Failed to retrieve consent history for ${consentType}`);
    }
    
    return response.data!;
  }

  /**
   * Revoke consent for a specific type (sets consent_value to false)
   */
  static async revokeConsent(consentType: string): Promise<{ message: string }> {
    const response = await gameforgeAPI.delete<{ message: string }>(`/users/consent/${consentType}`);
    
    if (!response.success) {
      throw new Error(response.error?.message || `Failed to revoke consent for ${consentType}`);
    }
    
    return response.data!;
  }

  /**
   * Get all available consent types and their descriptions
   */
  static async getConsentTypes(): Promise<Record<string, string>> {
    const response = await gameforgeAPI.get<Record<string, string>>('/users/consent-types');
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to retrieve consent types');
    }
    
    return response.data!;
  }

  /**
   * Update a single consent preference
   */
  static async updateConsent(consentType: string, value: boolean, notes?: string): Promise<ConsentRecord> {
    const decision: ConsentDecision = {
      consent_type: consentType,
      consent_value: value,
      purpose_description: await this.getConsentDescription(consentType),
      version: "1.0",
      notes: notes || "Updated consent preference"
    };

    return this.grantConsent(decision);
  }

  /**
   * Helper method to get the purpose description for a consent type
   */
  private static async getConsentDescription(consentType: string): Promise<string> {
    const descriptions: Record<string, string> = {
      model_training: "Your data will be used to train and improve AI models for better quality outputs.",
      analytics: "Anonymous usage statistics will be collected to optimize platform performance and user experience.",
      marketing: "You will receive product updates, feature announcements, and tips for better asset generation.",
      feature_improvement: "Your usage patterns and feedback will inform the development of new platform features.",
      research: "Your data will be used for research and development of new technologies.",
      asset_sharing: "Your generated assets may be used as training data to improve models for all users.",
      performance_optimization: "Your data will be used to optimize platform performance and user experience.",
      security_monitoring: "Your account activity will be monitored to detect and prevent security threats and fraud."
    };

    return descriptions[consentType] || "Data will be used according to our privacy policy.";
  }

  /**
   * Check if user has granted consent for a specific purpose
   */
  static async hasConsent(consentType: string): Promise<boolean> {
    try {
      const consent = await this.getConsentByType(consentType);
      return consent.consent_value;
    } catch (error) {
      // If consent not found, assume not granted
      return false;
    }
  }

  /**
   * Check if user has granted consent for multiple purposes
   */
  static async hasConsents(consentTypes: string[]): Promise<Record<string, boolean>> {
    try {
      const summary = await this.getUserConsents();
      const result: Record<string, boolean> = {};
      
      consentTypes.forEach(type => {
        const consent = summary.consents.find(c => c.consent_type === type && c.is_current);
        result[type] = consent?.consent_value || false;
      });
      
      return result;
    } catch (error) {
      // If error, assume no consents granted
      const result: Record<string, boolean> = {};
      consentTypes.forEach(type => {
        result[type] = false;
      });
      return result;
    }
  }

  /**
   * Export user's consent data (for GDPR data portability)
   */
  static async exportConsentData(): Promise<Blob> {
    try {
      const summary = await this.getUserConsents();
      
      const exportData = {
        user_id: summary.user_id,
        export_date: new Date().toISOString(),
        total_consents: summary.total_consents,
        granted_count: summary.granted_count,
        denied_count: summary.denied_count,
        last_updated: summary.last_updated,
        consent_records: summary.consents.map(consent => ({
          id: consent.id,
          consent_type: consent.consent_type,
          consent_value: consent.consent_value,
          purpose_description: consent.purpose_description,
          granted_at: consent.granted_at,
          version: consent.version,
          is_current: consent.is_current,
          consent_method: consent.consent_method,
          notes: consent.notes
        }))
      };
      
      const jsonString = JSON.stringify(exportData, null, 2);
      return new Blob([jsonString], { type: 'application/json' });
    } catch (error) {
      throw new Error('Failed to export consent data');
    }
  }

  /**
   * Validate consent decisions before submission
   */
  static validateConsentDecisions(decisions: ConsentDecision[]): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (!decisions || decisions.length === 0) {
      errors.push("At least one consent decision is required");
    }
    
    const consentTypes = decisions.map(d => d.consent_type);
    const uniqueTypes = new Set(consentTypes);
    
    if (consentTypes.length !== uniqueTypes.size) {
      errors.push("Duplicate consent types are not allowed");
    }
    
    decisions.forEach((decision, index) => {
      if (!decision.consent_type) {
        errors.push(`Consent type is required for decision ${index + 1}`);
      }
      
      if (typeof decision.consent_value !== 'boolean') {
        errors.push(`Consent value must be true or false for ${decision.consent_type}`);
      }
      
      if (!decision.purpose_description || decision.purpose_description.trim().length < 10) {
        errors.push(`Purpose description must be at least 10 characters for ${decision.consent_type}`);
      }
      
      if (!decision.version) {
        errors.push(`Version is required for ${decision.consent_type}`);
      }
    });
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
}

export default ConsentAPI;