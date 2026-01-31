<template>
  <div class="settings-view">
    <h1>Settings</h1>

    <div v-if="loading" class="loading">Loading settings...</div>

    <form v-else @submit.prevent="saveSettings" class="settings-form">
      <!-- TMDB Section -->
      <section class="settings-section">
        <h2>TMDB</h2>
        <div class="form-group">
          <label for="tmdb_api_key">API Key</label>
          <div class="input-with-action">
            <input
              id="tmdb_api_key"
              v-model="form.tmdb_api_key"
              :type="showKeys.tmdb ? 'text' : 'password'"
              :placeholder="settings.tmdb_api_key_masked || 'Enter TMDB API key'"
            />
            <button type="button" @click="showKeys.tmdb = !showKeys.tmdb" class="btn-icon">
              {{ showKeys.tmdb ? 'Hide' : 'Show' }}
            </button>
            <button type="button" @click="testConnection('tmdb')" :disabled="testing.tmdb" class="btn-test">
              {{ testing.tmdb ? 'Testing...' : 'Test' }}
            </button>
          </div>
          <div v-if="testResults.tmdb" :class="['test-result', testResults.tmdb.success ? 'success' : 'error']">
            {{ testResults.tmdb.message }}
          </div>
        </div>
      </section>

      <!-- Radarr Section -->
      <section class="settings-section">
        <h2>Radarr</h2>
        <div class="form-group">
          <label for="radarr_url">URL</label>
          <input
            id="radarr_url"
            v-model="form.radarr_url"
            type="url"
            :placeholder="settings.radarr_url || 'http://localhost:7878'"
          />
        </div>
        <div class="form-group">
          <label for="radarr_api_key">API Key</label>
          <div class="input-with-action">
            <input
              id="radarr_api_key"
              v-model="form.radarr_api_key"
              :type="showKeys.radarr ? 'text' : 'password'"
              :placeholder="settings.radarr_api_key_masked || 'Enter Radarr API key'"
            />
            <button type="button" @click="showKeys.radarr = !showKeys.radarr" class="btn-icon">
              {{ showKeys.radarr ? 'Hide' : 'Show' }}
            </button>
            <button type="button" @click="testConnection('radarr')" :disabled="testing.radarr" class="btn-test">
              {{ testing.radarr ? 'Testing...' : 'Test' }}
            </button>
          </div>
          <div v-if="testResults.radarr" :class="['test-result', testResults.radarr.success ? 'success' : 'error']">
            {{ testResults.radarr.message }}
          </div>
        </div>
        <div class="form-group">
          <label for="radarr_root_folder">Root Folder Path</label>
          <input
            id="radarr_root_folder"
            v-model="form.radarr_root_folder"
            type="text"
            :placeholder="settings.radarr_root_folder || '/movies'"
          />
          <div class="hint">Leave empty to use Radarr's default root folder</div>
        </div>
      </section>

      <!-- Sonarr Section -->
      <section class="settings-section">
        <h2>Sonarr</h2>
        <div class="form-group">
          <label for="sonarr_url">URL</label>
          <input
            id="sonarr_url"
            v-model="form.sonarr_url"
            type="url"
            :placeholder="settings.sonarr_url || 'http://localhost:8989'"
          />
        </div>
        <div class="form-group">
          <label for="sonarr_api_key">API Key</label>
          <div class="input-with-action">
            <input
              id="sonarr_api_key"
              v-model="form.sonarr_api_key"
              :type="showKeys.sonarr ? 'text' : 'password'"
              :placeholder="settings.sonarr_api_key_masked || 'Enter Sonarr API key'"
            />
            <button type="button" @click="showKeys.sonarr = !showKeys.sonarr" class="btn-icon">
              {{ showKeys.sonarr ? 'Hide' : 'Show' }}
            </button>
            <button type="button" @click="testConnection('sonarr')" :disabled="testing.sonarr" class="btn-test">
              {{ testing.sonarr ? 'Testing...' : 'Test' }}
            </button>
          </div>
          <div v-if="testResults.sonarr" :class="['test-result', testResults.sonarr.success ? 'success' : 'error']">
            {{ testResults.sonarr.message }}
          </div>
        </div>
        <div class="form-group">
          <label for="sonarr_root_folder">Root Folder Path</label>
          <input
            id="sonarr_root_folder"
            v-model="form.sonarr_root_folder"
            type="text"
            :placeholder="settings.sonarr_root_folder || '/tv'"
          />
          <div class="hint">Leave empty to use Sonarr's default root folder</div>
        </div>
      </section>

      <!-- Save Button -->
      <div class="form-actions">
        <button type="submit" :disabled="saving" class="btn-save">
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
        <div v-if="saveMessage" :class="['save-message', saveSuccess ? 'success' : 'error']">
          {{ saveMessage }}
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import settingsService from '@/services/settings'

const loading = ref(true)
const saving = ref(false)
const saveMessage = ref('')
const saveSuccess = ref(false)

const settings = ref({})
const form = reactive({
  tmdb_api_key: '',
  radarr_url: '',
  radarr_api_key: '',
  radarr_root_folder: '',
  sonarr_url: '',
  sonarr_api_key: '',
  sonarr_root_folder: ''
})

const showKeys = reactive({
  tmdb: false,
  radarr: false,
  sonarr: false
})

const testing = reactive({
  tmdb: false,
  radarr: false,
  sonarr: false
})

const testResults = reactive({
  tmdb: null,
  radarr: null,
  sonarr: null
})

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  try {
    settings.value = await settingsService.getSettings()
    // Pre-fill URLs and root folders (not keys, those stay masked)
    form.radarr_url = settings.value.radarr_url || ''
    form.radarr_root_folder = settings.value.radarr_root_folder || ''
    form.sonarr_url = settings.value.sonarr_url || ''
    form.sonarr_root_folder = settings.value.sonarr_root_folder || ''
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMessage.value = ''

  try {
    // Only send non-empty values
    const updates = {}
    Object.entries(form).forEach(([key, value]) => {
      if (value && value.trim()) {
        updates[key] = value.trim()
      }
    })

    if (Object.keys(updates).length === 0) {
      saveMessage.value = 'No changes to save'
      saveSuccess.value = false
      return
    }

    settings.value = await settingsService.updateSettings(updates)
    saveMessage.value = 'Settings saved successfully'
    saveSuccess.value = true

    // Clear form fields (keys are now saved)
    form.tmdb_api_key = ''
    form.radarr_api_key = ''
    form.sonarr_api_key = ''
  } catch (error) {
    saveMessage.value = 'Failed to save settings'
    saveSuccess.value = false
    console.error('Failed to save settings:', error)
  } finally {
    saving.value = false
  }
}

async function testConnection(service) {
  testing[service] = true
  testResults[service] = null

  try {
    testResults[service] = await settingsService.testConnection(service)
  } catch (error) {
    testResults[service] = { success: false, message: 'Connection test failed' }
  } finally {
    testing[service] = false
  }
}
</script>

<style scoped>
.settings-view {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
  color: #fff;
}

.settings-section {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.settings-section h2 {
  margin: 0 0 1rem 0;
  color: #e94560;
  font-size: 1.2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f1a;
  color: #fff;
  font-size: 1rem;
}

.input-with-action {
  display: flex;
  gap: 0.5rem;
}

.input-with-action input {
  flex: 1;
}

.btn-icon, .btn-test {
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #252540;
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
}

.btn-icon:hover, .btn-test:hover {
  background: #333355;
}

.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-result {
  margin-top: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.test-result.success {
  background: rgba(0, 200, 83, 0.2);
  color: #00c853;
}

.test-result.error {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
}

.form-actions {
  margin-top: 2rem;
}

.btn-save {
  width: 100%;
  padding: 1rem;
  border: none;
  border-radius: 4px;
  background: #e94560;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.btn-save:hover {
  background: #d63850;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.save-message {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  text-align: center;
}

.save-message.success {
  background: rgba(0, 200, 83, 0.2);
  color: #00c853;
}

.save-message.error {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
}

.loading {
  text-align: center;
  color: #ccc;
  padding: 2rem;
}

.hint {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: #888;
}
</style>
