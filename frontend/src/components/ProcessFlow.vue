<template>
  <div class="flow">
    <article
      v-for="step in steps"
      :key="step.no"
      class="flow__card"
      :class="{ 'flow__card--hot': step.hot }"
    >
      <div class="flow__top">
        <span class="flow__num" :class="`flow__num--${step.tone}`">{{ step.no }}</span>
        <span v-if="step.hot" class="pill pill--orange">重点环节</span>
      </div>
      <h3>{{ step.title }}</h3>
      <p>{{ step.desc }}</p>
      <div class="flow__time">
        <span class="time-badge" :class="{ 'time-badge--orange': step.hot }">{{ step.time }}</span>
      </div>
    </article>
  </div>
</template>

<script setup>
const steps = [
  {
    no: 1,
    title: '集中宣讲',
    desc: '学院组织统一宣讲，由各实训室介绍项目方向、招录名额、培养安排与考核要求。',
    time: '10月29日 14:00',
    tone: 'green',
  },
  {
    no: 2,
    title: '实训室开放日',
    desc: '学生实地走访实训室，与导师、高年级学生交流，了解项目氛围和培养方式。',
    time: '10月29日—10月30日',
    tone: 'orange',
  },
  {
    no: 3,
    title: '意向填报',
    desc: '最多填报 3 个平行导师意向，不分志愿先后；同时选择是否服从实训室内部调剂和全院跨实训室调剂。',
    time: '11月2日 08:00–12:00',
    tone: 'green',
  },
  {
    no: 4,
    title: '导师初选与面试考核',
    desc: '以实训室为单位统一组织面试，所有报名学生均参加；考察学习态度、逻辑思维、编程基础和时间投入，确定拟录取、递补和内部调剂候选名单。',
    time: '11月2日 12:00—11月3日 17:00',
    tone: 'blue',
    hot: true,
  },
  {
    no: 5,
    title: '拟录取与学生确认',
    desc: '仅收到 1 个拟录取意向的自动确认；收到 2 个及以上意向的，须在规定时间内自主选择唯一去向，逾期视为放弃。',
    time: '11月4日 08:00–12:00',
    tone: 'orange',
  },
  {
    no: 6,
    title: '分轮补录',
    desc: '公布剩余名额，未录取学生重新填报；实训室统一组织面试、双向确认与顺位递补，依次完成第二轮和第三轮补录。',
    time: '11月4日 12:00—11月5日 17:00',
    tone: 'green',
  },
  {
    no: 7,
    title: '统筹调剂录取',
    desc: '剩余名额进入全院调剂池：第一优先级为实训室内部调剂，第二优先级为全院跨实训室调剂，第三优先级为约谈未服从调剂学生并最终统筹安置。',
    time: '11月6日 08:00–12:00',
    tone: 'green',
  },
  {
    no: 8,
    title: '结果公示与正式入组',
    desc: '学院汇总最终录取名单并公示 1 天；公示无异议后，学生正式加入实训室开展 AI+PBL 项目实训。',
    time: '公示 1 天',
    tone: 'navy',
  },
]
</script>

<style scoped>
.flow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.flow__card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 196px;
  padding: 18px;
  border: 1px solid var(--tls-line);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 10px 26px rgba(23, 50, 77, 0.05);
}

.flow__card--hot {
  border-color: #f3c8a9;
  box-shadow: 0 14px 30px rgba(232, 119, 46, 0.14);
  background: linear-gradient(180deg, #fffdfb 0%, #fff8f2 100%);
}

.flow__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.flow__num {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: #fff;
  font-size: 15px;
  font-weight: 800;
}

.flow__num--green {
  background: var(--tls-green);
}

.flow__num--orange {
  background: var(--tls-accent);
}

.flow__num--blue {
  background: var(--tls-primary);
}

.flow__num--navy {
  background: var(--tls-ink);
}

.flow__card h3 {
  font-size: 15px;
  line-height: 1.4;
}

.flow__card p {
  flex: 1;
  color: var(--tls-muted);
  font-size: 12.5px;
  line-height: 1.7;
}

.flow__time {
  display: flex;
}

@media (max-width: 1100px) {
  .flow {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .flow {
    grid-template-columns: 1fr;
  }

  .flow__card {
    min-height: auto;
  }
}
</style>
