<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  bootstrapFirstDepartment,
  createDepartmentJoinRequest,
  fetchDepartmentTree,
  fetchMyDepartmentJoinRequests,
} from '@/api/modules/organization'
import type { DepartmentJoinRequestItem, DepartmentNode } from '@/types/organization'

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
  requested_role_code: 'department_member',
  reason: '',
})

const hasDepartments = computed(() => departments.value.length > 0)
const hasMemberships = computed(() => (authStore.user?.memberships?.length ?? 0) > 0)

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
    ElMessage.error('读取组织信息失败，请确认后端服务状态。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleBootstrap() {
  submitting.value = true
  try {
    await bootstrapFirstDepartment(bootstrapForm)
    ElMessage.success('首个部门初始化成功，你已成为默认负责人。')
    await loadData()
  } catch (error) {
    ElMessage.error('初始化首个部门失败，请检查编码是否重复。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function handleJoinRequest() {
  if (!joinForm.target_department_id) {
    ElMessage.warning('请先选择目标部门。')
    return
  }

  if (!joinForm.reason.trim()) {
    ElMessage.warning('请填写申请理由。')
    return
  }

  submitting.value = true
  try {
    await createDepartmentJoinRequest({
      target_department_id: joinForm.target_department_id,
      requested_role_code: joinForm.requested_role_code,
      reason: joinForm.reason.trim(),
    })
    ElMessage.success('加入部门申请已提交。')
    joinForm.reason = ''
    await loadData()
  } catch (error) {
    ElMessage.error('申请提交失败，请确认是否已有待审批记录。')
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
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">Organization & RBAC</p>
        <h2>组织接入页已经切到真实流程，后续继续扩展审批和范围权限。</h2>
        <p class="page-copy">
          这一版已经接通部门树、首个部门初始化、加入部门申请和我的申请记录。后续会继续补负责人审批、成员关系范围角色和知识空间授权。
        </p>
      </div>

      <el-tag :type="hasMemberships ? 'success' : 'warning'" effect="dark" round>
        {{ hasMemberships ? '组织已接入' : '待加入组织' }}
      </el-tag>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>当前组织状态</template>
        <el-skeleton :loading="loading" animated :rows="5">
          <template #default>
            <div v-if="hasMemberships" class="roadmap-boxes">
              <div
                v-for="membership in authStore.user?.memberships || []"
                :key="membership.id"
                class="roadmap-box"
              >
                <strong>{{ membership.department_name }}</strong>
                <span>
                  {{ membership.membership_type }} / {{ membership.is_primary ? '主部门' : '协作部门' }}
                </span>
              </div>
            </div>
            <el-empty
              v-else
              description="你还没有部门归属。可以先创建首个根部门，或向已有部门发起加入申请。"
            />
          </template>
        </el-skeleton>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>我的申请记录</template>
        <el-table :data="myRequests" empty-text="还没有提交过申请" style="width: 100%">
          <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
          <el-table-column prop="requested_role_code" label="申请角色" min-width="140" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="review_comment" label="审批意见" min-width="180" />
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
        <template #header>为什么要有这个入口</template>
        <div class="roadmap-box">
          <strong>企业级系统必须能自举</strong>
          <span>
            在还没有组织树时，系统需要一个干净的初始化入口，用于创建首个根部门并建立首位负责人，之后再逐步扩展成员、审批和知识空间。
          </span>
        </div>
      </el-card>
    </section>

    <section v-else class="grid-two">
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
              placeholder="请选择要加入的部门"
            />
          </el-form-item>
          <el-form-item label="申请角色">
            <el-select v-model="joinForm.requested_role_code" placeholder="请选择申请角色">
              <el-option label="部门成员" value="department_member" />
              <el-option label="知识上传者" value="knowledge_operator" />
              <el-option label="知识审核者" value="knowledge_reviewer" />
            </el-select>
          </el-form-item>
          <el-form-item label="申请理由">
            <el-input
              v-model="joinForm.reason"
              type="textarea"
              :rows="4"
              placeholder="请输入申请原因和计划承担的职责"
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
