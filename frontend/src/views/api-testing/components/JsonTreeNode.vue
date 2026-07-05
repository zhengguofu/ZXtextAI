<template>
  <div class="json-tree-node" :style="{ paddingLeft: level * 16 + 'px' }">
    <!-- 可折叠的键 -->
    <div
      v-if="isObjectOrArray"
      class="json-tree-key-row"
      @click="collapsed = !collapsed"
    >
      <span class="json-tree-toggle">{{ collapsed ? '▶' : '▼' }}</span>
      <span class="json-tree-key">{{ keyName }}</span>
      <span class="json-tree-type">{{ typeLabel }}</span>
    </div>

    <!-- 基本类型值 -->
    <div v-else class="json-tree-value-row">
      <span class="json-tree-key">{{ keyName }}: </span>
      <span :class="['json-tree-value', getValueType]">{{ formattedValue }}</span>
    </div>

    <!-- 展开的子节点 -->
    <template v-if="!collapsed && isObjectOrArray">
      <JsonTreeNode
        v-for="(childValue, childKey) in data"
        :key="childKey"
        :data="childValue"
        :key-name="childKeyName(childKey)"
        :level="level + 1"
        :expand-all="expandAll"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  data: { type: [Object, Array, String, Number, Boolean, null], default: null },
  keyName: { type: String, default: '' },
  level: { type: Number, default: 0 },
  expandAll: { type: Boolean, default: false },
})

const collapsed = ref(props.level > 2)

watch(() => props.expandAll, (val) => {
  collapsed.value = !val
})

const isObjectOrArray = computed(() => {
  return props.data !== null && typeof props.data === 'object'
})

const isArray = computed(() => {
  return Array.isArray(props.data)
})

const getLength = computed(() => {
  if (props.data === null || props.data === undefined) return 0
  if (Array.isArray(props.data)) return props.data.length
  return Object.keys(props.data).length
})

const typeLabel = computed(() => {
  return isArray.value ? '[' + getLength.value + ']' : '{' + getLength.value + '}'
})

function childKeyName(childKey) {
  return isArray.value ? '[' + childKey + ']' : String(childKey)
}

const getValueType = computed(() => {
  if (props.data === null || props.data === undefined) return 'json-null'
  const t = typeof props.data
  if (t === 'string') return 'json-string'
  if (t === 'number') return 'json-number'
  if (t === 'boolean') return 'json-boolean'
  return 'json-string'
})

const formattedValue = computed(() => {
  if (props.data === null || props.data === undefined) return 'null'
  if (typeof props.data === 'string') return `"${props.data}"`
  return String(props.data)
})
</script>

<style scoped>
.json-tree-node {
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.7;
}

.json-tree-key-row {
  cursor: pointer;
  user-select: none;
  padding: 2px 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.json-tree-key-row:hover {
  background: rgba(37, 99, 235, 0.04);
}

.json-tree-toggle {
  font-size: 10px;
  width: 16px;
  text-align: center;
  color: #64748b;
  flex-shrink: 0;
}

.json-tree-key {
  color: #9333ea;
  font-weight: 600;
}

.json-tree-type {
  color: #94a3b8;
  font-weight: 400;
  margin-left: 4px;
}

.json-tree-value-row {
  padding: 2px 0;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.json-tree-value {
  font-weight: 500;
}

.json-string { color: #16a34a; }
.json-number { color: #2563eb; }
.json-boolean { color: #d97706; }
.json-null { color: #94a3b8; font-style: italic; }
</style>
