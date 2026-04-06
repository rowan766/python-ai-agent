<script setup lang="ts">
import type { AxiosError } from 'axios'
import { CirclePlus, Delete, EditPen, Rank } from '@element-plus/icons-vue'
import {
  createDepartment,
  deleteDepartment,
  fetchDepartmentImpact,
  fetchDepartmentMembers,
  fetchDepartmentTree,
  updateDepartment,
  updateDepartmentManager,
  updateDepartmentParent,
} from '@/api/modules/organization'
import type {
  CreateDepartmentPayload,
  DepartmentImpact,
  DepartmentMemberItem,
  DepartmentNode,
  UpdateDepartmentPayload,
} from '@/types/organization'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const departments = ref<DepartmentNode[]>([])
const selectedDepartment = ref<DepartmentNode | null>(null)
const departmentMembers = ref<DepartmentMemberItem[]>([])
const departmentImpact = ref<DepartmentImpact | null>(null)

const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const moveDialogVisible = ref(false)
const creating = ref(false)
const saving = ref(false)
const moving = ref(false)
const deleting = ref(false)

const createForm = reactive<CreateDepartmentPayload>({
  parent_id: undefined,
  code: '',
  name: '',
  full_name: '',
})

const editForm = reactive<
  UpdateDepartmentPayload & { manager_user_id?: number }
>({
  name: '',
  full_name: '',
  status: 'active',
  manager_user_id: undefined,
})

const moveParentId = ref<number | undefined>(undefined)

const departmentCount = computed(() => {
  function countNodes(items: DepartmentNode[]): number {
    return items.reduce((total, item) => total + 1 + countNodes(item.children ?? []), 0)
  }
  return countNodes(departments.value)
})

const impactRows = computed(() => [
  { label: '下级部门', value: departmentImpact.value?.child_department_count ?? 0 },
  { label: '有效成员', value: departmentImpact.value?.active_member_count ?? 0 },
  { label: '知识库空间', value: departmentImpact.value?.knowledge_base_count ?? 0 },
  { label: '文档数量', value: departmentImpact.value?.document_count ?? 0 },
  { label: '共享关系', value: departmentImpact.value?.active_share_count ?? 0 },
  { label: '待处理共享申请', value: departmentImpact.value?.pending_share_request_count ?? 0 },
])

async function loadTree() {
  loading.value = true
  try {
    const result = await fetchDepartmentTree()
    departments.value = result.items
    if (selectedDepartment.value) {
      const refreshed = findDepartmentById(result.items, selectedDepartment.value.id)
      if (refreshed) {
        await applySelection(refreshed)
      } else {
        selectedDepartment.value = null
        departmentMembers.value = []
        departmentImpact.value = null
      }
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('读取部门树失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function findDepartmentById(items: DepartmentNode[], departmentId: number): DepartmentNode | null {
  for (const item of items) {
    if (item.id === departmentId) {
      return item
    }
    const matched = findDepartmentById(item.children ?? [], departmentId)
    if (matched) {
      return matched
    }
  }
  return null
}

async function applySelection(node: DepartmentNode) {
  selectedDepartment.value = node
  moveParentId.value = node.parent_id ?? undefined
  await loadDepartmentContext(node.id)
}

async function loadDepartmentContext(departmentId: number) {
  try {
    const [memberResult, impactResult] = await Promise.all([
      fetchDepartmentMembers(departmentId),
      fetchDepartmentImpact(departmentId),
    ])
    departmentMembers.value = memberResult.items
    departmentImpact.value = impactResult
  } catch (error) {
    departmentMembers.value = []
    departmentImpact.value = null
    console.error(error)
  }
}

function resetCreateForm() {
  createForm.parent_id = undefined
  createForm.code = ''
  createForm.name = ''
  createForm.full_name = ''
}

function openCreateDialog(node?: DepartmentNode) {
  resetCreateForm()
  createForm.parent_id = node?.id
  createDialogVisible.value = true
}

function openEditDialog(node: DepartmentNode) {
  selectedDepartment.value = node
  editForm.name = node.name
  editForm.full_name = node.full_name
  editForm.status = node.status as 'active' | 'inactive'
  editForm.manager_user_id = node.manager_user_id ?? undefined
  if (!departmentMembers.value.length || selectedDepartment.value?.id !== node.id) {
    void applySelection(node).then(() => {
      editForm.manager_user_id = selectedDepartment.value?.manager_user_id ?? undefined
    })
  }
  editDialogVisible.value = true
}

function openMoveDialog(node: DepartmentNode) {
  selectedDepartment.value = node
  moveParentId.value = node.parent_id ?? undefined
  moveDialogVisible.value = true
}

async function handleCreateDepartment() {
  if (!createForm.code.trim() || !createForm.name.trim()) {
    ElMessage.warning('请输入部门编码和名称。')
    return
  }

  creating.value = true
  try {
    await createDepartment({
      parent_id: createForm.parent_id,
      code: createForm.code.trim(),
      name: createForm.name.trim(),
      full_name: createForm.full_name?.trim() || undefined,
    })
    ElMessage.success('部门创建成功。')
    createDialogVisible.value = false
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '创建部门失败。')
    console.error(error)
  } finally {
    creating.value = false
  }
}

async function handleSaveDepartment() {
  if (!selectedDepartment.value) {
    return
  }
  if (!editForm.name?.trim()) {
    ElMessage.warning('部门名称不能为空。')
    return
  }

  saving.value = true
  try {
    await updateDepartment(selectedDepartment.value.id, {
      name: editForm.name.trim(),
      full_name: editForm.full_name?.trim() || editForm.name.trim(),
      status: editForm.status,
    })

    if (
      editForm.manager_user_id &&
      editForm.manager_user_id !== selectedDepartment.value.manager_user_id
    ) {
      await updateDepartmentManager(selectedDepartment.value.id, {
        manager_user_id: editForm.manager_user_id,
      })
    }

    ElMessage.success('部门信息已更新。')
    editDialogVisible.value = false
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string | { message?: string } }>
    const detail = axiosError.response?.data?.detail
    const message =
      typeof detail === 'string' ? detail : detail?.message || '更新部门失败。'
    ElMessage.error(message)
    console.error(error)
  } finally {
    saving.value = false
  }
}

async function handleMoveDepartment() {
  if (!selectedDepartment.value) {
    return
  }

  moving.value = true
  try {
    await updateDepartmentParent(selectedDepartment.value.id, {
      parent_id: moveParentId.value,
    })
    ElMessage.success('部门层级已更新。')
    moveDialogVisible.value = false
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '调整部门层级失败。')
    console.error(error)
  } finally {
    moving.value = false
  }
}

async function handleDeleteDepartment(node: DepartmentNode) {
  let impactText = ''
  try {
    const impact = await fetchDepartmentImpact(node.id)
    impactText = `下级部门 ${impact.child_department_count} 个，成员 ${impact.active_member_count} 人，知识库 ${impact.knowledge_base_count} 个，文档 ${impact.document_count} 份，共享关系 ${impact.active_share_count} 条。`
  } catch {
    impactText = '删除前影响信息读取失败，仍可以继续尝试删除。'
  }

  try {
    await ElMessageBox.confirm(
      `${impactText}\n\n确认删除部门「${node.name}」吗？`,
      '删除部门',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    await deleteDepartment(node.id)
    ElMessage.success('部门已删除。')
    if (selectedDepartment.value?.id === node.id) {
      selectedDepartment.value = null
      departmentMembers.value = []
      departmentImpact.value = null
    }
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string | { message?: string; impact?: unknown } }>
    const detail = axiosError.response?.data?.detail
    const message =
      typeof detail === 'string' ? detail : detail?.message || '删除部门失败。'
    ElMessage.error(message)
    console.error(error)
  } finally {
    deleting.value = false
  }
}

function renderActionLabel(node: DepartmentNode) {
  return `${node.name}${node.status === 'inactive' ? '（已停用）' : ''}`
}

onMounted(async () => {
  await loadTree()
})
</script>

<template>
  <div class="page">
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">Department Governance</p>
        <h2>把组织治理动作收回到部门树本身，点到哪里就管理哪里。</h2>
        <p class="page-copy">
          现在新增、编辑、删除和调整层级都直接挂在树节点上，部门树本身就是主要操作面。下面保留成员和影响信息，作为你做决策时的辅助区。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ departmentCount }}</span>
        <small>当前部门节点数</small>
        <el-button type="primary" @click="openCreateDialog()">新增根部门</el-button>
      </div>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>部门树</template>
      <el-tree
        v-loading="loading"
        :data="departments"
        node-key="id"
        default-expand-all
        :props="{ label: 'name', children: 'children' }"
        highlight-current
        empty-text="暂无部门"
        @node-click="applySelection"
      >
        <template #default="{ data }">
          <div class="tree-node">
            <div class="tree-node__label">
              <span>{{ renderActionLabel(data) }}</span>
              <el-tag v-if="data.id === selectedDepartment?.id" size="small" round>当前选中</el-tag>
            </div>
            <div class="tree-node__actions">
              <el-button text size="small" @click.stop="openCreateDialog(data)">
                <el-icon><CirclePlus /></el-icon>
                <span>新增</span>
              </el-button>
              <el-button text size="small" @click.stop="openEditDialog(data)">
                <el-icon><EditPen /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button text size="small" @click.stop="openMoveDialog(data)">
                <el-icon><Rank /></el-icon>
                <span>调整</span>
              </el-button>
              <el-button text size="small" type="danger" @click.stop="handleDeleteDepartment(data)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </div>
        </template>
      </el-tree>
    </el-card>

    <section v-if="selectedDepartment" class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>部门成员</template>
        <el-table :data="departmentMembers" empty-text="当前部门还没有可见成员">
          <el-table-column prop="username" label="成员" min-width="140" />
          <el-table-column prop="email" label="邮箱" min-width="200" />
          <el-table-column prop="membership_type" label="关系" width="120" />
          <el-table-column prop="is_primary" label="主部门" width="100">
            <template #default="{ row }">
              {{ row.is_primary ? '是' : '否' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>影响提示</template>
        <div v-if="departmentImpact" class="impact-stack">
          <div v-for="item in impactRows" :key="item.label" class="impact-row">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <p class="impact-note">
            删除或停用前，先看这里的影响范围。只要还挂着下级部门、知识库或共享关系，就不应该直接清掉节点。
          </p>
        </div>
        <el-empty v-else description="选择部门后会显示当前影响范围。" />
      </el-card>
    </section>

    <el-dialog v-model="createDialogVisible" title="新增部门" width="520px">
      <el-form label-position="top">
        <el-form-item label="上级部门">
          <el-tree-select
            v-model="createForm.parent_id"
            :data="departments"
            node-key="id"
            check-strictly
            default-expand-all
            clearable
            :props="{ label: 'name', children: 'children', value: 'id' }"
            placeholder="不选则创建根部门（仅平台管理员）"
          />
        </el-form-item>
        <el-form-item label="部门编码">
          <el-input v-model="createForm.code" placeholder="例如 dept-rd-platform" />
        </el-form-item>
        <el-form-item label="部门名称">
          <el-input v-model="createForm.name" placeholder="例如 平台研发部" />
        </el-form-item>
        <el-form-item label="部门全称">
          <el-input v-model="createForm.full_name" placeholder="例如 研发中心 / 平台研发部" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateDepartment">
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑部门" width="560px">
      <el-form label-position="top">
        <el-form-item label="部门名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="部门全称">
          <el-input v-model="editForm.full_name" />
        </el-form-item>
        <el-form-item label="部门负责人">
          <el-select
            v-model="editForm.manager_user_id"
            placeholder="请选择负责人"
            style="width: 100%"
          >
            <el-option
              v-for="member in departmentMembers"
              :key="member.user_id"
              :label="`${member.username} · ${member.email}`"
              :value="member.user_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门状态">
          <el-radio-group v-model="editForm.status">
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="inactive">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveDepartment">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="moveDialogVisible" title="调整部门层级" width="520px">
      <el-form label-position="top">
        <el-form-item label="新的上级部门">
          <el-tree-select
            v-model="moveParentId"
            :data="departments"
            node-key="id"
            check-strictly
            default-expand-all
            clearable
            :props="{ label: 'name', children: 'children', value: 'id' }"
            placeholder="不选则作为根部门（仅平台管理员）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="moving" @click="handleMoveDepartment">
          更新层级
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 4px 0;
}

.tree-node__label {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: var(--page-green-deep);
}

.tree-node__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.tree-node:hover .tree-node__actions {
  opacity: 1;
}

.impact-stack {
  display: grid;
  gap: 12px;
}

.impact-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid rgba(24, 54, 48, 0.08);
  border-radius: 16px;
  background: rgba(255, 253, 248, 0.9);
  color: var(--page-muted);
}

.impact-row strong {
  color: var(--page-green-deep);
  font-size: 20px;
}

.impact-note {
  margin: 0;
  color: var(--page-muted);
  line-height: 1.8;
}
</style>
