<script setup>
import { ref } from 'vue'
import { runAudit } from './api.js'
import AuditReport from './components/AuditReport.vue'

const url = ref('https://infotrust.com/')
const loading = ref(false)
const error = ref('')
const report = ref(null)

async function submit() {
  error.value = ''
  report.value = null
  loading.value = true

  try {
    let target = url.value.trim()
    if (!/^https?:\/\//i.test(target)) {
      target = 'https://' + target
    }
    report.value = await runAudit(target)
    url.value = target
  } catch (e) {
    error.value = e.message || 'Audit failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <header>
    <h1>Web Privacy Auditor</h1>
    <p class="subtitle">
      Scan a URL for third-party tags, trackers, and cookies — forensic-style privacy report.
    </p>
  </header>

  <section class="card">
    <h2>Audit a URL</h2>
    <form class="form-row" @submit.prevent="submit">
      <input
        v-model="url"
        type="url"
        placeholder="https://infotrust.com"
        required
        :disabled="loading"
      />
      <button type="submit" :disabled="loading">
        {{ loading ? 'Scanning…' : 'Run audit' }}
      </button>
    </form>

    <p v-if="loading" class="loading">
      Scanning in headless browser (may take up to 60 seconds)…
    </p>
    <p v-if="error" class="error-box">{{ error }}</p>
  </section>

  <AuditReport v-if="report" :report="report" />
</template>
