<script setup lang="ts">
import {
  CollectionTag,
  Connection,
  Document,
  Files,
  HomeFilled,
  OfficeBuilding,
  UploadFilled,
} from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface MenuItem {
  label: string
  path: string
  icon: unknown
  caption: string
}

const route = useRoute()
const router = useRouter()

const menuItems: MenuItem[] = [
  { label: '工作台', path: '/workspace', icon: HomeFilled, caption: '系统概览与快捷入口' },
  { label: '组织接入', path: '/onboarding', icon: Connection, caption: '组织归属、申请与审批' },
  { label: '部门治理', path: '/departments', icon: OfficeBuilding, caption: '创建部门并维护组织树' },
  { label: '知识库空间', path: '/knowledge-bases', icon: CollectionTag, caption: '部门归属的真实空间清单' },
  { label: '文档中心', path: '/documents', icon: Files, caption: '文档归属、切片与治理状态' },
  { label: '上传文档', path: '/documents/upload', icon: UploadFilled, caption: '按知识库空间归属上传' },
  { label: '智能检索', path: '/rag/search', icon: Document, caption: '按权限范围检索知识内容' },
]

const activePath = computed(() => String(route.meta.navKey ?? route.path))

function handleSelect(path: string) {
  void router.push(path)
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__brand">
      <div class="sidebar__mark">ER</div>
      <div>
        <div class="sidebar__title">Enterprise RAG</div>
        <div class="sidebar__subtitle">Vue + FastAPI Phase 1</div>
      </div>
    </div>

    <el-menu
      :default-active="activePath"
      class="sidebar__menu"
      @select="handleSelect"
    >
      <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <div class="sidebar__menu-copy">
          <span>{{ item.label }}</span>
          <small>{{ item.caption }}</small>
        </div>
      </el-menu-item>
    </el-menu>

    <div class="sidebar__footer">
      <span>当前阶段</span>
      <strong>组织接入 + 知识归属主链</strong>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  height: 100%;
  flex-direction: column;
  gap: 18px;
  padding: 24px 18px 20px;
  background:
    linear-gradient(180deg, rgba(18, 90, 72, 0.94), rgba(14, 41, 36, 0.98)),
    radial-gradient(circle at top, rgba(241, 198, 111, 0.22), transparent 35%);
  color: #f7f2e8;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sidebar__mark {
  display: grid;
  height: 46px;
  width: 46px;
  place-items: center;
  border-radius: 15px;
  background: rgba(245, 224, 188, 0.18);
  color: #f9e8b9;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.sidebar__title {
  font-size: 18px;
  font-weight: 700;
}

.sidebar__subtitle {
  margin-top: 4px;
  color: rgba(247, 242, 232, 0.72);
  font-size: 12px;
}

.sidebar__menu {
  border-right: 0;
  background: transparent;
}

:deep(.sidebar__menu .el-menu-item) {
  height: auto;
  min-height: 58px;
  margin-bottom: 8px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(247, 242, 232, 0.92);
  line-height: 1.3;
  padding-top: 10px;
  padding-bottom: 10px;
}

:deep(.sidebar__menu .el-menu-item.is-active) {
  background: rgba(246, 232, 201, 0.16);
  color: #fff9ec;
}

:deep(.sidebar__menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.1);
}

.sidebar__menu-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar__menu-copy small {
  color: rgba(247, 242, 232, 0.68);
  font-size: 11px;
}

.sidebar__footer {
  margin-top: auto;
  border: 1px solid rgba(255, 248, 229, 0.12);
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
}

.sidebar__footer span {
  display: block;
  margin-bottom: 6px;
  color: rgba(247, 242, 232, 0.68);
  font-size: 12px;
}

.sidebar__footer strong {
  font-size: 14px;
  font-weight: 600;
}
</style>
