const pad = (value) => String(value).padStart(2, '0')

export function parseServerTime(value) {
  if (!value) return null
  if (value instanceof Date) return value
  const text = String(value)
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(text)) return new Date(text)
  return new Date(`${text.replace(' ', 'T')}Z`)
}

export function fmtDateTime(value) {
  const date = parseServerTime(value)
  if (!date || Number.isNaN(date.getTime())) return '—'
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function fmtDate(value) {
  const date = parseServerTime(value)
  if (!date || Number.isNaN(date.getTime())) return '—'
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function fmtTime(value) {
  const date = parseServerTime(value)
  if (!date || Number.isNaN(date.getTime())) return '—'
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function toLocalInput(value) {
  const date = parseServerTime(value)
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function fromLocalInput(value) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString().slice(0, 19)
}

export function roundState(round) {
  if (!round) return { key: 'none', text: '暂无轮次' }
  if (round.is_open) return { key: 'open', text: '进行中' }
  const now = Date.now()
  const start = parseServerTime(round.starts_at)?.getTime() ?? 0
  const end = parseServerTime(round.ends_at)?.getTime() ?? 0
  if (now < start) return { key: 'upcoming', text: '未开始' }
  if (now > end) return { key: 'closed', text: '已结束' }
  return { key: 'open', text: '进行中' }
}

export const ROLE_TEXT = {
  student: '学生',
  mentor: '老师',
  admin: '管理员',
}

export const STAGE_TEXT = {
  not_applied: '未填报',
  applied: '已填报',
  interviewed: '已面试',
  offered: '待确认',
  enrolled: '已入组',
}

export const STAGE_TAG = {
  not_applied: 'info',
  applied: 'primary',
  interviewed: 'primary',
  offered: 'warning',
  enrolled: 'success',
}

export const OFFER_STATUS_TEXT = {
  pending: '待确认',
  confirmed: '已确认',
  rejected: '已放弃',
  expired: '已过期',
}

export const OFFER_STATUS_TAG = {
  pending: 'warning',
  confirmed: 'success',
  rejected: 'danger',
  expired: 'info',
}

export const OFFER_TYPE_TEXT = {
  regular: '拟录取',
  supplement: '递补',
  internal: '内部调剂',
  cross: '跨室调剂',
  assigned: '约谈安置',
}

export const DECISION_TEXT = {
  proposed: '拟录取',
  waitlist: '递补',
  internal_candidate: '内部调剂候选',
  rejected: '不推荐',
}

export const DECISION_TAG = {
  proposed: 'success',
  waitlist: 'warning',
  internal_candidate: 'primary',
  rejected: 'danger',
}

export const ROUND_KIND_TEXT = {
  briefing: '集中宣讲',
  open_day: '开放日',
  intention: '志愿填报',
  interview: '统一面试',
  confirm: '拟录取确认',
  supplement: '分轮补录',
  adjust: '统筹调剂',
  publish: '结果公示',
}

export const ROUND_KIND_TONE = {
  briefing: 'green',
  open_day: 'green',
  intention: 'blue',
  interview: 'orange',
  confirm: 'blue',
  supplement: 'green',
  adjust: 'navy',
  publish: 'navy',
}

export const APPEAL_STATUS_TEXT = {
  open: '待处理',
  accepted: '已受理',
  rejected: '已驳回',
  closed: '已办结',
}

export const APPEAL_STATUS_TAG = {
  open: 'warning',
  accepted: 'primary',
  rejected: 'danger',
  closed: 'success',
}

export const PUBLICATION_STATUS_TEXT = {
  draft: '草稿',
  published: '已发布',
  closed: '已结束',
}

export const PUBLICATION_STATUS_TAG = {
  draft: 'info',
  published: 'success',
  closed: 'info',
}

export function totalScore(row) {
  if (!row) return 0
  return (
    Number(row.score_attitude || 0) +
    Number(row.score_logic || 0) +
    Number(row.score_code || 0) +
    Number(row.score_time || 0)
  )
}

export function quotaPercent(taken, quota) {
  if (!quota) return 0
  return Math.min(100, Math.round((Number(taken) / Number(quota)) * 100))
}

export const ACTION_TEXT = {
  register: '注册账号',
  create_user: '创建账号',
  reset_password: '重置密码',
  submit_intentions: '提交志愿',
  create_interview: '录入面试',
  update_interview: '修改面试',
  run_selection: '运行选拔',
  confirm_offer: '确认录取',
  expire_offers: '逾期释放',
  fill_vacancy: '顺位补录',
  adjust: '统筹调剂',
  assign_talk: '约谈安置',
  create_lab: '新建实训室',
  update_lab: '更新实训室',
  delete_lab: '删除实训室',
  create_mentor: '新建导师',
  update_mentor: '更新导师',
  delete_mentor: '删除导师',
  create_round: '新建轮次',
  update_round: '更新轮次',
  create_publication: '新建公示',
  publish: '发布公示',
  create_appeal: '提交申诉',
  handle_appeal: '处理申诉',
}

export function actionText(action) {
  return ACTION_TEXT[action] || action || '—'
}

export function jsonText(value) {
  if (!value) return '—'
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return String(value)
  }
}
