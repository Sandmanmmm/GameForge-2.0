import React, { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Progress } from "./ui/progress";
import { Alert, AlertDescription } from "./ui/alert";
import { ConsentForm, ConsentDecision } from "./ConsentForm";
import { ConsentAPI } from "../services/consentAPI";
import { Eye, EyeOff, Mail, Lock, User, ArrowRight, ArrowLeft, Check, AlertTriangle } from "lucide-react";

// Default consent options for signup flow
const SIGNUP_CONSENT_OPTIONS = [
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
  },
  {
    type: 'asset_storage',
    title: 'Asset Storage & Processing',
    description: 'Store and process your generated assets on our platform',
    purpose_description: 'Your generated assets will be stored securely and processed to provide platform features like history, sharing, and organization.',
    required: true,
    default_value: true,
    policy_link: '/privacy#storage',
    more_info: 'This is required to use the platform and cannot be opted out.'
  },
  {
    type: 'sharing_outputs',
    title: 'Asset Sharing',
    description: 'Allow sharing of your assets with the GameForge community',
    purpose_description: 'Your assets may be featured in community showcases, used as examples, or shared with other users when you explicitly choose to share them.',
    required: false,
    default_value: false,
    policy_link: '/privacy#sharing',
    more_info: 'Only applies when you actively choose to share assets. Your private assets remain private.'
  },
  {
    type: 'community_features',
    title: 'Community Features',
    description: 'Participate in community features like contests and showcases',
    purpose_description: 'Your participation in community events, contests, and showcases will be tracked to provide personalized recommendations and features.',
    required: false,
    default_value: true,
    policy_link: '/privacy#community'
  }
];

interface RegistrationData {
  name: string;
  email: string;
  password: string;
  consents: ConsentDecision[];
}

export default function SignupPage() {
  const navigate = useNavigate();
  const { register } = useContext(AuthContext);
  
  // Multi-step state
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 3;
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: ""
  });
  const [consents, setConsents] = useState<ConsentDecision[]>([]);
  
  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateStep1 = (): boolean => {
    const errors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      errors.name = "Name is required";
    } else if (formData.name.trim().length < 2) {
      errors.name = "Name must be at least 2 characters";
    }
    
    if (!formData.email.trim()) {
      errors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = "Please enter a valid email address";
    }
    
    if (!formData.password) {
      errors.password = "Password is required";
    } else if (formData.password.length < 8) {
      errors.password = "Password must be at least 8 characters";
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      errors.password = "Password must contain at least one uppercase letter, one lowercase letter, and one number";
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateStep2 = (): boolean => {
    // Check that required consents are given
    const requiredConsents = consents.filter(c => 
      c.consent_type === 'security_monitoring'
    );
    
    if (requiredConsents.length === 0 || !requiredConsents.every(c => c.consent_value)) {
      setError("Security monitoring consent is required to create an account");
      return false;
    }
    
    setError("");
    return true;
  };

  const handleNext = () => {
    setError("");
    
    if (currentStep === 1 && !validateStep1()) {
      return;
    }
    
    if (currentStep === 2 && !validateStep2()) {
      return;
    }
    
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleConsentSubmit = async (decisions: ConsentDecision[]) => {
    setConsents(decisions);
    
    // Validate consents
    const validation = ConsentAPI.validateConsentDecisions(decisions);
    if (!validation.valid) {
      setError(validation.errors[0]);
      return;
    }
    
    // Move to next step
    setError("");
    setCurrentStep(3);
  };

  const handleFinalSubmit = async () => {
    setIsLoading(true);
    setError("");
    
    try {
      // First, create the user account
      await register(formData.email, formData.password, formData.name);
      
      // Then, record their consent decisions
      if (consents.length > 0) {
        await ConsentAPI.grantBulkConsent({ consents });
      }
      
      // Success! Navigate to dashboard
      navigate("/dashboard");
      
    } catch (err: any) {
      setError(err.message || "Failed to create account");
    } finally {
      setIsLoading(false);
    }
  };

  const getProgressPercentage = () => {
    return (currentStep / totalSteps) * 100;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-900 via-purple-900 to-blue-900 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="stars"></div>
        <div className="twinkling"></div>
      </div>
      
      {/* Branding */}
      <div className="absolute top-8 left-1/2 transform -translate-x-1/2 z-10">
        <div className="flex items-center space-x-3 animate-fadeIn">
          <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center shadow-lg">
            <span className="text-2xl font-bold text-white">🔥</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-wide">
            Game<span className="text-orange-400">Forge</span>
          </h1>
        </div>
      </div>

      {/* Main content */}
      <div className="min-h-screen flex items-center justify-center px-4 pt-24 pb-8">
        <Card className="w-full max-w-2xl bg-white/10 backdrop-blur-xl border-white/20 shadow-2xl">
          <CardHeader className="text-center pb-6">
            <CardTitle className="text-2xl font-bold text-white mb-2">
              Join GameForge
            </CardTitle>
            <CardDescription className="text-white/70 mb-4">
              Create your account and start building amazing games
            </CardDescription>
            
            {/* Progress indicator */}
            <div className="space-y-3">
              <Progress value={getProgressPercentage()} className="w-full h-2" />
              <div className="flex justify-between text-sm text-white/60">
                <span className={currentStep >= 1 ? "text-white" : ""}>Account Details</span>
                <span className={currentStep >= 2 ? "text-white" : ""}>Privacy & Consent</span>
                <span className={currentStep >= 3 ? "text-white" : ""}>Review & Create</span>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-6">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Step 1: Account Details */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40 h-5 w-5" />
                      <Input
                        type="text"
                        placeholder="Enter your full name"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="pl-12 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-orange-400/50 focus:ring-orange-400/20 h-12"
                        disabled={isLoading}
                      />
                    </div>
                    {validationErrors.name && (
                      <p className="text-red-400 text-sm">{validationErrors.name}</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40 h-5 w-5" />
                      <Input
                        type="email"
                        placeholder="Enter your email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="pl-12 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-orange-400/50 focus:ring-orange-400/20 h-12"
                        disabled={isLoading}
                      />
                    </div>
                    {validationErrors.email && (
                      <p className="text-red-400 text-sm">{validationErrors.email}</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40 h-5 w-5" />
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="Create a strong password"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        className="pl-12 pr-12 bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-orange-400/50 focus:ring-orange-400/20 h-12"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                        tabIndex={-1}
                      >
                        {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                      </button>
                    </div>
                    {validationErrors.password && (
                      <p className="text-red-400 text-sm">{validationErrors.password}</p>
                    )}
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button
                    onClick={handleNext}
                    className="bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white px-8"
                    disabled={isLoading}
                  >
                    Next <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step 2: Privacy & Consent */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <ConsentForm
                  consentOptions={SIGNUP_CONSENT_OPTIONS}
                  isInitialConsent={true}
                  onSubmit={handleConsentSubmit}
                  isLoading={isLoading}
                  error={error}
                />
                
                <div className="flex justify-between">
                  <Button
                    variant="outline"
                    onClick={handleBack}
                    className="border-white/20 text-white hover:bg-white/10"
                    disabled={isLoading}
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" /> Back
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Review & Create */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div className="bg-white/5 rounded-lg p-6 space-y-4">
                  <h3 className="text-lg font-semibold text-white mb-4">Review Your Information</h3>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-white/70">Name:</span>
                      <span className="text-white">{formData.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/70">Email:</span>
                      <span className="text-white">{formData.email}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/70">Consents Granted:</span>
                      <span className="text-white">{consents.filter(c => c.consent_value).length} of {consents.length}</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t border-white/10">
                    <h4 className="text-white font-medium mb-2">Your Consent Decisions:</h4>
                    <div className="space-y-2">
                      {consents.map((consent) => (
                        <div key={consent.consent_type} className="flex items-center justify-between text-sm">
                          <span className="text-white/70 capitalize">
                            {consent.consent_type.replace('_', ' ')}
                          </span>
                          <div className="flex items-center">
                            {consent.consent_value ? (
                              <><Check className="h-4 w-4 text-green-400 mr-1" /> Granted</>
                            ) : (
                              <span className="text-red-400">Denied</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between">
                  <Button
                    variant="outline"
                    onClick={handleBack}
                    className="border-white/20 text-white hover:bg-white/10"
                    disabled={isLoading}
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" /> Back
                  </Button>
                  
                  <Button
                    onClick={handleFinalSubmit}
                    className="bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white px-8"
                    disabled={isLoading}
                  >
                    {isLoading ? "Creating Account..." : "Create Account"}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}