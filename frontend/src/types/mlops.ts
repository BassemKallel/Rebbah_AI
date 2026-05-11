export interface FallbackReasonStat {
  trigger_reason: string;
  count: number;
}

export interface MLOpsStats {
  reviewed_count: number;
  pending_review: number;
  total_fallbacks_30d: number;
  avg_tunbert_confidence: number;
  fallback_by_reason: FallbackReasonStat[];
  sparkline_7d: number[];
  last_retraining: RetrainingLog | null;
  total_embeddings: number;
  manual_count: number;
}

export interface ModelHealth {
  status: 'healthy' | 'unhealthy' | 'unreachable';
  version: string;
}

export interface ModelsHealthResponse {
  tunbert: ModelHealth;
  gliner: ModelHealth;
  clip: ModelHealth;
}

export interface NLUFallbackLog {
  id: number;
  message_id: number | null;
  original_text: string;
  tunbert_intent: string;
  tunbert_confidence: number;
  gemini_intent: string;
  gemini_confidence: number;
  trigger_reason: string;
  intent_changed: boolean;
  reviewed: boolean;
  review_label: string | null;
  created_at: string;
}

export interface PaginatedFallbacks {
  count: number;
  next: string | null;
  previous: string | null;
  results: NLUFallbackLog[];
}

export interface ManualDataset {
  id: number;
  original_text: string;
  label: string;
  source: string;
  created_at: string;
}

export interface PaginatedManualDatasets {
  count: number;
  next: string | null;
  previous: string | null;
  results: ManualDataset[];
}

export interface PerClassMetric {
  intent: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface TrainingReport {
  meta: {
    started_at: string;
    finished_at: string;
    duration_seconds: number;
    base_model: string;
    epochs: number;
    batch_size: number;
    samples_total: number;
  };
  training_curves: Array<{
    epoch: number;
    train_loss: number;
    val_loss: number;
    val_f1: number;
    val_acc: number;
  }>;
  evaluation: {
    new_model: {
      f1_weighted: number;
      f1_macro: number;
      accuracy: number;
    };
    per_class: PerClassMetric[];
    confusion_matrix: {
      labels: string[];
      matrix: number[][];
    };
  };
  dataset_distribution: Record<string, number>;
}

export interface RetrainingLog {
  id: number;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED' | 'PENDING_REVIEW';
  old_f1: number | null;
  new_f1: number | null;
  deployed: boolean;
  run_number: number | null;
  samples: number | null;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
  training_report: TrainingReport | null;
  duration_seconds: number | null;
  f1_improvement: number | null;
}

export interface RetrainingStatus {
  current: RetrainingLog | null;
  history: RetrainingLog[];
}
