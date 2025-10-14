// Type definitions for Dating Wizard

export interface ReferenceImage {
  id: number;
  file_path: string;
  thumbnail_path?: string;
  category: string;
  description?: string;
  uploaded_at: string;
}

export interface Preference {
  id: number;
  physical_weight: number;
  personality_weight: number;
  interest_weight: number;
  min_score: number;
  super_like_score: number;
  age_min: number;
  age_max: number;
  updated_at: string;
}

export interface Keyword {
  id: number;
  keyword: string;
  keyword_type: 'positive' | 'negative' | 'required';
}

export interface Trait {
  id: number;
  trait: string;
}

export interface Interest {
  id: number;
  interest: string;
  is_dealbreaker: boolean;
}

export interface ClassificationReason {
  id: number;
  reason: string;
}

export interface ClassificationResult {
  id: number;
  screenshot_path: string;
  is_match: boolean;
  confidence_score: number;
  physical_score: number;
  personality_score: number;
  interest_score: number;
  name?: string;
  age?: number;
  bio?: string;
  created_at: string;
  reasons: ClassificationReason[];
  // Active learning feedback fields
  model_version_id?: number | null;
  user_feedback?: 'like' | 'dislike' | 'super_like' | null;
  feedback_at?: string | null;
}

export interface ClassifierStats {
  reference_images: number;
  positive_examples: number;
  negative_examples: number;
  total_training_data: number;
  weights: {
    physical_weight: number;
    personality_weight: number;
    interest_weight: number;
  };
  min_score_threshold: number;
  super_like_threshold: number;
}

export interface ResultsStats {
  total_classified: number;
  total_matches: number;
  match_rate: number;
  avg_confidence: number;
  classifications_today: number;
  matches_today: number;
}

export interface InstagramSearch {
  id: number;
  query: string;
  limit: number;
  min_score: number;
  total_found: number;
  matches_found: number;
  created_at: string;
  results: InstagramResult[];
}

export interface InstagramResult {
  id: number;
  username: string;
  name?: string;
  bio?: string;
  url?: string;
  followers?: number;
  profile_image_url?: string;

  // Classification fields (denormalized for quick access)
  screenshot_path?: string;
  confidence_score?: number;
  physical_score?: number;
  personality_score?: number;
  interest_score?: number;
  is_match?: boolean;

  // User feedback
  user_feedback?: 'like' | 'dislike' | 'super_like';
  feedback_at?: string;

  created_at: string;
  classification?: ClassificationResult;
}
