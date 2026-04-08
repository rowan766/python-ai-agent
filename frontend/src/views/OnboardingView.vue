<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  bootstrapFirstDepartment,
  createDepartmentJoinRequest,
  fetchDepartmentTree,
  fetchMyDepartmentJoinRequests,
} from '@/api/modules/organization'
import type { DepartmentJoinRequestItem, DepartmentNode } from '@/types/organization'
import { getPrimaryMembership } from '@/utils/organization'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const submitting = ref(false)
const departments = ref<DepartmentNode[]>([])
const myRequests = ref<DepartmentJoinRequestItem[]>([])

const bootstrapForm = reactive({
  code: 'dept-root',
  name: '企业知识中心',
  full_name: '企业知识中心',
})

const joinForm = reactive({
  target_department_id: undefined as number | undefined,
  reason: '',
})

const memberships = computed(() => authStore.user?.memberships ?? [])
const hasDepartments = computed(() => departments.value.length > 0)
const hasMemberships = computed(() => memberships.value.length > 0)
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
    ElMessage.error('读取组织接入信息失败，请确认后端服务状态。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleBootstrap() {
  submitting.value = true
  try {
    await bootstrapFirstDepartment(bootstrapForm)
    ElMessage.success('首个部门创建完成。')
    await loadData()
  } catch (error) {
    ElMessage.error('初始化首个部门失败，请检查部门编码是否重复。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function handleJoinRequest() {
  if (!joinForm.target_department_id) {
    ElMessage.warning('请先选择要加入的部门。')
    return
  }

  if (!joinForm.reason.trim()) {
    ElMessage.warning('请补充申请说明。')
    return
  }

  submitting.value = true
  try {
    await createDepartmentJoinRequest({
      target_department_id: joinForm.target_department_id,
      requested_role_code: 'department_member',
      reason: joinForm.reason.trim(),
    })
    ElMessage.success('加入申请已提交。')
    joinForm.reason = ''
    await loadData()
  } catch (error) {
    ElMessage.error('提交申请失败，请确认是否已经有一条待审批记录。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

function goToWorkspace() {
  void router.push('/workspace')
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>组织接入</h2>
        <span>{{ hasMemberships ? '已完成接入' : '待完成接入' }}</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button v-if="hasMemberships" type="primary" @click="goToWorkspace">
          进入工作台
        </el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">组织状态</span>
        <strong class="summary-card__value">{{ hasMemberships ? '已加入' : '待归属' }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">可选部门</span>
        <strong class="summary-card__value">{{ departments.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">我的申请</span>
        <strong class="summary-card__value">{{ myRequests.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">主归属</span>
        <strong class="summary-card__value">{{ primaryMembership?.department_name || '--' }}</strong>
      </el-card>
    </section>

    <section v-if="hasMemberships" class="split-grid">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>当前归属</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="memberships" stripe>
          <el-table-column prop="department_name" label="部门" min-width="180" />
          <el-table-column label="关系" min-width="120">
            <template #default="{ row }">
              {{ row.is_primary ? '主归属部门' : '协作部门' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>我的申请记录</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="myRequests" stripe empty-text="还没有提交过申请">
          <el-table-column prop="target_department_name" label="目标部门" min-width="160" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="reason" label="申请说明" min-width="220" show-overflow-tooltip />
          <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>
    </section>

    <section v-else-if="!hasDepartments" class="split-grid">
      <el-card class="form-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>初始化首个部门</strong>
          </div>
        </template>
        <el-form label-position="top">
          <el-form-item label="部门编码">
            <el-input v-model="bootstrapForm.code" />
          </el-form-item>
          <el-form-item label="部门名称">
            <el-input v-model="bootstrapForm.name" />
          </el-form-item>
          <el-form-item label="部门全称">
            <el-input v-model="bootstrapForm.full_name" />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleBootstrap">
            创建首个部门
          </el-button>
        </el-form>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>当前状态</strong>
          </div>
        </template>
        <div class="compact-stack">
          <div class="compact-row">
            <span>系统部门数</span>
            <strong>0</strong>
          </div>
          <div class="compact-row">
            <span>下一步</span>
            <strong>创建首个部门</strong>
          </div>
        </div>
      </el-card>
    </section>

    <section v-else class="split-grid">
      <el-card class="form-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>申请加入部门</strong>
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
              placeholder="请选择部门"
            />
          </el-form-item>
          <el-form-item label="申请说明">
            <el-input
              v-model="joinForm.reason"
              type="textarea"
              :rows="4"
              placeholder="说明你的工作职责"
            />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleJoinRequest">
            提交申请
          </el-button>
        </el-form>
      </el-card>

      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>我的申请记录</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="myRequests" stripe empty-text="还没有提交过申请">
          <el-table-column prop="target_department_name" label="目标部门" min-width="160" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="reason" label="申请说明" min-width="220" show-overflow-tooltip />
          <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>
    </section>
  </div>
</template>
