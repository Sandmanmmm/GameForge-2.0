import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";
import { Alert, AlertDescription } from "./ui/alert";
import { ChevronDown, ChevronUp, Info, Shield, ExternalLink, AlertTriangle } from "lucide-react";
import { Separator } from "./ui/separator";

export interface ConsentDecision {
  consent_type: string;
  consent_value: boolean;
  purpose_description: string;
  version: string;
  notes?: string;
}

export interface ConsentOption {
  type: string;
  title: string;
  description: string;
  purpose_description: string;
  required: boolean;
  default_value: boolean;
  policy_link?: string;
  more_info?: string;
}

interface ConsentFormProps {
  /**
   * List of consent options to display
   */
  consentOptions: ConsentOption[];
  
  /**
   * Whether this is initial consent collection (e.g., during signup)
   */
  isInitialConsent?: boolean;
  
  /**
   * Current consent values (for updating existing consents)
   */
  currentConsents?: Record<string, boolean>;
  
  /**
   * Called when user submits consent decisions
   */
  onSubmit: (decisions: ConsentDecision[]) => Promise<void>;
  
  /**
   * Loading state
   */
  isLoading?: boolean;
  
  /**
   * Error message to display
   */
  error?: string;
  
  /**
   * Additional class name for styling
   */
  className?: string;
}

const DEFAULT_CONSENT_OPTIONS: ConsentOption[] = [
  {
    type: 'model_training',
    title: 'AI Model Training',
    description: 'Allow GameForge to use your assets and interactions to improve AI models',
    purpose_description: 'Your generated assets and usage patterns will be used to train and improve our AI models, resulting in better quality outputs for all users.',
    required: false,
    default_value: false,
    policy_link: '/privacy#model-training',
    more_info: 'This includes generated images, prompts, and model preferences. All data is anonymized and used only for model improvement.'
  },
  {
    type: 'analytics',
    title: 'Platform Analytics',
    description: 'Help us improve GameForge through usage analytics and insights',
    purpose_description: 'Anonymous usage statistics and feature interactions will be collected to optimize platform performance and user experience.',
    required: false,
    default_value: true,
    policy_link: '/privacy#analytics',
    more_info: 'Includes page views, feature usage, performance metrics, and error reporting. No personal data is included.'
  },
  {
    type: 'feature_improvement',
    title: 'Feature Development',
    description: 'Use your feedback and usage patterns to develop new features',
    purpose_description: 'Your usage patterns and feedback will inform the development of new platform features and improvements.',
    required: false,
    default_value: true,
    policy_link: '/privacy#features'
  },
  {
    type: 'security_monitoring',
    title: 'Security & Fraud Prevention',
    description: 'Monitor for security threats and prevent fraudulent activity',
    purpose_description: 'Your account activity will be monitored to detect and prevent security threats, fraud, and abuse of the platform.',
    required: true,
    default_value: true,
    policy_link: '/privacy#security',
    more_info: 'This is required for platform security and cannot be opted out.'
  },
  {
    type: 'marketing',
    title: 'Marketing Communications',
    description: 'Receive updates about new features, tips, and GameForge news',
    purpose_description: 'We will send you product updates, feature announcements, tips for better asset generation, and community highlights.',
    required: false,
    default_value: false,
    policy_link: '/privacy#marketing',
    more_info: 'You can unsubscribe at any time. We will never share your email with third parties.'
  }
];

export const ConsentForm: React.FC<ConsentFormProps> = ({
  consentOptions = DEFAULT_CONSENT_OPTIONS,
  isInitialConsent = false,
  currentConsents = {},
  onSubmit,
  isLoading = false,
  error,
  className = ""
}) => {
  const [consents, setConsents] = useState<Record<string, boolean>>(() => {
    // Initialize with current consents or default values
    const initial: Record<string, boolean> = {};
    consentOptions.forEach(option => {
      initial[option.type] = currentConsents[option.type] ?? option.default_value;
    });
    return initial;
  });

  const [expandedInfo, setExpandedInfo] = useState<Record<string, boolean>>({});

  useEffect(() => {
    // Update consents when currentConsents prop changes
    const updated: Record<string, boolean> = {};
    consentOptions.forEach(option => {
      updated[option.type] = currentConsents[option.type] ?? option.default_value;
    });
    setConsents(updated);
  }, [currentConsents, consentOptions]);

  const handleConsentChange = (consentType: string, value: boolean) => {
    setConsents(prev => ({
      ...prev,
      [consentType]: value
    }));
  };

  const toggleInfo = (consentType: string) => {
    setExpandedInfo(prev => ({
      ...prev,
      [consentType]: !prev[consentType]
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const decisions: ConsentDecision[] = consentOptions.map(option => ({
      consent_type: option.type,
      consent_value: consents[option.type],
      purpose_description: option.purpose_description,
      version: "1.0",
      notes: isInitialConsent ? "Initial consent during signup" : "Updated consent preference"
    }));

    await onSubmit(decisions);
  };

  const requiredConsentsGiven = consentOptions
    .filter(option => option.required)
    .every(option => consents[option.type]);

  return (
    <div className={`space-y-6 ${className}`}>
      {isInitialConsent && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-600" />
              <CardTitle className="text-lg text-blue-900">Data Privacy & Consent</CardTitle>
            </div>
            <CardDescription className="text-blue-700">
              GameForge is committed to protecting your privacy. Please review and decide how you'd like your data to be used.
              You can change these preferences at any time in your account settings.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {consentOptions.map((option) => (
          <Card key={option.type} className={option.required ? "border-amber-200" : ""}>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <Checkbox
                    id={option.type}
                    checked={consents[option.type]}
                    onCheckedChange={(checked) => 
                      handleConsentChange(option.type, checked as boolean)
                    }
                    disabled={option.required || isLoading}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Label 
                        htmlFor={option.type} 
                        className="text-sm font-medium cursor-pointer"
                      >
                        {option.title}
                      </Label>
                      {option.required && (
                        <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full">
                          Required
                        </span>
                      )}
                      {option.more_info && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleInfo(option.type)}
                          className="h-6 w-6 p-0"
                        >
                          <Info className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {option.description}
                    </p>
                    
                    {expandedInfo[option.type] && option.more_info && (
                      <div className="mt-2 p-3 bg-gray-50 rounded-md">
                        <p className="text-xs text-gray-600">{option.more_info}</p>
                      </div>
                    )}

                    {option.policy_link && (
                      <div className="mt-2">
                        <a
                          href={option.policy_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          Read our privacy policy
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        <Separator className="my-6" />

        <div className="flex flex-col sm:flex-row gap-3 justify-between items-center">
          <p className="text-sm text-muted-foreground">
            {isInitialConsent 
              ? "You can update these preferences at any time in your account settings."
              : "Changes will take effect immediately."
            }
          </p>
          
          <Button
            type="submit"
            disabled={!requiredConsentsGiven || isLoading}
            className="w-full sm:w-auto"
          >
            {isLoading ? "Saving..." : isInitialConsent ? "Create Account" : "Update Preferences"}
          </Button>
        </div>
      </form>

      {!requiredConsentsGiven && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Some consent decisions are required to use GameForge. Please review the required items above.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default ConsentForm;