<template>
  <div class="device-simulator">
    <!-- 左侧：手机投屏 -->
    <div class="ds-phone-panel">
      <h3 class="panel-title">手机投屏</h3>
      <div class="phone-container" :class="{ 'no-device': !activeDevice }">
        <!-- 手机框 -->
        <div class="phone-frame">
          <!-- 屏幕区域 -->
          <div class="phone-screen" ref="screenRef"
               @click="onScreenClick"
               @touchstart.prevent="onTouchStart"
               @touchend.prevent="onTouchEnd">
            <!-- 设备屏幕(真机ADB截图) -->
            <img v-if="screenImage" :src="screenImage" class="phone-screen-img"
                 draggable="false" />

            <!-- 连接中 -->
            <div v-else-if="connecting" class="screen-placeholder">
              <el-icon class="is-loading" :size="32"><Loading /></el-icon>
              <p>正在连接设备...</p>
            </div>

            <!-- 无设备占位 -->
            <div v-else class="screen-placeholder">
              <el-icon :size="48"><Iphone /></el-icon>
              <p>请选择或添加一个真实设备</p>
              <p class="placeholder-hint">通过 USB 连接手机后点击"发现设备"</p>
              <el-button size="small" type="primary" @click="discoverAndLoad" style="margin-top:12px">
                发现设备
              </el-button>
            </div>

            <!-- 截图错误覆盖 -->
            <div v-if="screenError && screenImage" class="screen-error-overlay">
              <p>{{ screenError }}</p>
              <el-button size="small" @click="refreshScreen">重试</el-button>
            </div>
          </div>

          <!-- 底部导航按键 -->
          <div class="phone-nav" v-if="activeDevice && !connecting">
            <button class="nav-btn" @click="sendKey(3)" title="Home">🏠</button>
            <button class="nav-btn" @click="sendKey(4)" title="返回">↩</button>
            <button class="nav-btn" @click="sendKey(187)" title="多任务">⬛</button>
          </div>
        </div>

        <!-- 设备信息 -->
        <div class="phone-info" v-if="activeDevice">
          <div class="info-row">
            <strong>{{ activeDevice.name || activeDevice.device_id }}</strong>
            <el-tag :type="statusType(activeDevice.status)" size="small">
              {{ statusLabel(activeDevice.status) }}
            </el-tag>
          </div>
          <div class="info-row sub">
            <span>Android {{ activeDevice.android_version || '-' }}</span>
            <span v-if="deviceInfo.screen_size">{{ deviceInfo.screen_size }}</span>
            <span :class="deviceInfo.adb_connected ? 'connected' : 'disconnected'">
              {{ deviceInfo.adb_connected ? 'ADB已连接' : 'ADB断开' }}
            </span>
          </div>
          <!-- 操控按钮 -->
          <div class="control-row">
            <el-button-group size="small">
              <el-button @click="sendKey(26)" title="电源键">电源</el-button>
              <el-button @click="sendKey(24)" title="音量+">🔊</el-button>
              <el-button @click="sendKey(25)" title="音量-">🔉</el-button>
              <el-button @click="refreshScreen" :loading="screenPolling" title="刷新屏幕">🔄</el-button>
            </el-button-group>
            <el-button size="small" type="danger" plain @click="closeDevice">关闭</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：设备列表 + 录屏文件 -->
    <div class="ds-list-panel">
      <el-tabs v-model="rightTab" class="ds-tabs">
        <!-- 设备列表 Tab -->
        <el-tab-pane label="设备列表" name="devices">
          <div class="ds-toolbar">
            <h3>设备列表</h3>
            <div class="ds-actions">
              <el-button size="small" type="primary" :icon="Plus" @click="showAddDevice">连接设备</el-button>
              <el-button size="small" type="success" :icon="Refresh" @click="discoverAndLoad" :loading="loading">
                发现设备
              </el-button>
            </div>
          </div>

          <!-- 未发现设备提示 -->
          <el-alert
            v-if="devices.length === 0 && !loading"
            title="未发现设备"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom:12px"
          >
            <template #default>
              <p style="margin:0;font-size:12px">
                请通过 USB 连接 Android 手机，开启<strong>开发者选项 → USB调试</strong>，然后点击"发现设备"。
                <br/>也可以点击"连接设备"通过局域网 IP 远程连接。
              </p>
            </template>
          </el-alert>

          <!-- 设备表格 -->
          <el-table :data="devices" v-loading="loading" stripe size="small" class="ds-table"
                    highlight-current-row @row-click="selectDevice">
            <el-table-column label="设备" min-width="160">
              <template #default="{ row }">
                <div class="device-row">
                  <el-icon :size="18"><Iphone /></el-icon>
                  <div>
                    <div class="dr-name">{{ row.name || row.device_id }}</div>
                    <div class="dr-sub">{{ row.device_id }} · {{ typeLabel(row.connection_type) }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="系统" width="80">
              <template #default="{ row }">{{ row.android_version || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link size="small" type="primary" @click.stop="selectDevice(row)">
                  {{ activeDevice?.id === row.id ? '已选' : '投屏' }}
                </el-button>
                <el-button
                  v-if="row.connection_type === 'remote_emulator'"
                  link size="small" type="warning" @click.stop="disconnectDevice(row)">
                  断开
                </el-button>
                <el-button link size="small" type="danger" @click.stop="removeDevice(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 录屏文件 Tab -->
        <el-tab-pane name="records">
          <template #label>
            <span>录屏文件 <el-badge v-if="recordFiles.length" :value="recordFiles.length" class="tab-badge" /></span>
          </template>
          <div class="ds-toolbar">
            <h3>录屏文件</h3>
            <div class="ds-actions">
              <el-button size="small" :icon="Refresh" @click="loadRecords" :loading="recordsLoading">刷新</el-button>
              <el-button
                v-if="recordFiles.length && activeDevice"
                size="small" type="danger" plain @click="clearAllRecords">
                清空全部
              </el-button>
            </div>
          </div>

          <el-empty v-if="!recordsLoading && recordFiles.length === 0" description="暂无录屏文件" :image-size="60" />

          <div v-else class="record-file-list">
            <div v-for="file in recordFiles" :key="file.filename" class="record-file-item">
              <div class="rfi-info">
                <el-icon :size="18" color="#409eff"><VideoCamera /></el-icon>
                <div class="rfi-name" :title="file.filename">{{ file.filename }}</div>
              </div>
              <div class="rfi-meta">
                <span class="rfi-size">{{ formatFileSize(file.size) }}</span>
                <span class="rfi-time">{{ formatTime(file.created_at) }}</span>
              </div>
              <div class="rfi-actions">
                <el-button link size="small" type="primary" @click="playRecord(file)">播放</el-button>
                <el-button link size="small" type="danger" @click="deleteRecordFile(file)">删除</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 录屏播放对话框 -->
    <el-dialog v-model="playVisible" title="录屏播放" width="420px" destroy-on-close>
      <video v-if="playUrl" :src="playUrl" controls autoplay style="width:100%;max-height:70vh;border-radius:8px" />
      <el-empty v-else description="无法加载视频" />
    </el-dialog>

    <!-- 连接设备对话框 (IP:Port) -->
    <el-dialog v-model="addVisible" title="连接远程设备" width="420px" destroy-on-close>
      <el-alert
        title="USB 连接"
        type="success"
        :closable="false"
        style="margin-bottom:16px"
      >
        如果是 USB 连接，请直接点"发现设备"按钮，无需手动添加。
      </el-alert>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="85px">
        <el-form-item label="IP 地址" prop="ip_address">
          <el-input v-model="form.ip_address" placeholder="如: 192.168.1.100" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="connectDevice">连接</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Iphone, Loading, VideoCamera } from '@element-plus/icons-vue'
import {
  getDeviceList, discoverDevices,
  getDeviceLiveScreenshot,
  sendDeviceTouch, sendDeviceKeyevent,
  connectDevice as apiConnectDevice,
  disconnectDevice as apiDisconnectDevice,
  deleteDevice as apiDeleteDevice,
  getDeviceInfo,
  getDeviceScreenRecords,
  deleteDeviceScreenRecord
} from '@/api/app-automation'

// ===== State =====
const loading = ref(false)
const saving = ref(false)
const connecting = ref(false)
const addVisible = ref(false)
const devices = ref([])
const activeDevice = ref(null)
const screenImage = ref('')
const screenError = ref('')
const screenPolling = ref(false)
const screenRef = ref(null)
const formRef = ref(null)
const deviceInfo = reactive({ screen_size: '', adb_connected: false })

let pollTimeout = null
let isPolling = false   // 防止请求堆积
let pollInterval = 1500  // 基础轮询间隔（可动态调整）

const form = ref({
  ip_address: '',
  port: 5555,
})

const rules = {
  ip_address: [
    { required: true, message: '请输入设备 IP 地址' },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: 'IP 格式不正确' },
  ],
  port: [{ required: true, message: '请输入端口' }],
}

// 录屏相关状态
const rightTab = ref('devices')
const recordFiles = ref([])
const recordsLoading = ref(false)
const playVisible = ref(false)
const playUrl = ref('')

// ===== Methods =====
function typeLabel(t) {
  const map = { real_device: 'USB真机', remote_emulator: '远程设备', emulator: '模拟器', usb: 'USB' }
  return map[t] || t
}
function statusType(s) {
  const map = { available: 'success', online: 'success', locked: 'warning', offline: 'info' }
  return map[s] || 'info'
}
function statusLabel(s) {
  const map = { available: '在线', online: '在线', locked: '已锁定', offline: '离线' }
  return map[s] || s
}

function showAddDevice() {
  form.value = { ip_address: '', port: 5555 }
  addVisible.value = true
}

async function loadDevices() {
  loading.value = true
  try {
    const res = await getDeviceList({ page: 1, page_size: 1000 })
    devices.value = res.data?.results || res.data || []
  } catch {
    devices.value = []
  } finally {
    loading.value = false
  }
}

async function discoverAndLoad() {
  loading.value = true
  try {
    const res = await discoverDevices()
    if (res.data?.success) {
      if (res.data.devices?.length) {
        ElMessage.success(res.data.message || `发现 ${res.data.devices.length} 个设备`)
        devices.value = res.data.devices
      } else {
        ElMessage.warning(res.data.message || '未发现设备')
        devices.value = []
      }
    }
  } catch (err) {
    ElMessage.error('发现设备失败: ' + (err.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function connectDevice() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const res = await apiConnectDevice({
      ip_address: form.value.ip_address,
      port: form.value.port,
    })
    if (res.data?.success) {
      ElMessage.success('设备连接成功！')
      addVisible.value = false
      await loadDevices()
    }
  } catch (err) {
    ElMessage.error('连接失败: ' + (err.response?.data?.message || err.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

// ==== 设备选择 & 投屏 ====
async function selectDevice(device) {
  if (activeDevice.value?.id === device.id) return

  closeDevice()
  activeDevice.value = device
  connecting.value = true
  screenImage.value = ''
  screenError.value = ''

  // 获取设备信息
  try {
    const res = await getDeviceInfo(device.id)
    if (res.data?.success) {
      Object.assign(deviceInfo, res.data.data)
    }
  } catch {}

  // 稍等后开始投屏
  setTimeout(() => {
    connecting.value = false
    startScreenMirror()
  }, 800)
}

function startScreenMirror() {
  if (!activeDevice.value) return
  screenPolling.value = true
  refreshScreen()
  scheduleNextPoll()
}

// 使用 setTimeout 链替代 setInterval，防止请求堆积
function scheduleNextPoll(delay = pollInterval) {
  if (!screenPolling.value) return
  clearTimeout(pollTimeout)
  pollTimeout = setTimeout(async () => {
    if (!isPolling) {
      isPolling = true
      await refreshScreen()
      isPolling = false
    }
    scheduleNextPoll()
  }, delay)
}

// 操作后强制刷新：取消当前定时器，立即刷新后重新排期
function refreshAndReschedule(delay = 500) {
  clearTimeout(pollTimeout)
  pollTimeout = setTimeout(async () => {
    if (!isPolling) {
      isPolling = true
      await refreshScreen()
      isPolling = false
    }
    scheduleNextPoll()
  }, delay)
}

async function refreshScreen() {
  if (!activeDevice.value) return
  screenError.value = ''
  try {
    // 使用 quality=60, max_size=360 减少带宽（手机框只显示小尺寸）
    const res = await getDeviceLiveScreenshot(activeDevice.value.id, {
      quality: 60,
      max_size: 360,
      format: 'jpeg',
    })
    if (res.data?.success) {
      screenImage.value = res.data.data.image
      // 更新屏幕尺寸信息
      if (res.data.data.width) {
        deviceInfo.screen_size = `${res.data.data.width}x${res.data.data.height}`
      }
    } else {
      screenError.value = res.data?.message || '截图失败'
    }
  } catch (err) {
    screenError.value = '截图失败: ' + (err.message || '网络错误')
  }
}

function closeDevice() {
  stopScreenMirror()
  activeDevice.value = null
  screenImage.value = ''
  screenError.value = ''
  connecting.value = false
}

function stopScreenMirror() {
  screenPolling.value = false
  clearTimeout(pollTimeout)
  pollTimeout = null
  isPolling = false
}

// ==== 设备操控 ====
async function sendKey(keycode) {
  if (!activeDevice.value) return
  try {
    await sendDeviceKeyevent(activeDevice.value.id, { keycode })
    refreshAndReschedule(600)
  } catch {
    // 静默
  }
}

// 点击投屏画面 = 点击真实设备
function getScreenCoords(e) {
  if (!screenRef.value) return null
  const rect = screenRef.value.getBoundingClientRect()
  // 根据设备实际分辨率计算比例
  const img = screenRef.value.querySelector('img')
  let scaleX, scaleY
  if (img && img.naturalWidth && img.naturalHeight) {
    scaleX = img.naturalWidth / rect.width
    scaleY = img.naturalHeight / rect.height
  } else {
    // 回退到设备信息中的尺寸
    const [w, h] = (deviceInfo.screen_size || '1080x2340').split('x').map(Number)
    scaleX = w / rect.width
    scaleY = h / rect.height
  }
  return {
    x: Math.round((e.clientX - rect.left) * scaleX),
    y: Math.round((e.clientY - rect.top) * scaleY),
    scaleX, scaleY,
  }
}

function onScreenClick(e) {
  if (!activeDevice.value || !screenRef.value) return
  const coords = getScreenCoords(e)
  if (!coords) return
  sendDeviceTouch(activeDevice.value.id, { x: coords.x, y: coords.y, action: 'tap' })
    .then(() => refreshAndReschedule(500))
    .catch(() => {})
}

function onTouchStart(e) {
  if (!activeDevice.value) return
  const touch = e.touches[0]
  if (!touch) return
  const coords = getScreenCoords(touch)
  if (!coords) return
  this._touchData = { x: coords.x, y: coords.y, t: Date.now() }
}

function onTouchEnd(e) {
  if (!activeDevice.value || !this._touchData) return
  const touch = e.changedTouches[0]
  if (!touch) return
  const coords = getScreenCoords(touch)
  if (!coords) return
  const { x: sx, y: sy, t: st } = this._touchData
  const dt = Date.now() - st
  const dx = Math.abs(coords.x - sx)
  const dy = Math.abs(coords.y - sy)

  if (dx < 30 && dy < 30 && dt < 300) {
    sendDeviceTouch(activeDevice.value.id, { x: sx, y: sy, action: 'tap' })
  } else if (dt > 400) {
    sendDeviceTouch(activeDevice.value.id, { x: sx, y: sy, action: 'long_press', duration: dt })
  }
  refreshAndReschedule(500)
  this._touchData = null
}

// ==== 设备管理 ====
async function disconnectDevice(device) {
  try {
    await apiDisconnectDevice(device.id)
    ElMessage.success('已断开连接')
    if (activeDevice.value?.id === device.id) closeDevice()
    await loadDevices()
  } catch {
    ElMessage.error('断开失败')
  }
}

async function removeDevice(device) {
  try {
    await ElMessageBox.confirm(`确定删除 ${device.name || device.device_id}？`, '确认', { type: 'warning' })
  } catch { return }
  try {
    await apiDeleteDevice(device.id)
    if (activeDevice.value?.id === device.id) closeDevice()
    ElMessage.success('已删除')
    await loadDevices()
  } catch { ElMessage.error('删除失败') }
}

// ==== 录屏文件管理 ====
async function loadRecords() {
  if (!activeDevice.value) return
  recordsLoading.value = true
  try {
    const res = await getDeviceScreenRecords(activeDevice.value.id)
    if (res.data?.success) {
      recordFiles.value = res.data.data || []
    }
  } catch {
    // 静默失败
  } finally {
    recordsLoading.value = false
  }
}

async function deleteRecordFile(file) {
  try {
    await ElMessageBox.confirm(`确定删除录屏文件 "${file.filename}"？此操作不可恢复。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
    })
  } catch { return }

  try {
    const res = await deleteDeviceScreenRecord(activeDevice.value.id, file.filename)
    if (res.data?.success) {
      ElMessage.success(res.data.message || '已删除')
      recordFiles.value = recordFiles.value.filter(f => f.filename !== file.filename)
    } else {
      ElMessage.error(res.data?.message || '删除失败')
    }
  } catch (err) {
    ElMessage.error('删除失败: ' + (err.response?.data?.message || err.message || '网络错误'))
  }
}

async function clearAllRecords() {
  if (!recordFiles.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定清空当前设备所有 ${recordFiles.value.length} 个录屏文件？此操作不可恢复。`,
      '确认清空',
      { type: 'warning', confirmButtonText: '全部删除' }
    )
  } catch { return }

  let errCount = 0
  for (const file of [...recordFiles.value]) {
    try {
      await deleteDeviceScreenRecord(activeDevice.value.id, file.filename)
    } catch {
      errCount++
    }
  }
  ElMessage.success(`已清空录屏文件${errCount ? `（${errCount}个失败）` : ''}`)
  await loadRecords()
}

function playRecord(file) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
  playUrl.value = `${baseUrl}/media/screen_records/${file.filename}`
  playVisible.value = true
}

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return size.toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function formatTime(ts) {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 切换设备时自动加载录屏列表
watch(activeDevice, (newVal) => {
  if (newVal) {
    loadRecords()
  } else {
    recordFiles.value = []
  }
})

// ==== Lifecycle ====
onMounted(() => {
  loadDevices()
})

onBeforeUnmount(() => {
  stopScreenMirror()
})
</script>

<style scoped lang="scss">
.device-simulator {
  display: flex;
  gap: 24px;
  padding: var(--spacing-lg);
  max-width: 1400px;
  height: calc(100vh - 120px);
  overflow: hidden;
}

// ===== 左侧手机面板 =====
.ds-phone-panel {
  flex: 0 0 420px;
  display: flex;
  flex-direction: column;
  .panel-title { margin: 0 0 16px; font-size: 16px; color: var(--color-text); }
}

.phone-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;

  &.no-device { justify-content: center; opacity: 0.7; }
}

.phone-frame {
  width: 320px;
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border-radius: 32px;
  border: 3px solid #2a2a3e;
  box-shadow: 0 20px 60px rgba(0,0,0,0.4), inset 0 0 20px rgba(255,255,255,0.03);
  overflow: hidden;
  position: relative;
}

.phone-screen {
  width: 100%;
  height: 580px;
  background: #0a0a1a;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: crosshair;
  overflow: hidden;
}

.phone-screen-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: auto;
}

.screen-error-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(200, 40, 40, 0.85);
  color: #fff;
  padding: 8px 12px;
  font-size: 12px;
  text-align: center;
  p { margin: 0 0 4px; }
}

// ===== 空白占位 =====
.screen-placeholder {
  text-align: center;
  color: rgba(255,255,255,0.3);
  p { margin: 8px 0 0; font-size: 13px; }
  .placeholder-hint { font-size: 11px; opacity: 0.6; margin-top: 4px; }
}

// ===== 手机导航键 =====
.phone-nav {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 10px 0 14px;
}

.nav-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
  &:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.8); }
}

// ===== 设备信息 =====
.phone-info {
  width: 320px;
  padding: 12px 16px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  strong { font-size: 14px; color: var(--color-text); }
  &.sub { margin-top: 4px; font-size: 12px; color: var(--color-text-secondary); gap: 8px; }
}

.connected { color: #67c23a; }
.disconnected { color: #f56c6c; }

.control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  gap: 8px;
}

// ===== 右侧设备列表 =====
.ds-list-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.ds-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  h3 { margin: 0; font-size: 16px; color: var(--color-text); }
}

.ds-actions { display: flex; gap: 8px; }

.ds-table { margin-top: 8px; }

.device-row {
  display: flex; align-items: center; gap: 8px;
  .dr-name { font-size: 13px; font-weight: 500; }
  .dr-sub { font-size: 11px; color: var(--color-text-muted); }
}

// ===== 录屏文件列表 =====
.tab-badge { margin-left: 4px; }

.record-file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.record-file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  gap: 12px;
  transition: background 0.15s;

  &:hover { background: var(--color-bg-hover); }
}

.rfi-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.rfi-name {
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.rfi-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.rfi-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>
