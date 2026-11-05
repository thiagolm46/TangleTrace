export type Status = 'pending' | 'complete' | 'no_reply' | 'outside_context' | 'ambiguous' | 'new_conversation'
export type Confidence = 'high' | 'medium' | 'low'
export interface Edge {
  target_message_id: string
  relation: 'reply'
  ambiguous: boolean
  confidence: Confidence
  notes: string
}
export interface Decision {
  source_status: Status
  edges: Edge[]
  confidence: Confidence
  notes: string
  unresolved_additional_relation: boolean
  unresolved_reason: string
}
export interface Message {
  message_id: string
  sequence: number
  guild_id: string
  channel_id: string
  author_id: string
  author_username?: string
  content: string
  timestamp?: string
  native_reply_to_message_id?: string | null
  requires_reply_annotation: boolean
  window_role: 'context' | 'annotated'
}
export interface Session {
  id: string
  import_id: string
  sample_id: string
  annotator_id: string
  label: string
  kind: 'single_annotator' | 'adjudication'
  graph_revision: number
  cursor: string | null
  confirmed?: number
  validated?: boolean
}
export interface SampleWindow {
  sample_id: string
  annotation_id: string
  guild_name: string
  channel_name: string
  period?: string
  annotated_message_count: number
  context_message_count: number
  sessions: Session[]
}
export interface Component {
  signature: string
  conversation_id: string
  message_ids: string[]
  participants: number
  reviewed: boolean
  includes_context: boolean
  start: string
}
export interface AnnotationState {
  session: Session
  window: SampleWindow
  messages: Message[]
  decisions: Record<string, Decision>
  drafts: Record<string, {decision: Decision; updated_at: string; base_revision: number}>
  components: Component[]
  pending: string[]
  unassigned: string[]
  validated: boolean
  review_blockers: string[]
  progress: {confirmed: number; total: number; active_ms: number}
}
export interface Config {
  version: string
  default_source: string
  workspace: string
  database: string
  exports: string
}
export interface ImportRecord {
  id: string
  name: string
  source_path: string
  provenance: {window_count: number; target_count: number; diagnostics: string[]}
}
export interface Comparison {
  left: Session
  right: Session
  comparable_sources: number
  exact_decision_agreement: number | null
  link_jaccard: number | null
  component_pair_jaccard: number | null
  component_comparable_nodes: number
  rows: {message_id: string; left: Decision; right: Decision; comparable: boolean; agree: boolean}[]
}
export interface ExportResult {
  directory: string
  manifest: Record<string, unknown>
}
export interface HistoryEvent {
  id: number
  event_type: string
  revision: number
  created_at: string
  source_id: string | null
  actor_id: string
  after_data: string | null
}
export interface Job {
  status: 'running' | 'done' | 'error'
  message: string
  result?: {import_id: string; reused: boolean}
}
type Revision = {session_id: string; expected_revision: number}
type DraftParams = Revision & {source_id: string; decision: Decision; expected_draft_updated: string | null}
export interface Protocol {
  config: [Record<string, never>, Config]
  imports: [Record<string, never>, ImportRecord[]]
  windows: [{import_id: string; annotator_id: string}, SampleWindow[]]
  state: [{session_id: string}, AnnotationState]
  sessions: [{import_id: string; sample_id: string}, Session[]]
  compare: [{left: string; right: string}, Comparison]
  history: [{session_id: string}, HistoryEvent[]]
  job: [{job_id: string}, Job]
  import: [{path: string}, {job_id: string}]
  demo: [Record<string, never>, {job_id: string}]
  open_session: [{import_id: string; sample_id: string; annotator_id: string; label: string; kind?: Session['kind']; bases?: string[]}, Session]
  cursor: [{session_id: string; source_id: string}, {saved: boolean}]
  draft: [DraftParams, {saved: boolean; updated_at: string | null}]
  discard_draft: [{session_id: string; source_id: string; expected_draft_updated: string | null}, {saved: boolean}]
  confirm: [DraftParams & {active_ms: number}, AnnotationState]
  undo: [Revision, AnnotationState]
  redo: [Revision, AnnotationState]
  review_component: [Revision & {signature: string}, AnnotationState]
  review_interval: [Revision & {checklist: Record<string, boolean>}, AnnotationState]
  export: [Revision, ExportResult]
  backup: [Record<string, never>, {path: string}]
}
