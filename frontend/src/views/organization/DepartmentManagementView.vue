<script setup lang="ts">
import type { AxiosError } from 'axios'
import {
  createDepartment,
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
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const creating = ref(false)
const saving = ref(false)
const moving = ref(false)
const assigningManager = ref(false)
const departments = ref<DepartmentNode[]>([])
const selectedDepartment = ref<DepartmentNode | null>(null)
const departmentMembers = ref<DepartmentMemberItem[]>([])
const departmentImpact = ref<DepartmentImpact | null>(null)
const selectedManagerUserId = ref<number | undefined>(undefined)
const selectedParentId = ref<number | undefined>(undefined)

const createForm = reactive<CreateDepartmentPayload>({
  parent_id: undefined,
  code: '',
  name: '',
  full_name: '',
})

const editForm = reactive<UpdateDepartmentPayload>({
  name: '',
  full_name: '',
  status: 'active',
})

const departmentCount = computed(() => {
  function countNodes(items: DepartmentNode[]): number {
    return items.reduce((total, item) => total + 1 + countNodes(item.children ?? []), 0)
  }
  return countNodes(departments.value)
})

async function loadTree() {
  loading.value = true
  try {
    const result = await fetchDepartmentTree()
    departments.value = result.items
    if (selectedDepartment.value) {
      const refreshed = findDepartmentById(result.items, selectedDepartment.value.id)
      if (refreshed) {
        applySelection(refreshed)
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

function applySelection(node: DepartmentNode) {
  selectedDepartment.value = node
  editForm.name = node.name
  editForm.full_name = node.full_name
  editForm.status = node.status as 'active' | 'inactive'
  createForm.parent_id = node.id
  selectedParentId.value = node.parent_id ?? undefined
  void loadDepartmentContext(node.id)
}

async function loadDepartmentContext(departmentId: number) {
  try {
    const [memberResult, impactResult] = await Promise.all([
      fetchDepartmentMembers(departmentId),
      fetchDepartmentImpact(departmentId),
    ])
    departmentMembers.value = memberResult.items
    departmentImpact.value = impactResult
    selectedManagerUserId.value = findDepartmentById(departments.value, departmentId)?.manager_user_id ?? undefined
  } catch (error) {
    departmentMembers.value = []
    departmentImpact.value = null
    selectedManagerUserId.value = undefined
    console.error(error)
    ElMessage.error('读取部门上下文失败，请确认是否有管理权限。')
  }
}

async function handleCreateDepartment() {
  if (!createForm.code?.trim() || !createForm.name?.trim()) {
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
    createForm.code = ''
    createForm.name = ''
    createForm.full_name = ''
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
    ElMessage.warning('请先从左侧选择一个部门。')
    return
  }
  if (!editForm.name?.trim()) {
    ElMessage.warning('部门名称不能为空。')
    return
  }

  saving.value = true
  try {
    const willDisable =
      selectedDepartment.value.status === 'active' &&
      editForm.status === 'inactive' &&
      Boolean(departmentImpact.value) &&
      (
        (departmentImpact.value?.child_department_count ?? 0) > 0 ||
        (departmentImpact.value?.active_member_count ?? 0) > 0 ||
        (departmentImpact.value?.knowledge_base_count ?? 0) > 0 ||
        (departmentImpact.value?.document_count ?? 0) > 0
      )
    if (willDisable) {
      ElMessage.warning('当前部门下仍有成员、子部门或知识资产，已在右侧给出影响提示，请确认后再停用。')
    }
    await updateDepartment(selectedDepartment.value.id, {
      name: editForm.name.trim(),
      full_name: editForm.full_name?.trim() || editForm.name.trim(),
      status: editForm.status,
    })
    ElMessage.success('部门信息已更新。')
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '更新部门失败。')
    console.error(error)
  } finally {
    saving.value = false
  }
}

async function handleAssignManager() {
  if (!selectedDepartment.value || !selectedManagerUserId.value) {
    ElMessage.warning('请先选择一个成员作为部门负责人。')
    return
  }

  assigningManager.value = true
  try {
    await updateDepartmentManager(selectedDepartment.value.id, {
      manager_user_id: selectedManagerUserId.value,
    })
    ElMessage.success('部门负责人已更新。')
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '设置负责人失败。')
    console.error(error)
  } finally {
    assigningManager.value = false
  }
}

async function handleMoveDepartment() {
  if (!selectedDepartment.value) {
    ElMessage.warning('请先选择一个部门。')
    return
  }

  moving.value = true
  try {
    await updateDepartmentParent(selectedDepartment.value.id, {
      parent_id: selectedParentId.value,
    })
    ElMessage.success('部门层级已更新。')
    await loadTree()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '调整部门层级失败。')
    console.error(error)
  } finally {
    moving.value = false
  }
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
        <h2>这里才是建设和维护部门树的地方，不该让它缺席。</h2>
        <p class="page-copy">
          组织接入页负责“用户如何加入组织”，部门治理页负责“组织结构如何持续演进”。当前已经支持新增子部门和维护部门名称、全称、状态。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ departmentCount }}</span>
        <small>当前部门节点数</small>
      </div>
    </section>

    <section class="grid-two">
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
        />
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>创建子部门</template>
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
          <el-button type="primary" :loading="creating" @click="handleCreateDepartment">
            创建部门
          </el-button>
        </el-form>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>维护部门</template>
      <el-empty
        v-if="!selectedDepartment"
        description="先从左侧部门树选择一个节点，再维护它的基本信息。"
      />

      <el-form v-else label-position="top" class="department-edit-form">
        <el-form-item label="部门编码">
          <el-input :model-value="selectedDepartment.code" disabled />
        </el-form-item>
        <el-form-item label="调整上级部门">
          <el-tree-select
            v-model="selectedParentId"
            :data="departments"
            node-key="id"
            check-strictly
            default-expand-all
            clearable
            :props="{ label: 'name', children: 'children', value: 'id' }"
            placeholder="不选则作为根部门（仅平台管理员）"
          />
          <el-button class="section-action" :loading="moving" @click="handleMoveDepartment">
            更新层级
          </el-button>
        </el-form-item>
        <el-form-item label="部门负责人">
          <el-select
            v-model="selectedManagerUserId"
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
          <el-button class="section-action" type="primary" plain :loading="assigningManager" @click="handleAssignManager">
            设置负责人
          </el-button>
        </el-form-item>
        <el-form-item label="部门名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="部门全称">
          <el-input v-model="editForm.full_name" />
        </el-form-item>
        <el-form-item label="部门状态">
          <el-radio-group v-model="editForm.status">
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="inactive">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="handleSaveDepartment">
          保存修改
        </el-button>
      </el-form>
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
          <div class="impact-row">
            <span>下级部门</span>
            <strong>{{ departmentImpact.child_department_count }}</strong>
          </div>
          <div class="impact-row">
            <span>有效成员</span>
            <strong>{{ departmentImpact.active_member_count }}</strong>
          </div>
          <div class="impact-row">
            <span>知识库空间</span>
            <strong>{{ departmentImpact.knowledge_base_count }}</strong>
          </div>
          <div class="impact-row">
            <span>文档数量</span>
            <strong>{{ departmentImpact.document_count }}</strong>
          </div>
          <p class="impact-note">
            停用部门前，建议先评估下级部门、成员和知识资产的承接关系，避免把组织树和权限范围直接切断。
          </p>
        </div>
        <el-empty v-else description="选择部门后会显示当前影响范围。" />
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.department-edit-form {
  max-width: 720px;
}

.section-action {
  margin-top: 12px;
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
