<template>
  <div class="prediction-container">
    <!-- Top Navigation -->
    <nav class="navbar" :style="s.navbar">
      <div :style="s.navBrand" @click="$router.push('/')" style="cursor:pointer">MIROFISH OFFLINE</div>
      <div :style="s.navLinks">
        <span :style="s.navTag">Prediction Market Engine</span>
      </div>
    </nav>

    <div :style="s.mainContent">
      <!-- Header -->
      <div :style="s.header">
        <div>
          <h1 :style="s.title">Prediction Markets</h1>
          <p :style="s.subtitle">Fetch markets → Simulate agent discourse → Surface trading signals</p>
        </div>
        <button :style="s.backBtn" @click="$router.push('/')">← Back to Home</button>
      </div>

      <div :style="s.layout">
        <!-- Left: Market Browser -->
        <div :style="s.leftPanel">
          <div :style="s.panelBox">
            <div :style="s.panelHeader">
              <span :style="s.statusDot">■</span> Active Markets
              <button :style="s.refreshBtn" @click="loadMarkets" :disabled="loadingMarkets">
                {{ loadingMarkets ? 'Loading...' : 'Refresh' }}
              </button>
            </div>

            <!-- Filters -->
            <div :style="s.filterRow">
              <input
                v-model="searchQuery"
                :style="s.searchInput"
                placeholder="Search markets..."
                @keyup.enter="loadMarkets"
              />
              <select v-model="minVolume" :style="s.selectInput" @change="loadMarkets">
                <option :value="1000">$1K+ vol</option>
                <option :value="10000">$10K+ vol</option>
                <option :value="100000">$100K+ vol</option>
                <option :value="1000000">$1M+ vol</option>
              </select>
            </div>

            <!-- Market List -->
            <div :style="s.marketList">
              <div v-if="marketsError" :style="s.errorBox">{{ marketsError }}</div>
              <div v-if="!loadingMarkets && markets.length === 0 && !marketsError" :style="s.emptyState">
                No markets found. Try adjusting filters or click Refresh.
              </div>
              <div
                v-for="market in markets"
                :key="market.condition_id"
                :style="[s.marketCard, selectedMarket?.condition_id === market.condition_id ? s.marketCardSelected : {}]"
                @click="selectMarket(market)"
              >
                <div :style="s.marketTitle">{{ market.title }}</div>
                <div :style="s.marketMeta">
                  <span :style="s.priceTag">
                    YES {{ (market.prices[0] * 100).toFixed(0) }}%
                  </span>
                  <span :style="s.priceTagNo">
                    NO {{ (market.prices[1] * 100).toFixed(0) }}%
                  </span>
                  <span :style="s.volumeTag">${{ formatNumber(market.volume) }} vol</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Run Panel + Results -->
        <div :style="s.rightPanel">
          <!-- Selected Market + Run Button -->
          <div :style="s.panelBox">
            <div :style="s.panelHeader">
              <span :style="s.statusDot">■</span> Prediction Run
            </div>

            <div v-if="!selectedMarket" :style="s.emptyState">
              Select a market from the left panel to run a prediction.
            </div>

            <div v-else>
              <div :style="s.selectedInfo">
                <div :style="s.selectedTitle">{{ selectedMarket.title }}</div>
                <div :style="s.selectedPrices">
                  Market: YES {{ (selectedMarket.prices[0] * 100).toFixed(1) }}% / NO {{ (selectedMarket.prices[1] * 100).toFixed(1) }}%
                </div>
                <div v-if="selectedMarket.description" :style="s.selectedDesc">
                  {{ selectedMarket.description.substring(0, 300) }}{{ selectedMarket.description.length > 300 ? '...' : '' }}
                </div>
              </div>

              <button
                :style="[s.runBtn, activeRun ? s.runBtnDisabled : {}]"
                @click="startRun"
                :disabled="!!activeRun"
              >
                {{ activeRun ? 'Running...' : 'Run Prediction' }} →
              </button>
            </div>
          </div>

          <!-- Active Run Progress -->
          <div v-if="activeRun" :style="s.panelBox">
            <div :style="s.panelHeader">
              <span :style="s.statusDot">■</span> Progress
            </div>
            <div :style="s.progressSection">
              <div :style="s.progressStage">{{ activeRun.status }}</div>
              <div :style="s.progressMsg">{{ activeRun.progress_message }}</div>
              <div :style="s.progressBar">
                <div :style="{ ...s.progressFill, width: progressPercent + '%' }"></div>
              </div>
            </div>
          </div>

          <!-- Signal Result -->
          <div v-if="completedRun && completedRun.signal" :style="s.panelBox">
            <div :style="s.panelHeader">
              <span :style="s.statusDot">■</span> Trading Signal
            </div>
            <div :style="s.signalSection">
              <div :style="[s.signalDirection, signalColor]">
                {{ completedRun.signal.direction }}
              </div>
              <div :style="s.signalGrid">
                <div :style="s.signalItem">
                  <div :style="s.signalLabel">Simulated P(Yes)</div>
                  <div :style="s.signalValue">{{ (completedRun.signal.simulated_probability * 100).toFixed(1) }}%</div>
                </div>
                <div :style="s.signalItem">
                  <div :style="s.signalLabel">Market P(Yes)</div>
                  <div :style="s.signalValue">{{ (completedRun.signal.market_probability * 100).toFixed(1) }}%</div>
                </div>
                <div :style="s.signalItem">
                  <div :style="s.signalLabel">Edge</div>
                  <div :style="s.signalValue">{{ (completedRun.signal.edge * 100).toFixed(1) }}%</div>
                </div>
                <div :style="s.signalItem">
                  <div :style="s.signalLabel">Confidence</div>
                  <div :style="s.signalValue">{{ (completedRun.signal.confidence * 100).toFixed(0) }}%</div>
                </div>
              </div>
              <div :style="s.signalReasoning">{{ completedRun.signal.reasoning }}</div>
            </div>

            <!-- Sentiment Breakdown -->
            <div v-if="completedRun.sentiment" :style="s.sentimentSection">
              <div :style="s.sentimentHeader">Stance Breakdown</div>
              <div :style="s.stanceCounts">
                <span :style="s.stanceFor">For: {{ completedRun.sentiment.stance_counts.for }}</span>
                <span :style="s.stanceAgainst">Against: {{ completedRun.sentiment.stance_counts.against }}</span>
                <span :style="s.stanceNeutral">Neutral: {{ completedRun.sentiment.stance_counts.neutral }}</span>
              </div>
              <div v-if="completedRun.sentiment.key_arguments_for.length">
                <div :style="s.argHeader">Key Arguments For:</div>
                <ul :style="s.argList">
                  <li v-for="(arg, i) in completedRun.sentiment.key_arguments_for" :key="'for-'+i">{{ arg }}</li>
                </ul>
              </div>
              <div v-if="completedRun.sentiment.key_arguments_against.length">
                <div :style="s.argHeader">Key Arguments Against:</div>
                <ul :style="s.argList">
                  <li v-for="(arg, i) in completedRun.sentiment.key_arguments_against" :key="'against-'+i">{{ arg }}</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Run History -->
          <div :style="s.panelBox">
            <div :style="s.panelHeader">
              <span :style="s.statusDot">■</span> History
              <button :style="s.refreshBtn" @click="loadHistory">Refresh</button>
            </div>
            <div :style="s.historyList">
              <div v-if="history.length === 0" :style="s.emptyState">No prediction runs yet.</div>
              <div
                v-for="run in history"
                :key="run.run_id"
                :style="s.historyItem"
                @click="viewRun(run)"
              >
                <div :style="s.historyTitle">{{ run.market?.title || run.run_id }}</div>
                <div :style="s.historyMeta">
                  <span :style="statusStyle(run.status)">{{ run.status }}</span>
                  <span v-if="run.signal" :style="s.historySignal">{{ run.signal.direction }} ({{ (run.signal.edge * 100).toFixed(1) }}%)</span>
                  <span :style="s.historyDate">{{ formatDate(run.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { fetchMarkets, startPredictionRun, getRunStatus, getRun, listRuns } from '../api/prediction'

const mono = 'JetBrains Mono, monospace'

const s = reactive({
  navbar: { height: '60px', background: '#000', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 40px' },
  navBrand: { fontFamily: mono, fontWeight: '800', letterSpacing: '1px', fontSize: '1.2rem' },
  navLinks: { display: 'flex', alignItems: 'center' },
  navTag: { fontFamily: mono, fontSize: '0.8rem', color: '#FF4500', border: '1px solid #FF4500', padding: '4px 12px' },
  mainContent: { maxWidth: '1400px', margin: '0 auto', padding: '30px 40px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '30px' },
  title: { fontSize: '2rem', fontWeight: '520', margin: '0 0 8px 0', letterSpacing: '-1px' },
  subtitle: { color: '#666', fontFamily: mono, fontSize: '0.85rem' },
  backBtn: { background: 'none', border: '1px solid #E5E5E5', padding: '8px 20px', fontFamily: mono, fontSize: '0.85rem', cursor: 'pointer', color: '#666' },
  layout: { display: 'flex', gap: '30px', alignItems: 'flex-start' },
  leftPanel: { flex: '0.9', minWidth: '0' },
  rightPanel: { flex: '1.1', display: 'flex', flexDirection: 'column', gap: '20px' },
  panelBox: { border: '1px solid #E5E5E5', padding: '20px', marginBottom: '0' },
  panelHeader: { fontFamily: mono, fontSize: '0.8rem', color: '#999', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' },
  statusDot: { color: '#FF4500', fontSize: '0.8rem' },
  refreshBtn: { marginLeft: 'auto', background: 'none', border: '1px solid #DDD', padding: '4px 12px', fontFamily: mono, fontSize: '0.75rem', cursor: 'pointer', color: '#666' },
  filterRow: { display: 'flex', gap: '10px', marginBottom: '15px' },
  searchInput: { flex: '1', border: '1px solid #DDD', padding: '8px 12px', fontFamily: mono, fontSize: '0.85rem', outline: 'none', background: '#FAFAFA' },
  selectInput: { border: '1px solid #DDD', padding: '8px 12px', fontFamily: mono, fontSize: '0.85rem', background: '#FAFAFA', cursor: 'pointer' },
  marketList: { maxHeight: '600px', overflowY: 'auto' },
  marketCard: { padding: '15px', borderBottom: '1px solid #F0F0F0', cursor: 'pointer', transition: 'background 0.15s' },
  marketCardSelected: { background: '#FFF5F0', borderLeft: '3px solid #FF4500' },
  marketTitle: { fontSize: '0.95rem', fontWeight: '500', marginBottom: '8px', lineHeight: '1.4' },
  marketMeta: { display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' },
  priceTag: { fontFamily: mono, fontSize: '0.8rem', color: '#16a34a', fontWeight: '600', background: '#f0fdf4', padding: '2px 8px' },
  priceTagNo: { fontFamily: mono, fontSize: '0.8rem', color: '#dc2626', fontWeight: '600', background: '#fef2f2', padding: '2px 8px' },
  volumeTag: { fontFamily: mono, fontSize: '0.75rem', color: '#999' },
  emptyState: { textAlign: 'center', color: '#999', padding: '30px', fontFamily: mono, fontSize: '0.85rem' },
  errorBox: { color: '#dc2626', background: '#fef2f2', padding: '12px', fontFamily: mono, fontSize: '0.85rem', marginBottom: '10px' },
  selectedInfo: { marginBottom: '15px' },
  selectedTitle: { fontSize: '1.1rem', fontWeight: '520', marginBottom: '8px' },
  selectedPrices: { fontFamily: mono, fontSize: '0.9rem', color: '#666', marginBottom: '8px' },
  selectedDesc: { fontSize: '0.85rem', color: '#888', lineHeight: '1.5' },
  runBtn: { width: '100%', background: '#000', color: '#fff', border: 'none', padding: '15px', fontFamily: mono, fontWeight: '700', fontSize: '1rem', cursor: 'pointer', letterSpacing: '1px', display: 'flex', justifyContent: 'space-between' },
  runBtnDisabled: { background: '#666', cursor: 'not-allowed' },
  progressSection: { padding: '10px 0' },
  progressStage: { fontFamily: mono, fontSize: '0.85rem', fontWeight: '600', textTransform: 'uppercase', color: '#FF4500', marginBottom: '5px' },
  progressMsg: { fontSize: '0.85rem', color: '#666', marginBottom: '10px' },
  progressBar: { height: '4px', background: '#F0F0F0', borderRadius: '2px', overflow: 'hidden' },
  progressFill: { height: '100%', background: '#FF4500', transition: 'width 0.5s ease' },
  signalSection: { padding: '10px 0' },
  signalDirection: { fontFamily: mono, fontSize: '1.5rem', fontWeight: '700', marginBottom: '15px' },
  signalGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '15px' },
  signalItem: { border: '1px solid #F0F0F0', padding: '12px' },
  signalLabel: { fontFamily: mono, fontSize: '0.7rem', color: '#999', marginBottom: '4px' },
  signalValue: { fontFamily: mono, fontSize: '1.2rem', fontWeight: '600' },
  signalReasoning: { fontSize: '0.9rem', color: '#666', lineHeight: '1.6', borderTop: '1px solid #F0F0F0', paddingTop: '12px' },
  sentimentSection: { borderTop: '1px solid #F0F0F0', paddingTop: '15px', marginTop: '15px' },
  sentimentHeader: { fontFamily: mono, fontSize: '0.8rem', color: '#999', marginBottom: '10px' },
  stanceCounts: { display: 'flex', gap: '15px', marginBottom: '12px', fontFamily: mono, fontSize: '0.85rem' },
  stanceFor: { color: '#16a34a', fontWeight: '600' },
  stanceAgainst: { color: '#dc2626', fontWeight: '600' },
  stanceNeutral: { color: '#999' },
  argHeader: { fontFamily: mono, fontSize: '0.75rem', color: '#999', marginTop: '10px', marginBottom: '5px' },
  argList: { fontSize: '0.85rem', color: '#666', lineHeight: '1.6', paddingLeft: '20px', margin: '0' },
  historyList: { maxHeight: '300px', overflowY: 'auto' },
  historyItem: { padding: '12px 0', borderBottom: '1px solid #F0F0F0', cursor: 'pointer' },
  historyTitle: { fontSize: '0.9rem', fontWeight: '500', marginBottom: '5px', lineHeight: '1.3' },
  historyMeta: { display: 'flex', gap: '10px', alignItems: 'center', fontFamily: mono, fontSize: '0.75rem' },
  historySignal: { color: '#FF4500', fontWeight: '600' },
  historyDate: { color: '#BBB' },
})

// State
const markets = ref([])
const loadingMarkets = ref(false)
const marketsError = ref('')
const searchQuery = ref('')
const minVolume = ref(10000)
const selectedMarket = ref(null)
const activeRun = ref(null)
const completedRun = ref(null)
const history = ref([])
let pollInterval = null

// Computed
const progressPercent = computed(() => {
  if (!activeRun.value) return 0
  const map = {
    fetching_market: 5,
    generating_scenario: 15,
    creating_project: 20,
    building_graph: 35,
    preparing_simulation: 50,
    running_simulation: 70,
    analyzing: 90,
    completed: 100,
  }
  return map[activeRun.value.status] || 0
})

const signalColor = computed(() => {
  if (!completedRun.value?.signal) return {}
  const dir = completedRun.value.signal.direction
  if (dir === 'BUY_YES') return { color: '#16a34a' }
  if (dir === 'BUY_NO') return { color: '#dc2626' }
  return { color: '#999' }
})

// Methods
const formatNumber = (n) => {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'K'
  return n.toString()
}

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const statusStyle = (status) => {
  const colors = {
    completed: { color: '#16a34a', fontWeight: '600' },
    failed: { color: '#dc2626', fontWeight: '600' },
  }
  return colors[status] || { color: '#FF4500', fontWeight: '600' }
}

const loadMarkets = async () => {
  loadingMarkets.value = true
  marketsError.value = ''
  try {
    const res = await fetchMarkets({
      min_volume: minVolume.value,
      limit: 50,
      search: searchQuery.value || undefined,
    })
    markets.value = res.data || []
  } catch (e) {
    marketsError.value = e.message || 'Failed to load markets'
    markets.value = []
  } finally {
    loadingMarkets.value = false
  }
}

const selectMarket = (market) => {
  selectedMarket.value = market
}

const startRun = async () => {
  if (!selectedMarket.value || activeRun.value) return

  try {
    const res = await startPredictionRun(selectedMarket.value)
    const { run_id } = res.data
    activeRun.value = { run_id, status: 'fetching_market', progress_message: 'Starting...' }
    completedRun.value = null
    startPolling(run_id)
  } catch (e) {
    marketsError.value = 'Failed to start prediction run: ' + (e.message || '')
  }
}

const startPolling = (runId) => {
  stopPolling()
  pollInterval = setInterval(async () => {
    try {
      const res = await getRunStatus(runId)
      const data = res.data
      activeRun.value = data

      if (data.status === 'completed' || data.status === 'failed') {
        stopPolling()
        activeRun.value = null

        // Load full run for results
        const fullRes = await getRun(runId)
        completedRun.value = fullRes.data
        loadHistory()
      }
    } catch (e) {
      console.error('Poll error:', e)
    }
  }, 3000)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const viewRun = async (run) => {
  try {
    const res = await getRun(run.run_id)
    completedRun.value = res.data
  } catch (e) {
    console.error('Failed to load run:', e)
  }
}

const loadHistory = async () => {
  try {
    const res = await listRuns(20)
    history.value = res.data || []
  } catch (e) {
    console.error('Failed to load history:', e)
  }
}

// Lifecycle
onMounted(() => {
  loadMarkets()
  loadHistory()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.prediction-container {
  min-height: 100vh;
  background: #fff;
}
</style>
