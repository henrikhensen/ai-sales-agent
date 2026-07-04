// Types mirror the backend Pydantic schemas exactly. Keep in sync with
// backend/agents/*/schemas.py and backend/api/v1/schemas/*.py.

export interface HealthComponent {
  status: "up" | "down";
}

export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  components: Record<string, HealthComponent>;
}

// -- Lead Research Agent ----------------------------------------------------

export interface LeadResearchRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  notes?: string | null;
}

export interface LeadResearchResponse {
  company_name: string;
  website_url: string | null;
  industry: string | null;
  location: string | null;
  short_summary: string;
  target_customers: string[];
  likely_pain_points: string[];
  possible_sales_angles: string[];
  confidence_score: number;
  missing_information: string[];
  sources_used: string[];
}

// -- Company Intelligence Agent ----------------------------------------------

export interface CompanyIntelligenceRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  company_description?: string | null;
  website_text?: string | null;
  known_products?: string[] | null;
  known_customers?: string[] | null;
  notes?: string | null;
}

export interface CompanyIntelligenceResponse {
  company_name: string;
  website_url: string | null;
  industry: string | null;
  location: string | null;
  business_summary: string;
  products_and_services: string[];
  target_segments: string[];
  likely_buyer_personas: string[];
  value_proposition: string[];
  positioning_summary: string;
  possible_competitive_context: string[];
  sales_relevance: string[];
  potential_business_challenges: string[];
  personalization_hooks: string[];
  missing_information: string[];
  sources_used: string[];
  confidence_score: number;
}

// -- Personalization Engine ---------------------------------------------------

export interface PersonalizationRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  lead_summary?: string | null;
  company_intelligence_summary?: string | null;
  target_persona?: string | null;
  product_or_service_offered: string;
  value_proposition?: string | null;
  known_pain_points?: string[] | null;
  known_triggers?: string[] | null;
  notes?: string | null;
}

export interface PersonalizationResponse {
  company_name: string;
  website_url: string | null;
  industry: string | null;
  personalization_summary: string;
  relevant_observations: string[];
  possible_conversation_starters: string[];
  pain_point_angles: string[];
  value_arguments: string[];
  credibility_points: string[];
  objection_risks: string[];
  suggested_ctas: string[];
  do_not_use_claims: string[];
  missing_information: string[];
  sources_used: string[];
  confidence_score: number;
}

// -- Email Draft Agent --------------------------------------------------------

export type EmailTone = "professional" | "friendly" | "concise" | "consultative";

export interface EmailDraftRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  recipient_role?: string | null;
  recipient_name?: string | null;
  sender_name?: string | null;
  sender_company?: string | null;
  product_or_service_offered: string;
  personalization_summary?: string | null;
  relevant_observations?: string[] | null;
  pain_point_angles?: string[] | null;
  value_arguments?: string[] | null;
  credibility_points?: string[] | null;
  suggested_ctas?: string[] | null;
  tone?: EmailTone | null;
  language?: string | null;
  notes?: string | null;
}

export interface EmailDraftResponse {
  company_name: string;
  subject_lines: string[];
  email_body: string;
  alternative_openings: string[];
  alternative_ctas: string[];
  personalization_used: string[];
  claims_to_verify: string[];
  do_not_send_if: string[];
  compliance_notes: string[];
  missing_information: string[];
  confidence_score: number;
}

// -- Reply Analysis Agent ------------------------------------------------------

export type ReplyClassification =
  | "interested"
  | "meeting_request"
  | "question"
  | "objection"
  | "not_interested"
  | "out_of_office"
  | "unclear";

export type ReplySentiment = "positive" | "neutral" | "negative" | "unclear";
export type ReplyUrgency = "low" | "medium" | "high" | "unclear";

export interface ReplyAnalysisRequest {
  company_name: string;
  lead_name?: string | null;
  lead_role?: string | null;
  original_email_subject?: string | null;
  original_email_body?: string | null;
  reply_text: string;
  previous_context?: string | null;
  product_or_service_offered?: string | null;
  notes?: string | null;
}

export interface ReplyAnalysisResponse {
  company_name: string;
  classification: ReplyClassification;
  sentiment: ReplySentiment;
  urgency: ReplyUrgency;
  summary: string;
  detected_intent: string[];
  recommended_next_action: string;
  suggested_reply: string | null;
  suggested_reply_subject: string | null;
  questions_to_answer: string[];
  objections_detected: string[];
  buying_signals: string[];
  do_not_continue_if: string[];
  compliance_notes: string[];
  missing_information: string[];
  confidence_score: number;
}

// -- CRM ------------------------------------------------------------------

export type LeadStatus = "new" | "contacted" | "qualified" | "won" | "lost";
export type LeadSource = "website" | "referral" | "outbound" | "event" | "other";

export interface Company {
  id: string;
  name: string;
  domain: string | null;
  industry: string | null;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  company_id: string;
  source: LeadSource;
  status: LeadStatus;
  score: number;
  created_at: string;
  updated_at: string;
}
