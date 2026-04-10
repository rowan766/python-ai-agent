<template>
  <el-button
    :icon="icon"
    :disabled="disabled"
    :loading="loading"
    :type="resolvedType"
    :size="sizeVariant === 'table' ? 'small' : undefined"
    :class="buttonClasses"
    :native-type="nativeType"
    @click="$emit('click', $event)"
  >
    <slot />
  </el-button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: {
    type: [Object, Function],
    default: null
  },
  tone: {
    type: String,
    default: 'blue'
  },
  styleType: {
    type: String,
    default: 'soft'
  },
  sizeVariant: {
    type: String,
    default: 'default'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  nativeType: {
    type: String,
    default: 'button'
  },
  type: {
    type: String,
    default: ''
  }
})

defineEmits(['click'])

const toneMap = {
  blue: 'primary',
  green: 'success',
  red: 'danger',
  gray: 'info',
  amber: 'warning'
}

const resolvedType = computed(() => {
  if (props.type) {
    return props.type
  }

  if (props.styleType === 'primary') {
    return toneMap[props.tone] || 'primary'
  }

  return undefined
})

const buttonClasses = computed(() => [
  'crud-button',
  `crud-button--${props.styleType}`,
  `crud-button--${props.tone}`,
  `crud-button--${props.sizeVariant}`
])
</script>

<style scoped>
.crud-button {
  border-radius: 4px;
  font-weight: 600;
  transition: all 0.18s ease;
}

.crud-button--default {
  min-height: 32px;
  padding: 7px 12px;
}

.crud-button--table {
  min-height: 28px;
  padding: 5px 10px;
}

.crud-button--secondary {
  border-color: #dbe3ec;
  background: #ffffff;
  color: #6b7b91;
}

.crud-button--secondary:hover:not(.is-disabled),
.crud-button--secondary:focus-visible {
  border-color: #c8d4e1;
  background: #f7f9fc;
  color: #52687f;
}

.crud-button--soft {
  border: 1px solid transparent;
}

.crud-button--soft.crud-button--blue {
  background: #e8f3ff;
  border-color: #cfe4ff;
  color: #2f7ef7;
}

.crud-button--soft.crud-button--blue:hover:not(.is-disabled),
.crud-button--soft.crud-button--blue:focus-visible {
  background: #d7eaff;
  border-color: #b9d8ff;
}

.crud-button--soft.crud-button--green {
  background: #edf9ee;
  border-color: #d2f2d6;
  color: #43a047;
}

.crud-button--soft.crud-button--green:hover:not(.is-disabled),
.crud-button--soft.crud-button--green:focus-visible {
  background: #dcf3df;
  border-color: #bfe6c5;
}

.crud-button--soft.crud-button--red {
  background: #fff1f0;
  border-color: #ffd9d6;
  color: #e85d57;
}

.crud-button--soft.crud-button--red:hover:not(.is-disabled),
.crud-button--soft.crud-button--red:focus-visible {
  background: #ffe3e0;
  border-color: #ffc5bf;
}

.crud-button--soft.crud-button--gray {
  background: #f6f8fb;
  border-color: #e5eaf1;
  color: #6b7b91;
}

.crud-button--soft.crud-button--gray:hover:not(.is-disabled),
.crud-button--soft.crud-button--gray:focus-visible {
  background: #edf2f7;
  border-color: #d6dee8;
}

.crud-button--soft.crud-button--amber {
  background: #fff7e8;
  border-color: #ffe2ae;
  color: #d9822b;
}

.crud-button--soft.crud-button--amber:hover:not(.is-disabled),
.crud-button--soft.crud-button--amber:focus-visible {
  background: #ffefcf;
  border-color: #ffd48b;
}
</style>
