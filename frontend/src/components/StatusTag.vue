<template>
  <el-tag :type="tag" effect="light" round size="small">{{ text }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
import {
  APPEAL_STATUS_TAG,
  APPEAL_STATUS_TEXT,
  DECISION_TAG,
  DECISION_TEXT,
  OFFER_STATUS_TAG,
  OFFER_STATUS_TEXT,
  OFFER_TYPE_TEXT,
  PUBLICATION_STATUS_TAG,
  PUBLICATION_STATUS_TEXT,
  ROUND_KIND_TEXT,
  STAGE_TAG,
  STAGE_TEXT,
} from '../utils/format'

const props = defineProps({
  kind: { type: String, required: true },
  value: { type: String, default: '' },
})

const dictionary = {
  stage: [STAGE_TEXT, STAGE_TAG],
  offerStatus: [OFFER_STATUS_TEXT, OFFER_STATUS_TAG],
  offerType: [OFFER_TYPE_TEXT, {}],
  decision: [DECISION_TEXT, DECISION_TAG],
  roundKind: [ROUND_KIND_TEXT, {}],
  appeal: [APPEAL_STATUS_TEXT, APPEAL_STATUS_TAG],
  publication: [PUBLICATION_STATUS_TEXT, PUBLICATION_STATUS_TAG],
}

const current = computed(() => dictionary[props.kind] || [{}, {}])
const text = computed(() => current.value[0][props.value] || props.value || '—')
const tag = computed(() => current.value[1][props.value] || 'primary')
</script>
