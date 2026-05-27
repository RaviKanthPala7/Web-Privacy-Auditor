<script setup>
import { ref } from 'vue'

const props = defineProps({
  report: { type: Object, required: true },
})

const tab = ref('trackers')

function slugFromUrl(url) {
  try {
    return new URL(url).hostname.replace(/\./g, '-')
  } catch {
    return 'site'
  }
}

function downloadJson() {
  const json = JSON.stringify(props.report, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const link = document.createElement('a')
  const slug = slugFromUrl(props.report.url)
  const date = props.report.scanned_at?.slice(0, 10) || 'report'
  link.href = URL.createObjectURL(blob)
  link.download = `privacy-audit-${slug}-${date}.json`
  link.click()
  URL.revokeObjectURL(link.href)
}

function badgeClass(category) {
  const map = {
    Analytics: 'badge-analytics',
    Advertising: 'badge-advertising',
    Social: 'badge-social',
    CDN: 'badge-cdn',
    Unknown: 'badge-unknown',
  }
  return 'badge ' + (map[category] || 'badge-unknown')
}
</script>

<template>
  <section class="card">
    <div class="report-header">
      <h2>Results</h2>
      <button type="button" class="btn-secondary" @click="downloadJson">
        Download JSON
      </button>
    </div>
    <p class="meta">
      <strong>{{ report.page_title || 'Untitled' }}</strong><br />
      <code>{{ report.url }}</code><br />
      {{ report.duration_ms }} ms
    </p>

    <div v-if="report.summary?.length" class="summary-grid">
      <div v-for="s in report.summary" :key="s.category" class="summary-chip">
        <div class="count">{{ s.count }}</div>
        <div class="label">{{ s.category }}</div>
      </div>
    </div>
  </section>

  <section v-if="report.notes?.length" class="card">
    <h2>Privacy notes</h2>
    <ul class="notes">
      <li v-for="(note, i) in report.notes" :key="i">{{ note }}</li>
    </ul>
  </section>

  <section class="card">
    <div class="tabs">
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'trackers' }"
        @click="tab = 'trackers'"
      >
        Trackers ({{ report.trackers?.length || 0 }})
      </button>
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'third_parties' }"
        @click="tab = 'third_parties'"
      >
        Third parties ({{ report.third_parties?.length || 0 }})
      </button>
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'cookies' }"
        @click="tab = 'cookies'"
      >
        Cookies ({{ report.cookies?.length || 0 }})
      </button>
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'scripts' }"
        @click="tab = 'scripts'"
      >
        Scripts ({{ report.scripts?.length || 0 }})
      </button>
    </div>

    <div v-show="tab === 'trackers'">
      <table v-if="report.trackers?.length">
        <thead>
          <tr>
            <th>Vendor</th>
            <th>Category</th>
            <th>URL</th>
            <th>Why it matters</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(t, i) in report.trackers" :key="i">
            <td>{{ t.name }}</td>
            <td><span :class="badgeClass(t.category)">{{ t.category }}</span></td>
            <td><code>{{ t.matched_url }}</code></td>
            <td>{{ t.why_it_matters }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">No known trackers matched.</p>
    </div>

    <div v-show="tab === 'third_parties'">
      <table v-if="report.third_parties?.length">
        <thead>
          <tr>
            <th>Domain</th>
            <th>Type</th>
            <th>Example URL</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(t, i) in report.third_parties" :key="i">
            <td>{{ t.domain }}</td>
            <td>{{ t.resource_type }}</td>
            <td><code>{{ t.url }}</code></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">No third-party requests.</p>
    </div>

    <div v-show="tab === 'cookies'">
      <table v-if="report.cookies?.length">
        <thead>
          <tr>
            <th>Name</th>
            <th>Domain</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(c, i) in report.cookies" :key="i">
            <td>{{ c.name }}</td>
            <td>{{ c.domain }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">No cookies in this session.</p>
    </div>

    <div v-show="tab === 'scripts'">
      <table v-if="report.scripts?.length">
        <thead>
          <tr>
            <th>Domain</th>
            <th>Src</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in report.scripts" :key="i">
            <td>{{ s.domain }}</td>
            <td><code>{{ s.src }}</code></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">No third-party scripts.</p>
    </div>
  </section>
</template>
