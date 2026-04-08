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
    ElMessage.success('首个部门已经创建完成，你现在是企业知识中心负责人。')
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
    ElMessage.warning('请补充你加入该部门后的职责说明。')
    return
  }

  submitting.value = true
  try {
    await createDepartmentJoinRequest({
      target_department_id: joinForm.target_department_id,
      requested_role_code: 'department_member',
      reason: joinForm.reason.trim(),
    })
    ElMessage.success('加入申请已提交，负责人审批后你就能进入正式工作台。')
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
    <section class="hero-card onboarding-hero">
      <div>
        <p class="page-eyebrow">Onboarding</p>
        <h2>先完成组织接入，再进入知识空间、上传和审批工作流。</h2>
        <p class="page-copy">
          你现在只需要完成一件事：明确自己属于哪个部门。系统会根据部门归属自动决定你可见的知识空间、文档范围和审批职责。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ hasMemberships ? '已接入' : '待接入' }}</span>
        <small>
          {{ hasMemberships ? `当前主归属：${primaryMembership?.department_name || '-'}` : '完成部门归属后继续' }}
        </small>
        <el-button v-if="hasMemberships" type="primary" @click="goToWorkspace">
          进入工作台
        </el-button>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">组织状态</span>
        <strong>{{ hasMemberships ? '已加入组织' : '等待归属' }}</strong>
        <p>决定你是否能进入正式知识流程。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可选部门</span>
        <strong>{{ departments.length }}</strong>
        <p>系统里当前已经建立的部门数量。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">我的申请</span>
        <strong>{{ myRequests.length }}</strong>
        <p>这里会持续显示你发起过的接入申请。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">下一步</span>
        <strong>{{ hasMemberships ? '开始使用' : hasDepartments ? '提交申请' : '初始化组织' }}</strong>
        <p>流程只保留当前最重要的一步。</p>
      </el-card>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>当前状态</template>
        <el-skeleton :loading="loading" animated :rows="5">
          <template #default>
            <div v-if="hasMemberships" class="roadmap-boxes">
              <div
                v-for="membership in memberships"
                :key="membership.id"
                class="roadmap-box"
              >
                <strong>{{ membership.department_name }}</strong>
                <span>
                  {{ membership.is_primary ? '主归属部门' : '协作部门' }} · 完成接入后可进入知识空间和文档流程
                </span>
              </div>
            </div>
            <div v-else class="roadmap-boxes">
              <div class="roadmap-box">
                <strong>现在先完成部门归属</strong>
                <span>系统不会要求你先理解共享、审批、知识空间等概念，只要先确定组织归属即可。</span>
              </div>
              <div class="roadmap-box">
                <strong>通过后自动开启可见范围</strong>
                <span>知识空间、文档和权限内检索会根据归属部门自动开放。</span>
              </div>
            </div>
          </template>
        </el-skeleton>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>我的申请记录</template>
        <el-table :data="myRequests" empty-text="还没有提交过申请" style="width: 100%">
          <el-table-column prop="target_department_name" label="目标部门" min-width="160" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="reason" label="职责说明" min-width="220" show-overflow-tooltip />
          <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>
    </section>

    <section v-if="!hasDepartments" class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>初始化首个部门</template>
        <el-form label-position="top">
          <el-form-item label="部门编码">
            <el-input v-model="bootstrapForm.code" placeholder="例如 dept-root" />
          </el-form-item>
          <el-form-item label="部门名称">
            <el-input v-model="bootstrapForm.name" placeholder="例如 企业知识中心" />
          </el-form-item>
          <el-form-item label="部门全称">
            <el-input v-model="bootstrapForm.full_name" placeholder="例如 企业知识中心" />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleBootstrap">
            创建首个部门并设我为负责人
          </el-button>
        </el-form>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>为什么先做这一步</template>
        <div class="roadmap-box">
          <strong>企业系统必须先有组织边界</strong>
          <span>
            当系统还没有任何部门时，需要一个干净的初始化入口来建立根部门和第一位负责人，后面的知识空间、共享和审批才能挂上去。
          </span>
        </div>
      </el-card>
    </section>

    <section v-else-if="!hasMemberships" class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>申请加入部门</template>
        <el-form label-position="top">
          <el-form-item label="目标部门">
            <el-tree-select
              v-model="joinForm.target_department_id"
              :data="departments"
              node-key="id"
              check-strictly
              default-expand-all
              :props="{ label: 'name', children: 'children', value: 'id' }"
              placeholder="请选择你将要加入的部门"
            />
          </el-form-item>
          <el-form-item label="你会承担什么工作">
            <el-input
              v-model="joinForm.reason"
              type="textarea"
              :rows="4"
              placeholder="例如：负责整理经营周报、维护产品知识空间和需求复盘资料"
            />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleJoinRequest">
            提交加入申请
          </el-button>
        </el-form>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>当前部门树</template>
        <el-tree
          :data="departments"
          node-key="id"
          default-expand-all
          :props="{ label: 'name', children: 'children' }"
          empty-text="暂无部门"
        />
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.onboarding-hero {
  align-items: center;
}
</style>
