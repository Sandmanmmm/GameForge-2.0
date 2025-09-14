import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Settings, 
  Shield, 
  History, 
  Download, 
  ExternalLink, 
  Check, 
  X, 
  Clock,
  AlertTriangle,
  Info
} from "lucide-react";
import { format } from 'date-fns';

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
  source_ip?: string;
}

export interface ConsentSummary {
  user_id: string;
  consents: ConsentRecord[];
  total_consents: number;
  granted_count: number;
  denied_count: number;
  last_updated?: string;
}

interface ConsentDashboardProps {
  /**
   * Current user's consent summary
   */
  consentSummary?: ConsentSummary;
  
  /**
   * Called when user updates a consent preference
   */
  onUpdateConsent: (consentType: string, value: boolean) => Promise<void>;
  
  /**
   * Called when user requests to download their consent data
   */
  onDownloadData?: () => Promise<void>;
  
  /**
   * Loading states
   */
  isLoading?: boolean;
  isUpdating?: boolean;
  
  /**
   * Error message
   */
  error?: string;
  
  className?: string;
}

const CONSENT_TYPE_LABELS: Record<string, { title: string; description: string; category: string }> = {
  model_training: {
    title: "AI Model Training",
    description: "Use your assets and interactions to improve AI models",
    category: "AI & Machine Learning"
  },
  analytics: {
    title: "Platform Analytics", 
    description: "Usage statistics to optimize platform performance",
    category: "Platform Improvement"
  },
  feature_improvement: {
    title: "Feature Development",
    description: "Feedback and usage patterns for new features",
    category: "Platform Improvement"
  },
  security_monitoring: {
    title: "Security & Fraud Prevention",
    description: "Monitor for security threats and fraudulent activity",
    category: "Security & Safety"
  },
  marketing: {
    title: "Marketing Communications",
    description: "Product updates, tips, and GameForge news",
    category: "Communications"
  },
  asset_sharing: {
    title: "Asset Sharing",
    description: "Allow generated assets to be used as training data",
    category: "AI & Machine Learning"
  },
  performance_optimization: {
    title: "Performance Optimization",
    description: "Data usage to optimize platform performance",
    category: "Platform Improvement"
  },
  research: {
    title: "Research & Development",
    description: "Data usage for research and new technology development",
    category: "AI & Machine Learning"
  }
};

export const ConsentDashboard: React.FC<ConsentDashboardProps> = ({
  consentSummary,
  onUpdateConsent,
  onDownloadData,
  isLoading = false,
  isUpdating = false,
  error,
  className = ""
}) => {
  const [localConsents, setLocalConsents] = useState<Record<string, boolean>>({});
  const [updatingConsent, setUpdatingConsent] = useState<string | null>(null);

  useEffect(() => {
    if (consentSummary?.consents) {
      const consentMap: Record<string, boolean> = {};
      consentSummary.consents.forEach(consent => {
        if (consent.is_current) {
          consentMap[consent.consent_type] = consent.consent_value;
        }
      });
      setLocalConsents(consentMap);
    }
  }, [consentSummary]);

  const handleConsentToggle = async (consentType: string, newValue: boolean) => {
    // Don't allow toggling security monitoring
    if (consentType === 'security_monitoring') {
      return;
    }

    setUpdatingConsent(consentType);
    try {
      await onUpdateConsent(consentType, newValue);
      setLocalConsents(prev => ({
        ...prev,
        [consentType]: newValue
      }));
    } catch (error) {
      console.error('Failed to update consent:', error);
    } finally {
      setUpdatingConsent(null);
    }
  };

  const groupConsentsByCategory = () => {
    const categories: Record<string, ConsentRecord[]> = {};
    
    consentSummary?.consents
      ?.filter(consent => consent.is_current)
      ?.forEach(consent => {
        const category = CONSENT_TYPE_LABELS[consent.consent_type]?.category || 'Other';
        if (!categories[category]) {
          categories[category] = [];
        }
        categories[category].push(consent);
      });
    
    return categories;
  };

  const getConsentHistory = () => {
    return consentSummary?.consents
      ?.filter(consent => !consent.is_current)
      ?.sort((a, b) => new Date(b.granted_at).getTime() - new Date(a.granted_at).getTime()) || [];
  };

  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const categorizedConsents = groupConsentsByCategory();
  const consentHistory = getConsentHistory();

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <CardTitle>Privacy & Consent Management</CardTitle>
            </div>
            {onDownloadData && (
              <Button
                variant="outline"
                size="sm"
                onClick={onDownloadData}
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Download My Data
              </Button>
            )}
          </div>
          <CardDescription>
            Manage how your data is used by GameForge. You have full control over your privacy preferences.
          </CardDescription>
        </CardHeader>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {consentSummary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Consent Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{consentSummary.granted_count}</div>
                <p className="text-sm text-muted-foreground">Granted</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{consentSummary.denied_count}</div>
                <p className="text-sm text-muted-foreground">Denied</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{consentSummary.total_consents}</div>
                <p className="text-sm text-muted-foreground">Total</p>
              </div>
              <div className="text-center">
                <div className="text-sm font-medium">
                  {consentSummary.last_updated 
                    ? format(new Date(consentSummary.last_updated), 'MMM d, yyyy')
                    : 'Never'
                  }
                </div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="preferences" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Preferences
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="preferences" className="space-y-6">
          {Object.entries(categorizedConsents).map(([category, consents]) => (
            <Card key={category}>
              <CardHeader>
                <CardTitle className="text-lg">{category}</CardTitle>
                <CardDescription>
                  Control how your data is used for {category.toLowerCase()}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {consents.map((consent) => {
                  const consentInfo = CONSENT_TYPE_LABELS[consent.consent_type];
                  const isRequired = consent.consent_type === 'security_monitoring';
                  const isUpdatingThis = updatingConsent === consent.consent_type;
                  
                  return (
                    <div key={consent.consent_type} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Label className="font-medium">
                            {consentInfo?.title || consent.consent_type}
                          </Label>
                          {isRequired && (
                            <Badge variant="secondary" className="text-xs">Required</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {consentInfo?.description || consent.purpose_description}
                        </p>
                        <div className="flex items-center gap-4 mt-2">
                          <span className="text-xs text-muted-foreground">
                            Last updated: {format(new Date(consent.granted_at), 'MMM d, yyyy')}
                          </span>
                          <Badge variant={consent.consent_value ? "default" : "secondary"} className="text-xs">
                            {consent.consent_value ? (
                              <><Check className="h-3 w-3 mr-1" /> Granted</>
                            ) : (
                              <><X className="h-3 w-3 mr-1" /> Denied</>
                            )}
                          </Badge>
                        </div>
                      </div>
                      <div className="ml-4">
                        <Switch
                          checked={localConsents[consent.consent_type] || false}
                          onCheckedChange={(checked) => 
                            handleConsentToggle(consent.consent_type, checked)
                          }
                          disabled={isRequired || isUpdatingThis || isUpdating}
                        />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="history" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Consent History</CardTitle>
              <CardDescription>
                Complete audit trail of all your consent decisions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {consentHistory.length === 0 ? (
                <div className="text-center py-8">
                  <Clock className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-muted-foreground">No consent history available</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {consentHistory.map((consent, index) => {
                    const consentInfo = CONSENT_TYPE_LABELS[consent.consent_type];
                    
                    return (
                      <div key={`${consent.id}-${index}`} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium">
                              {consentInfo?.title || consent.consent_type}
                            </span>
                            <Badge variant={consent.consent_value ? "default" : "secondary"} className="text-xs">
                              {consent.consent_value ? "Granted" : "Denied"}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>{format(new Date(consent.granted_at), 'MMM d, yyyy HH:mm')}</span>
                            <span>Method: {consent.consent_method}</span>
                            {consent.notes && <span>Notes: {consent.notes}</span>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-medium text-blue-900 mb-1">Your Privacy Rights</h4>
              <p className="text-sm text-blue-700 mb-3">
                You have the right to access, correct, or delete your personal data at any time. 
                You can also withdraw consent for any non-required purposes.
              </p>
              <div className="flex flex-wrap gap-2">
                <a
                  href="/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  Privacy Policy <ExternalLink className="h-3 w-3" />
                </a>
                <a
                  href="/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  Terms of Service <ExternalLink className="h-3 w-3" />
                </a>
                <a
                  href="/support"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  Contact Support <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ConsentDashboard;