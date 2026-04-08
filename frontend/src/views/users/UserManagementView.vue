<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { fetchDepartmentTree } from '@/api/modules/organization'
import { fetchUsers, updateUserMemberships, updateUserStatus } from '@/api/modules/users'
import type { DepartmentNode } from '@/types/organization'
import type { UserManagementItem } from '@/types/users'

interface DepartmentOption {
  label: string
  value: number
}

const authStore = useAuthStore()

const loading = ref(false)
const savingMemberships = ref(false)
const users = ref<UserManagementItem[]>([])
const departments = ref<DepartmentNode[]>([])
const membershipDialogVisible = ref(false)
const editingUser = ref<UserManagementItem | null>(null)

const filters = reactive({
  keyword: '',
  department_id: undefined as number | undefined,
  active_status: 'all' as 'all' | 'active' | 'inactive',
})

const membershipForm = reactive({
  department_ids: [] as number[],
  primary_department_id: undefined as number | undefined,
})

const departmentOptions = computed<DepartmentOption[]>(() => {
  const options: DepartmentOption[] = []

  function walk(nodes: DepartmentNode[], parentLabels: string[] = []) {
    nodes.forEach((node) => {
      const labels = [...parentLabels, node.name]
      options.push({
        label: labels.join(' / '),
        value: node.id,
      })
      if (node.children?.length) {
        walk(node.children, labels)
      }
    })
  }

  walk(departments.value)
  return options
})

const selectedPrimaryOptions = computed(() =>
  departmentOptions.value.filter((item) => membershipForm.department_ids.includes(item.value)),
)

const activeUserCount = computed(() => users.value.filter((item) => item.is_active).length)
const platformAdminCount = computed(() => users.value.filter((item) => item.is_platform_admin).length)
const pendingAssignmentCount = computed(
  () => users.value.filter((item) => item.organization_status === 'pending_assignment').length,
)

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '--'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', { hour12: false })
}

function getPrimaryDepartmentName(user: UserManagementItem): string {
  return user.memberships.find((item) => item.is_primary)?.department_name || '--'
}

function getMembershipNames(user: UserManagementItem): string {
  return user.memberships.length
    ? user.memberships.map((item) => item.department_name).join('、')
    : '--'
}

function getManagedDepartmentNames(user: UserManagementItem): string {
  return user.managed_departments.length
    ? user.managed_departments.map((item) => item.name).join('、')
    : '--'
}

async function loadDepartments() {
  const result = await fetchDepartmentTree()
  departments.value = result.items
}

async function loadUsers() {
  loading.value = true
  try {
    const result = await fetchUsers({
      keyword: filters.keyword.trim() || undefined,
      department_id: filters.department_id,
      is_active:
        filters.active_status === 'all' ? undefined : filters.active_status === 'active',
    })
    users.value = result.items
  } catch (error) {
    ElMessage.error('读取用户列表失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

function handleResetFilters() {
  filters.keyword = ''
  filters.department_id = undefined
  filters.active_status = 'all'
  void loadUsers()
}

function openMembershipDialog(user: UserManagementItem) {
  editingUser.value = user
  membershipForm.department_ids = user.memberships.map((item) => item.department_id)
  membershipForm.primary_department_id = user.memberships.find((item) => item.is_primary)?.department_id
  membershipDialogVisible.value = true
}

async function handleSaveMemberships() {
  if (!editingUser.value) {
    return
  }

  if (membershipForm.department_ids.length && !membershipForm.primary_department_id) {
    ElMessage.warning('请先指定一个主部门。')
    return
  }

  savingMemberships.value = true
  try {
    await updateUserMemberships(editingUser.value.id, {
      memberships: membershipForm.department_ids.map((departmentId) => ({
        department_id: departmentId,
        is_primary: departmentId === membershipForm.primary_department_id,
      })),
    })
    ElMessage.success('用户部门归属已更新。')
    membershipDialogVisible.value = false
    await loadUsers()
    if (editingUser.value.id === authStore.user?.id) {
      await authStore.fetchCurrentUser()
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存用户归属失败。')
    console.error(error)
  } finally {
    savingMemberships.value = false
  }
}

async function handleToggleStatus(user: UserManagementItem) {
  const nextStatus = !user.is_active

  if (!nextStatus) {
    try {
      await ElMessageBox.confirm(
        `确认禁用用户「${user.username}」吗？禁用后该账号将无法登录。`,
        '禁用用户',
        {
          type: 'warning',
          confirmButtonText: '确认禁用',
          cancelButtonText: '取消',
        },
      )
    } catch {
      return
    }
  }

  try {
    await updateUserStatus(user.id, { is_active: nextStatus })
    ElMessage.success(nextStatus ? '用户已启用。' : '用户已禁用。')
    await loadUsers()
    if (user.id === authStore.user?.id) {
      await authStore.fetchCurrentUser()
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '更新用户状态失败。')
    console.error(error)
  }
}

watch(
  () => [...membershipForm.department_ids],
  (departmentIds) => {
    if (!departmentIds.length) {
      membershipForm.primary_department_id = undefined
      return
    }
    if (!membershipForm.primary_department_id || !departmentIds.includes(membershipForm.primary_department_id)) {
      membershipForm.primary_department_id = departmentIds[0]
    }
  },
)

onMounted(async () => {
  try {
    await loadDepartments()
    await loadUsers()
  } catch (error) {
    console.error(error)
  }
})
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>用户管理</h2>
        <span>平台管理员可维护用户状态和部门归属</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button @click="loadUsers">刷新列表</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">用户总数</span>
        <strong class="summary-card__value">{{ users.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">启用用户</span>
        <strong class="summary-card__value">{{ activeUserCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">平台管理员</span>
        <strong class="summary-card__value">{{ platformAdminCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">待归属用户</span>
        <strong class="summary-card__value">{{ pendingAssignmentCount }}</strong>
      </el-card>
    </section>

    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <strong>用户列表</strong>
          <div class="table-toolbar__filters">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索用户名或邮箱"
              class="user-filter user-filter--wide"
              clearable
              @keyup.enter="loadUsers"
            />
            <el-select
              v-model="filters.department_id"
              clearable
              placeholder="按部门筛选"
              class="user-filter"
            >
              <el-option
                v-for="option in departmentOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
            <el-select
              v-model="filters.active_status"
              class="user-filter"
            >
              <el-option label="全部状态" value="all" />
              <el-option label="已启用" value="active" />
              <el-option label="已禁用" value="inactive" />
            </el-select>
            <el-button type="primary" @click="loadUsers">查询</el-button>
            <el-button @click="handleResetFilters">重置</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="users" stripe empty-text="当前没有用户数据">
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="email" label="邮箱" min-width="220" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="平台管理员" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.is_platform_admin" type="warning" effect="plain">是</el-tag>
            <span v-else>否</span>
          </template>
        </el-table-column>
        <el-table-column label="主部门" min-width="140">
          <template #default="{ row }">
            {{ getPrimaryDepartmentName(row) }}
          </template>
        </el-table-column>
        <el-table-column label="部门归属" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getMembershipNames(row) }}
          </template>
        </el-table-column>
        <el-table-column label="负责审批" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getManagedDepartmentNames(row) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="openMembershipDialog(row)">编辑归属</el-button>
            <el-button
              text
              :type="row.is_active ? 'danger' : 'success'"
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="membershipDialogVisible" title="编辑用户归属" width="560px">
      <el-form label-position="top">
        <el-form-item label="用户">
          <el-input :model-value="editingUser ? `${editingUser.username} · ${editingUser.email}` : ''" disabled />
        </el-form-item>

        <el-alert
          v-if="editingUser?.managed_departments.length"
          type="warning"
          :closable="false"
          show-icon
          class="user-membership-alert"
          :title="`该用户当前负责：${editingUser.managed_departments.map((item) => item.name).join('、')}`"
        />

        <el-form-item label="部门归属">
          <el-select
            v-model="membershipForm.department_ids"
            multiple
            clearable
            filterable
            placeholder="选择一个或多个部门"
            style="width: 100%"
          >
            <el-option
              v-for="option in departmentOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="主部门">
          <el-select
            v-model="membershipForm.primary_department_id"
            clearable
            :disabled="!membershipForm.department_ids.length"
            placeholder="选择主部门"
            style="width: 100%"
          >
            <el-option
              v-for="option in selectedPrimaryOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="membershipDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingMemberships" @click="handleSaveMemberships">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-filter {
  width: 180px;
}

.user-filter--wide {
  width: 260px;
}

.user-membership-alert {
  margin-bottom: 18px;
}

@media (max-width: 960px) {
  .user-filter,
  .user-filter--wide {
    width: 100%;
  }
}
</style>
