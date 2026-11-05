import type {Status} from './types'

export const labels: Record<Status, string> = {
  pending: 'Choose a decision',
  complete: 'Antecedent list reviewed',
  no_reply: 'No reply relation identified',
  outside_context: 'Likely antecedent outside interval',
  ambiguous: 'Unable to decide',
  new_conversation: 'Start of a new conversation',
}
export const explanations: Record<Status, string> = {
  pending: 'Select antecedents or choose a no-link decision, then confirm.',
  complete: 'Confirms the reviewed antecedent list, which may be empty under the protocol.',
  no_reply: 'No reply relation was identified. This does not claim that a conversation starts here.',
  outside_context: 'Evidence suggests an antecedent outside this interval. No external link is invented.',
  ambiguous: 'Available context is insufficient to decide. The uncertainty is recorded.',
  new_conversation: 'You explicitly judged that this message starts a new topic.',
}
export const checklistLabels: Record<string, string> = {
  sources: 'I examined every target message and its decision.',
  components: 'I inspected the conversations and their internal links.',
  unassigned: 'I examined messages outside components, including no-link decisions.',
  interleaving: 'I reviewed the interleaved stream for missing connections.',
  uncertainty: 'I acknowledged ambiguities, uncertain relations, and out-of-context antecedents.',
  boundaries: 'This review is limited to the observed sample; conversation boundaries are not verified.',
}
