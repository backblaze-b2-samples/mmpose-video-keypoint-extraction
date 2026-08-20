export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// ---- MMPose keypoint-extraction domain ----------------------------------

export type RunStatus = "pending" | "running" | "done" | "error";
export type ModelName = "human" | "wholebody" | "hand" | "human3d";
export type DeviceChoice = "auto" | "cpu" | "cuda" | "mps";

export interface FrameKeypoints {
  frame: string;
  source_key: string;
  keypoints_key: string | null;
  overlay_key: string | null;
  num_instances: number;
  num_keypoints: number;
  mean_score: number;
}

export interface RunSummary {
  frame_count: number;
  total_instances: number;
  total_keypoints: number;
  source_bytes: number;
  derived_bytes: number;
  amplification_ratio: number;
}

/** The primary entity — persisted as a B2 JSON manifest, no database. */
export interface RunRecord {
  id: string;
  label: string;
  session: string;
  model: ModelName;
  device: DeviceChoice;
  kpt_thr: number;
  status: RunStatus;
  created_at: string;
  updated_at: string;
  notes: string;
  tags: string[];
  manifest_key: string;
  error: string | null;
  frames: FrameKeypoints[];
  summary: RunSummary;
}

export interface CreateRunRequest {
  label: string;
  session: string;
  model: ModelName;
  kpt_thr: number;
  device: DeviceChoice;
}

export interface UpdateRunRequest {
  label?: string;
  notes?: string;
  tags?: string[];
}

export interface SessionInfo {
  session: string;
  frame_count: number;
}

export interface EngineStatus {
  available: boolean;
  device: string;
  torch_installed: boolean;
  detail: string;
}

export interface RunActivityPoint {
  date: string;
  runs: number;
}

export interface PoseStats {
  total_runs: number;
  runs_done: number;
  runs_running: number;
  runs_error: number;
  sessions: number;
  frames_available: number;
  frames_processed: number;
  total_instances: number;
  total_keypoints: number;
  source_bytes: number;
  derived_bytes: number;
  source_bytes_human: string;
  derived_bytes_human: string;
  amplification_ratio: number;
  activity: RunActivityPoint[];
}

export interface LibraryStage {
  stage: string;
  object_count: number;
  total_bytes: number;
  total_bytes_human: string;
}

export interface LibrarySummary {
  prefix: string;
  stages: LibraryStage[];
  total_objects: number;
  total_bytes: number;
  total_bytes_human: string;
}
