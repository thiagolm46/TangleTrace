import type {AnnotationState, Decision, Message} from './types'

export const emptyDecision = (): Decision => ({
  source_status: 'pending', edges: [], notes: '', confidence: 'high',
  unresolved_additional_relation: false, unresolved_reason: '',
})
export function fixture(): AnnotationState {
  const messages: Message[] = [
    {message_id: 'P01', sequence: 1, guild_id: 'G', channel_id: 'C', author_id: 'A', content: '<img src=x onerror=alert(1)> Database question', window_role: 'context', requires_reply_annotation: false},
    {message_id: 'P02', sequence: 2, guild_id: 'G', channel_id: 'C', author_id: 'B', content: 'Use a fixture.', window_role: 'annotated', requires_reply_annotation: true},
    {message_id: 'P03', sequence: 3, guild_id: 'G', channel_id: 'C', author_id: 'A', content: 'It worked, thanks!', native_reply_to_message_id: 'P01', window_role: 'annotated', requires_reply_annotation: true},
    {message_id: 'P04', sequence: 4, guild_id: 'G', channel_id: 'C', author_id: 'B', content: 'Great!', native_reply_to_message_id: 'P03', window_role: 'annotated', requires_reply_annotation: true},
    {message_id: 'P05', sequence: 5, guild_id: 'G', channel_id: 'C', author_id: 'A', content: 'External reply', native_reply_to_message_id: 'OUTSIDE', window_role: 'annotated', requires_reply_annotation: true},
    {message_id: 'P06', sequence: 6, guild_id: 'G', channel_id: 'C', author_id: 'A', content: 'Invalid self-reference', native_reply_to_message_id: 'P06', window_role: 'annotated', requires_reply_annotation: true},
  ]
  return {
    session: {id: 'session', import_id: 'sample', sample_id: 'window', annotator_id: 'annotator-a', label: 'Primary', kind: 'single_annotator', graph_revision: 0, cursor: 'P03'},
    window: {sample_id: 'window', annotation_id: 'window', guild_name: 'Example server', channel_name: 'development', annotated_message_count: 5, context_message_count: 1, sessions: []},
    messages,
    decisions: Object.fromEntries(messages.filter(message => message.requires_reply_annotation).map(message => [message.message_id, emptyDecision()])),
    drafts: {}, components: [], pending: ['P02', 'P03', 'P04', 'P05', 'P06'], unassigned: messages.map(message => message.message_id),
    validated: false, review_blockers: ['5 pending messages'], progress: {confirmed: 0, total: 5, active_ms: 0},
  }
}
