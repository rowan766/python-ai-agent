<script setup lang="ts">
import { ArrowRight, Finished, Link, SwitchButton } from '@element-plus/icons-vue'
import { buildApiUrl } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPreferredMembership } from '@/utils/organization'
import { setActiveDepartmentId } from '@/utils/storage'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const breadcrumbs = computed(() =>
  route.matched
    .map((record) => record.meta?.title)
    .filter((title): title is string => typeof title === 'string' && title.length > 0),
)
const memberships = computed(() => authStore.user?.memberships ?? [])
const selectedDepartmentId = ref<number | undefined>(undefined)
const currentMembership = computed(
  () =>
    memberships.value.find((item) => item.department_id === selectedDepartmentId.value)
    ?? getPreferredMembership(memberships.value),
)

watch(
  memberships,
  (items) => {
    selectedDepartmentId.value = getPreferredMembership(items)?.department_id
  },
  { immediate: true },
)

watch(selectedDepartmentId, (value) => {
  setActiveDepartmentId(value ?? null)
})

function openDocs() {
  window.open(buildApiUrl('/docs'), '_blank', 'noopener,noreferrer')
}

function goToOnboarding() {
  void router.push('/onboarding')
}

function logout() {
  authStore.logout()
  void router.push('/login')
}
</script>

<template>
  <header class="app-header">
    <div>
      <el-breadcrumb :separator-icon="ArrowRight">
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item">
          {{ item }}
        </el-breadcrumb-item>
      </el-breadcrumb>
      <div class="app-header__headline">
        {{ breadcrumbs.at(-1) || '知识平台' }}
      </div>
    </div>

    <div class="app-header__actions">
      <el-tag :type="authStore.organizationReady ? 'success' : 'warning'" effect="plain" round>
        <el-icon><Finished /></el-icon>
        <span>{{ authStore.organizationReady ? '组织已接入' : '组织待接入' }}</span>
      </el-tag>

      <el-select
        v-if="authStore.organizationReady && memberships.length > 1"
        v-model="selectedDepartmentId"
        class="app-header__department"
        placeholder="当前工作部门"
      >
        <el-option
          v-for="membership in memberships"
          :key="membership.department_id"
          :label="membership.department_name"
          :value="membership.department_id"
        />
      </el-select>

      <div v-else-if="currentMembership" class="app-header__department-pill">
        当前部门：{{ currentMembership.department_name }}
      </div>

      <el-button v-if="!authStore.organizationReady" type="primary" plain @click="goToOnboarding">
        完成组织接入
      </el-button>

      <el-button text @click="openDocs">
        <el-icon><Link /></el-icon>
        <span>接口文档</span>
      </el-button>

      <el-dropdown>
        <div class="app-header__profile">
          <div class="app-header__avatar">{{ authStore.displayName.slice(0, 1).toUpperCase() }}</div>
          <div>
            <div class="app-header__name">{{ authStore.displayName }}</div>
            <div class="app-header__email">{{ authStore.user?.email }}</div>
          </div>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/organization')">
              组织中心
            </el-dropdown-item>
            <el-dropdown-item divided @click="logout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.app-header__headline {
  margin-top: 10px;
  font-size: 22px;
  font-weight: 600;
  color: #111827;
}

.app-header__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.app-header__department {
  width: 220px;
}

.app-header__department-pill {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  padding: 8px 12px;
  background: #ffffff;
  color: #4b5563;
  font-size: 13px;
}

.app-header__profile {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.app-header__avatar {
  display: grid;
  height: 38px;
  width: 38px;
  place-items: center;
  border-radius: 10px;
  background: #409eff;
  color: #fff;
  font-weight: 700;
}

.app-header__name {
  font-weight: 600;
  color: #111827;
}

.app-header__email {
  color: #6b7280;
  font-size: 12px;
}

@media (max-width: 900px) {
  .app-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .app-header__actions {
    flex-wrap: wrap;
  }
}
</style>
