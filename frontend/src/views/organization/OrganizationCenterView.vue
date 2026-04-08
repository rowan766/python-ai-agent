<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  createDepartmentJoinRequest,
  fetchDepartmentTree,
  fetchMyDepartmentJoinRequests,
} from '@/api/modules/organization'
import type { DepartmentJoinRequestItem, DepartmentNode } from '@/types/organization'
import { formatMembershipLabel, getPrimaryMembership } from '@/utils/organization'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const submitting = ref(false)
const departments = ref<DepartmentNode[]>([])
const myRequests = ref<DepartmentJoinRequestItem[]>([])

const joinForm = reactive({
  target_department_id: undefined as number | undefined,
  reason: '',
})

const memberships = computed(() => authStore.user?.memberships ?? [])
const primaryMembership = computed(() => getPrimaryMembership(memberships.value))

async function loadData() {
  loading.value = true
  try {
    const [treeResult, requestResult] = await Promise.all([
      fetchDepartmentTree(),
      fetchMyDepartmentJoinRequests(),
    ])
    departments.value = treeResult.items
    myRequests.value = requestResult.items
    await authStore.fetchCurrentUser()
  } catch (error) {
    ElMessage.error('读取组织数据失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleJoinRequest() {
  if (!joinForm.target_department_id) {
    ElMessage.warning('请先选择目标部门。')
    return
  }

  if (!joinForm.reason.trim()) {
    ElMessage.warning('请填写申请原因。')
    return
  }

  submitting.value = true
  try {
    await createDepartmentJoinRequest({
      target_department_id: joinForm.target_department_id,
      requested_role_code: 'department_member',
      reason: joinForm.reason.trim(),
    })
    ElMessage.success('协作部门申请已提交。')
    joinForm.reason = ''
    await loadData()
  } catch (error) {
    ElMessage.error('申请提交失败，请确认是否已有待处理记录。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>组织与部门</h2>
        <span>主归属：{{ primaryMembership?.department_name || '未设置' }}</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button @click="router.push('/approvals')">审批中心</el-button>
        <el-button type="primary" @click="router.push('/departments')">部门治理</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">归属部门数</span>
        <strong class="summary-card__value">{{ memberships.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">主归属部门</span>
        <strong class="summary-card__value">{{ primaryMembership?.department_name || '--' }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">部门节点</span>
        <strong class="summary-card__value">{{ departments.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">我的申请记录</span>
        <strong class="summary-card__value">{{ myRequests.length }}</strong>
      </el-card>
    </section>

    <section class="split-grid">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>我的组织身份</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="memberships" stripe empty-text="暂无归属信息">
          <el-table-column prop="department_name" label="部门" min-width="180" />
          <el-table-column label="关系" min-width="140">
            <template #default="{ row }">
              {{ formatMembershipLabel(row) }}
            </template>
          </el-table-column>
          <el-table-column label="主部门" width="100">
            <template #default="{ row }">
              {{ row.is_primary ? '是' : '否' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="form-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>申请新的协作部门</strong>
          </div>
        </template>
        <el-form label-position="top">
          <el-form-item label="目标部门">
            <el-tree-select
              v-model="joinForm.target_department_id"
              :data="departments"
              node-key="id"
              check-strictly
              default-expand-all
              :props="{ label: 'name', children: 'children', value: 'id' }"
              placeholder="请选择目标部门"
            />
          </el-form-item>
          <el-form-item label="申请原因">
            <el-input
              v-model="joinForm.reason"
              type="textarea"
              :rows="4"
              placeholder="说明协作需求"
            />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleJoinRequest">
            提交申请
          </el-button>
        </el-form>
      </el-card>
    </section>

    <section class="split-grid">
      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>部门树</strong>
          </div>
        </template>
        <el-tree
          :data="departments"
          node-key="id"
          default-expand-all
          :props="{ label: 'name', children: 'children' }"
          empty-text="暂无部门"
        />
      </el-card>

      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>组织申请记录</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="myRequests" stripe empty-text="还没有发起过协作申请">
          <el-table-column prop="target_department_name" label="目标部门" min-width="160" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="reason" label="申请原因" min-width="220" show-overflow-tooltip />
          <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>
    </section>
  </div>
</template>
