<template>
  <div class="skeleton-wrap">
    <!-- Card skeleton -->
    <div v-if="type === 'card'" class="sk-card" :style="{ width, height }">
      <div class="sk-shimmer" :style="{ borderRadius }"></div>
    </div>

    <!-- List row skeleton -->
    <div v-else-if="type === 'row'" class="sk-row">
      <div class="sk-shimmer sk-row-dot"></div>
      <div class="sk-row-body">
        <div class="sk-shimmer sk-row-line" style="width:65%"></div>
        <div class="sk-shimmer sk-row-line" style="width:40%;height:8px"></div>
      </div>
      <div class="sk-shimmer sk-row-tag"></div>
    </div>

    <!-- Stats card skeleton -->
    <div v-else-if="type === 'stat'" class="sk-stat">
      <div class="sk-shimmer sk-stat-icon"></div>
      <div class="sk-stat-body">
        <div class="sk-shimmer" style="width:40%;height:22px"></div>
        <div class="sk-shimmer" style="width:60%;height:10px;margin-top:6px"></div>
      </div>
    </div>

    <!-- Full list skeleton -->
    <div v-else-if="type === 'list'" class="sk-list">
      <div v-for="i in count" :key="i" class="sk-row">
        <div class="sk-shimmer" style="width:36px;height:36px;border-radius:8px;flex-shrink:0"></div>
        <div class="sk-row-body">
          <div class="sk-shimmer sk-row-line" style="width:55%"></div>
          <div class="sk-shimmer sk-row-line" style="width:80%;height:8px"></div>
        </div>
      </div>
    </div>

    <!-- Timeline event skeleton -->
    <div v-else-if="type === 'timeline'" class="sk-list">
      <div v-for="i in count" :key="i" class="sk-row" style="padding-left:20px">
        <div class="sk-shimmer" style="width:10px;height:10px;border-radius:50%;flex-shrink:0;position:absolute;left:0;top:14px"></div>
        <div class="sk-row-body">
          <div class="sk-shimmer sk-row-line" style="width:45%"></div>
          <div class="sk-shimmer sk-row-line" style="width:70%;height:8px"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'card' | 'row' | 'stat' | 'list' | 'timeline'
  count?: number
  width?: string
  height?: string
  borderRadius?: string
}>(), {
  type: 'row',
  count: 5,
  width: '100%',
  height: '100px',
  borderRadius: 'var(--radius-md)',
})
</script>

<style scoped>
.skeleton-wrap { width: 100%; }

/* ── Shimmer animation ── */
.sk-shimmer {
  background: linear-gradient(90deg,
    var(--el-fill-color) 25%,
    var(--el-fill-color-light) 50%,
    var(--el-fill-color) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Card ── */
.sk-card { padding: 0; }

/* ── Row ── */
.sk-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  position: relative;
}

.sk-row-dot {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 8px;
}

.sk-row-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sk-row-line {
  height: 12px;
  border-radius: 4px;
}

.sk-row-tag {
  width: 50px;
  height: 22px;
  border-radius: 12px;
  flex-shrink: 0;
}

/* ── Stat ── */
.sk-stat {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  border-radius: var(--radius-lg);
  background: var(--legal-bg-card);
}

.sk-stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.sk-stat-body {
  flex: 1;
}

/* ── List ── */
.sk-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
