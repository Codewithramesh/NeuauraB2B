export interface Organization {
  id: string;
  name: string;
  industry: string;
  categories: string[];
}
export interface UserContext {
  user: { id: string; email: string };
  organization: Organization;
  csrf: string;
}
export interface Evidence {
  id: string;
  quote: string;
  start: number | null;
  end: number | null;
}
export interface Insight {
  id: string;
  conversation_id: string;
  title: string;
  description: string;
  category: string;
  topic: string;
  sentiment: string;
  basis: string;
  confidence: number;
  uncertainty: string;
  evidence: Evidence[];
  created_at: string;
}
export interface Task {
  id: string;
  conversation_id: string;
  description: string;
  priority: string;
  owner: string | null;
  due_date: string | null;
  status: string;
  created_at: string;
}
export interface Job {
  status: string;
  stage: string;
  attempts: number;
  error_code: string | null;
  error_message: string | null;
  retryable: boolean;
}
export interface Conversation {
  id: string;
  title: string;
  status: string;
  source_type: string;
  device_id: string | null;
  duration: number | null;
  created_at: string;
  summary: string | null;
  topics: string[];
  entities: string[];
  job: Job | null;
}
export interface ConversationDetail extends Conversation {
  transcript: {
    text: string;
    segments: { start: number; end: number; text: string }[];
    provider: string;
    model: string;
  } | null;
  insights: Insight[];
  tasks: Task[];
  audio_retained: boolean;
  consent: { attested: boolean; created_at: string };
}
export interface Device {
  id: string;
  name: string;
  device_type: string;
  model: string;
  firmware: string | null;
  status: string;
  simulated: boolean;
  battery: number | null;
  last_seen: string | null;
  connection: string;
}
export interface Overview {
  total_conversations: number;
  succeeded: number;
  failed: number;
  processing: number;
  positive: number;
  negative: number;
  open_tasks: number;
  complaints: { topic: string; count: number }[];
  requests: { topic: string; count: number }[];
  recent_insights: Insight[];
  trend: {
    date: string;
    conversations: number;
    positive: number;
    negative: number;
  }[];
}
export interface Settings {
  organization: Organization;
  retain_audio: boolean;
  retention_days: number;
  max_upload_mb: number;
  max_duration_seconds: number;
  language: string;
  transcription: { provider: string; model: string; ready: boolean };
  extraction: {
    provider: string;
    model: string;
    ready: boolean;
    cloud_enabled: boolean;
  };
  categories: string[];
  profiles: Record<string, string[]>;
}
