import type { MembershipSummary } from '@/types/auth'
import { getActiveDepartmentId } from '@/utils/storage'

const VISIBILITY_LABELS: Record<string, string> = {
  knowledge_base_default: '沿用空间策略',
  department_private: '本部门可见',
  department_shared: '已共享给相关部门',
  org_public: '全组织可见',
}

const REQUESTED_ROLE_LABELS: Record<string, string> = {
  department_member: '部门成员',
  knowledge_operator: '资料上传协作者',
  knowledge_reviewer: '知识审核协作者',
}

const MEMBERSHIP_KIND_LABELS: Record<string, string> = {
  primary: '主归属部门',
  secondary: '协作部门',
}

export function formatVisibilityScope(scope: string): string {
  return VISIBILITY_LABELS[scope] ?? scope
}

export function formatRequestedRole(roleCode?: string | null): string {
  if (!roleCode) {
    return '部门成员'
  }
  return REQUESTED_ROLE_LABELS[roleCode] ?? roleCode
}

export function getPrimaryMembership(memberships: MembershipSummary[]): MembershipSummary | null {
  return memberships.find((item) => item.is_primary) ?? memberships[0] ?? null
}

export function getPreferredMembership(memberships: MembershipSummary[]): MembershipSummary | null {
  const activeDepartmentId = getActiveDepartmentId()
  if (activeDepartmentId !== null) {
    const matched = memberships.find((item) => item.department_id === activeDepartmentId)
    if (matched) {
      return matched
    }
  }
  return getPrimaryMembership(memberships)
}

export function formatMembershipLabel(membership: MembershipSummary): string {
  const label = MEMBERSHIP_KIND_LABELS[membership.membership_type] ?? membership.membership_type
  if (membership.is_primary) {
    return '主归属部门'
  }
  return label
}
