<template>
  <div class="device-management">
    <!-- 页面标题 -->
    <div class="device-header">
      <h3>手机设备管理</h3>
    </div>

    <!-- Tab 切换：真实设备 / 虚拟设备池 -->
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- ========== 真实设备 Tab ========== -->
      <el-tab-pane label="真实设备 (USB/远程)" name="real">
        <div class="tab-header">
          <div class="tab-stats">
            <span class="stat-item">在线: <b>{{ realOnlineCount }}</b></span>
            <span class="stat-item">总数: <b>{{ devices.length }}</b></span>
          </div>
          <div class="device-actions">
            <el-button type="primary" :icon="Refresh" :loading="refreshing" @click="refreshDevices">
              发现设备
            </el-button>
            <el-button type="success" :icon="Plus" @click="showAddRemoteDialog">
              连接远程设备
            </el-button>
          </div>
        </div>

        <el-table
          v-loading="loading"
          :data="devices"
          style="width: 100%; margin-top: 12px"
          :empty-text="emptyText"
        >
          <el-table-column prop="name" label="设备名称" min-width="150">
            <template #default="{ row }">
              <span>{{ row.name || row.device_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="device_id" label="设备序列号" min-width="180" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="locked_by" label="锁定用户" width="120">
            <template #default="{ row }">
              <span v-if="row.locked_by_name">{{ row.locked_by_name }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="android_version" label="Android版本" width="120" />
          <el-table-column prop="connection_type" label="连接类型" width="110">
            <template #default="{ row }">
              <el-tag :type="getConnectionType(row.connection_type) === 'local' ? 'primary' : 'warning'" size="small">
                {{ getConnectionTypeName(row.connection_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="ip_address" label="IP地址" width="150">
            <template #default="{ row }">
              <span v-if="row.ip_address">{{ row.ip_address }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="320" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'available' || row.status === 'online'" link size="small" type="primary" @click="lockDevice(row)">锁定</el-button>
              <el-button v-if="row.status === 'locked'" link size="small" type="success" @click="unlockDevice(row)">解锁</el-button>
              <el-button v-if="isRemoteDevice(row.connection_type) && row.status === 'offline'" link size="small" type="warning" :loading="reconnectingDevices[row.id]" @click="reconnectDevice(row)">重连</el-button>
              <el-button v-if="row.status === 'available' || row.status === 'online'" link size="small" type="info" @click="captureDeviceScreen(row)">截屏查看</el-button>
              <el-button link size="small" type="primary" @click="startScreenRecord(row)">启动录屏</el-button>
              <el-button link size="small" @click="viewDeviceInfo(row)">详情</el-button>
              <el-button v-if="isRemoteDevice(row.connection_type) && (row.status === 'online' || row.status === 'available')" link size="small" type="warning" @click="disconnectDevice(row)">断开</el-button>
              <el-button link size="small" type="danger" @click="handleDeleteDevice(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ========== 虚拟设备池 Tab ========== -->
      <el-tab-pane label="虚拟设备池" name="virtual">
        <div class="tab-header">
          <div class="tab-stats">
            <el-tag type="success" size="small">运行中: {{ virtualRunningCount }}</el-tag>
            <el-tag type="info" size="small" style="margin-left:8px;">已停止: {{ virtualStoppedCount }}</el-tag>
            <span class="stat-item" style="margin-left:12px;">总数: <b>{{ virtualDevices.length }}</b></span>
          </div>
          <div class="device-actions">
            <el-button type="primary" :icon="Plus" :loading="initPoolLoading" @click="handleInitPool">
              初始化设备池
            </el-button>
            <el-button type="success" :icon="VideoPlay" :loading="batchStarting" @click="handleBatchStart">
              批量启动
            </el-button>
            <el-button type="warning" :icon="VideoPause" :loading="batchStopping" @click="handleBatchStop">
              批量停止
            </el-button>
            <el-button :icon="Refresh" :loading="virtualLoading" @click="fetchVirtualDevices">
              刷新
            </el-button>
          </div>
        </div>

        <el-table
          v-loading="virtualLoading"
          :data="virtualDevices"
          style="width: 100%; margin-top: 12px"
          empty-text="暂无虚拟设备，请点击「初始化设备池」从预设模板创建"
        >
          <el-table-column prop="name" label="设备名称" min-width="140">
            <template #default="{ row }">
              <el-icon style="margin-right:4px;vertical-align:middle;"><Monitor /></el-icon>
              <span>{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="brand_display" label="品牌" width="80" />
          <el-table-column prop="model" label="型号" width="120" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="virtualStatusType(row.status)" size="small">
                {{ row.status_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="android_version" label="Android" width="90" />
          <el-table-column label="处理器" min-width="170">
            <template #default="{ row }">
              <span style="font-size:12px;">{{ row.cpu }}</span>
            </template>
          </el-table-column>
          <el-table-column label="RAM/存储" width="100">
            <template #default="{ row }">
              <span>{{ row.ram_gb }}GB / {{ row.storage_gb }}GB</span>
            </template>
          </el-table-column>
          <el-table-column prop="screen_resolution" label="分辨率" width="110" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'stopped' || row.status === 'error'" link size="small" type="success" :loading="actionLoading[row.id]" @click="startVD(row)">启动</el-button>
              <el-button v-if="row.status === 'running'" link size="small" type="warning" :loading="actionLoading[row.id]" @click="stopVD(row)">停止</el-button>
              <el-button v-if="row.status === 'running'" link size="small" type="primary" :loading="actionLoading[row.id]" @click="restartVD(row)">重启</el-button>
              <el-button link size="small" type="danger" @click="handleDeleteVD(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- ========== 对话框 ========== -->
    <!-- 添加远程设备对话框 -->
    <el-dialog v-model="addRemoteDialogVisible" title="添加远程设备" width="500px" :close-on-click-modal="false">
      <el-form ref="remoteDeviceFormRef" :model="remoteDeviceForm" :rules="remoteDeviceRules" label-width="100px">
        <el-form-item label="IP地址" prop="ip_address">
          <el-input v-model="remoteDeviceForm.ip_address" placeholder="请输入远程设备IP地址" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="remoteDeviceForm.port" :min="1" :max="65535" placeholder="默认5555" style="width: 100%" />
        </el-form-item>
        <el-alert title="提示" type="info" :closable="false" style="margin-top: 10px">
          <div>请确保：1.远程设备已开启ADB调试 2.远程设备已开启网络ADB（adb tcpip 5555） 3.网络连接正常</div>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="addRemoteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="connecting" @click="connectRemoteDevice">连接</el-button>
      </template>
    </el-dialog>

    <!-- 设备详情对话框 -->
    <el-dialog v-model="deviceInfoDialogVisible" title="设备详情" width="650px">
      <el-descriptions v-if="selectedDevice" :column="2" border>
        <el-descriptions-item label="设备名称">{{ selectedDevice.name || selectedDevice.device_id }}</el-descriptions-item>
        <el-descriptions-item label="设备序列号">{{ selectedDevice.device_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(selectedDevice.status)" size="small">{{ getStatusText(selectedDevice.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="锁定用户">{{ selectedDevice.locked_by_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Android版本">{{ selectedDevice.android_version || '-' }}</el-descriptions-item>
        <el-descriptions-item label="连接类型">
          <el-tag :type="getConnectionType(selectedDevice.connection_type) === 'local' ? 'primary' : 'warning'" size="small">{{ getConnectionTypeName(selectedDevice.connection_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ selectedDevice.ip_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ selectedDevice.port || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(selectedDevice.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(selectedDevice.updated_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="deviceInfoDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 设备截屏对话框 -->
    <el-dialog v-model="screenshotDialogVisible" title="设备屏幕截图" width="400px" :close-on-click-modal="false">
      <div v-if="screenshotLoading" style="text-align:center;padding:40px;">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top:12px;color:#909399;">正在获取设备截图...</p>
      </div>
      <div v-else-if="screenshotBase64" style="text-align:center;">
        <img :src="screenshotBase64" style="max-width:100%;border-radius:8px;border:1px solid #e2e8f0;" alt="设备截图" />
        <div style="margin-top:12px;">
          <el-button size="small" :icon="Refresh" @click="refreshScreenshot">刷新截图</el-button>
        </div>
      </div>
      <div v-else style="text-align:center;padding:40px;color:#909399;">
        获取截图失败，请检查设备连接状态
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Loading, Monitor, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import {
  getDeviceList,
  discoverDevices,
  lockDevice as apiLockDevice,
  unlockDevice as apiUnlockDevice,
  connectDevice,
  disconnectDevice as apiDisconnectDevice,
  deleteDevice,
  startDeviceScreenRecord,
  captureDeviceScreenshot,
  getVirtualDevices,
  deleteVirtualDevice,
  startVirtualDevice,
  stopVirtualDevice,
  restartVirtualDevice,
  initDevicePool,
  batchStartDevices,
  batchStopDevices,
  getDevicePoolStatus,
} from '@/api/app-automation'
import { getDeviceStatusType, getDeviceStatusText, formatDateTime } from '@/utils/app-automation-helpers'

// ---- Tab ----
const activeTab = ref('real')

// ---- 真实设备 ----
const remoteDeviceFormRef = ref(null)
const devices = ref([])
const loading = ref(false)
const refreshing = ref(false)
const connecting = ref(false)
const reconnectingDevices = ref({})
const addRemoteDialogVisible = ref(false)
const deviceInfoDialogVisible = ref(false)
const selectedDevice = ref(null)
const emptyText = ref('暂无设备，请点击刷新设备或添加远程设备')
const refreshTimer = ref(null)

const realOnlineCount = computed(() => {
  return devices.value.filter(d => d.status === 'online' || d.status === 'available').length
})

const remoteDeviceForm = ref({ ip_address: '', port: 5555 })

const screenshotDialogVisible = ref(false)
const screenshotLoading = ref(false)
const screenshotBase64 = ref('')
const screenshotDeviceId = ref(null)

const remoteDeviceRules = {
  ip_address: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: '请输入有效的IP地址', trigger: 'blur' }
  ],
  port: [{ required: true, message: '请输入端口号', trigger: 'blur' }]
}

// ---- 虚拟设备 ----
const virtualDevices = ref([])
const virtualLoading = ref(false)
const initPoolLoading = ref(false)
const batchStarting = ref(false)
const batchStopping = ref(false)
const actionLoading = ref({})

const virtualRunningCount = computed(() => virtualDevices.value.filter(d => d.status === 'running').length)
const virtualStoppedCount = computed(() => virtualDevices.value.filter(d => d.status === 'stopped').length)

// ========== 真实设备方法 ==========
const getDevices = async () => {
  loading.value = true
  try {
    const res = await getDeviceList({ page: 1, page_size: 1000 })
    devices.value = res.data.results || []
    emptyText.value = devices.value.length === 0 ? '暂无设备，请点击"发现设备"扫描ADB连接或点击"连接远程设备"通过IP连接' : ''
  } catch (error) {
    console.error('获取设备列表失败:', error)
    ElMessage.error('获取设备列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const refreshDevices = async () => {
  refreshing.value = true
  try {
    const res = await discoverDevices()
    if (res.data.success) {
      devices.value = res.data.devices || []
      ElMessage.success(res.data.message || '设备列表已刷新')
    } else {
      ElMessage.error(res.data.message || '刷新设备列表失败')
    }
  } catch (error) {
    console.error('刷新设备列表失败:', error)
    ElMessage.error('刷新设备列表失败: ' + (error.message || '未知错误'))
  } finally {
    refreshing.value = false
  }
}

const showAddRemoteDialog = () => {
  addRemoteDialogVisible.value = true
  remoteDeviceForm.value = { ip_address: '', port: 5555 }
  if (remoteDeviceFormRef.value) remoteDeviceFormRef.value.clearValidate()
}

const connectRemoteDevice = async () => {
  if (!remoteDeviceFormRef.value) return
  remoteDeviceFormRef.value.validate(async (valid) => {
    if (!valid) return
    connecting.value = true
    try {
      const res = await connectDevice({ ip_address: remoteDeviceForm.value.ip_address, port: remoteDeviceForm.value.port })
      if (res.data.success) {
        ElMessage.success(res.data.message || '远程设备连接成功')
        addRemoteDialogVisible.value = false
        await getDevices()
      } else {
        ElMessage.error(res.data.message || '连接远程设备失败')
      }
    } catch (error) {
      ElMessage.error('连接远程设备失败: ' + (error.message || '未知错误'))
    } finally {
      connecting.value = false
    }
  })
}

const reconnectDevice = async (device) => {
  if (!device.ip_address || !device.port) { ElMessage.error('设备信息不完整，无法重连'); return }
  reconnectingDevices.value[device.id] = true
  try {
    const res = await connectDevice({ ip_address: device.ip_address, port: device.port })
    if (res.data.success) { ElMessage.success('设备重连成功'); await getDevices() }
    else { ElMessage.error(res.data.message || '设备重连失败') }
  } catch (error) { ElMessage.error('设备重连失败') }
  finally { reconnectingDevices.value[device.id] = false }
}

const disconnectDevice = async (device) => {
  try {
    await ElMessageBox.confirm(`确定要断开设备 ${device.name || device.device_id} 的连接吗？`, '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await apiDisconnectDevice(device.id)
    if (res.data.success) { ElMessage.success('设备已断开'); await getDevices() }
    else { ElMessage.error(res.data.message || '断开设备失败') }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('断开设备失败: ' + (error.message || '未知错误'))
  }
}

const viewDeviceInfo = (device) => { selectedDevice.value = device; deviceInfoDialogVisible.value = true }

const lockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(`确定要锁定设备 ${device.name || device.device_id} 吗？`, '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await apiLockDevice(device.id)
    if (res.data.success) { ElMessage.success('设备已锁定'); await getDevices() }
    else { ElMessage.error(res.data.message || '锁定设备失败') }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('锁定设备失败: ' + (error.message || '未知错误'))
  }
}

const unlockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(`确定要解锁设备 ${device.name || device.device_id} 吗？`, '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await apiUnlockDevice(device.id)
    if (res.data.success) { ElMessage.success('设备已解锁'); await getDevices() }
    else { ElMessage.error(res.data.message || '解锁设备失败') }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('解锁设备失败: ' + (error.message || '未知错误'))
  }
}

const handleDeleteDevice = async (device) => {
  try {
    await ElMessageBox.confirm(`确定要删除设备 ${device.name || device.device_id} 吗？删除后将无法恢复。`, '删除设备', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await deleteDevice(device.id)
    if (res.status === 204 || res.status === 200) { ElMessage.success('设备已删除'); await getDevices() }
    else { ElMessage.error(res.data?.message || '删除设备失败') }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除设备失败: ' + (error.message || '未知错误'))
  }
}

const startScreenRecord = async (device) => {
  try {
    const res = await startDeviceScreenRecord(device.id)
    if (res.data.success) ElMessage.success('设备录屏已启动')
    else ElMessage.error(res.data.message || '启动录屏失败')
  } catch (error) { ElMessage.error('启动录屏失败: ' + (error.message || '未知错误')) }
}

const captureDeviceScreen = async (device) => {
  screenshotDeviceId.value = device.id
  screenshotDialogVisible.value = true
  screenshotLoading.value = true
  screenshotBase64.value = ''
  try {
    const res = await captureDeviceScreenshot(device.id)
    if (res.data?.success || res.data?.code === 0) {
      screenshotBase64.value = res.data?.data?.content || res.data?.content || ''
    } else { ElMessage.error(res.data?.msg || res.data?.message || '获取截图失败') }
  } catch (error) { ElMessage.error('获取截图失败: ' + (error.response?.data?.msg || error.message || '未知错误')) }
  finally { screenshotLoading.value = false }
}

const refreshScreenshot = async () => {
  if (!screenshotDeviceId.value) return
  screenshotLoading.value = true
  try {
    const res = await captureDeviceScreenshot(screenshotDeviceId.value)
    if (res.data?.success || res.data?.code === 0) screenshotBase64.value = res.data?.data?.content || res.data?.content || ''
  } catch (error) { /* silent */ }
  finally { screenshotLoading.value = false }
}

// ========== 虚拟设备方法 ==========
const fetchVirtualDevices = async () => {
  virtualLoading.value = true
  try {
    const res = await getVirtualDevices({ page: 1, page_size: 100 })
    virtualDevices.value = res.data.results || []
  } catch (error) {
    console.error('获取虚拟设备列表失败:', error)
    ElMessage.error('获取虚拟设备列表失败')
  } finally {
    virtualLoading.value = false
  }
}

const handleInitPool = async () => {
  initPoolLoading.value = true
  try {
    const res = await initDevicePool()
    if (res.data.success) {
      ElMessage.success(res.data.message || '设备池初始化成功')
      await fetchVirtualDevices()
    } else { ElMessage.error(res.data.message || '初始化失败') }
  } catch (error) { ElMessage.error('初始化设备池失败: ' + (error.message || '')) }
  finally { initPoolLoading.value = false }
}

const startVD = async (device) => {
  setActionLoading(device.id, true)
  try {
    const res = await startVirtualDevice(device.id)
    if (res.data.success) { ElMessage.success('设备已启动'); await fetchVirtualDevices() }
    else { ElMessage.error(res.data.message || '启动失败') }
  } catch (error) { ElMessage.error('启动失败') }
  finally { setActionLoading(device.id, false) }
}

const stopVD = async (device) => {
  setActionLoading(device.id, true)
  try {
    const res = await stopVirtualDevice(device.id)
    if (res.data.success) { ElMessage.success('设备已停止'); await fetchVirtualDevices() }
    else { ElMessage.error(res.data.message || '停止失败') }
  } catch (error) { ElMessage.error('停止失败') }
  finally { setActionLoading(device.id, false) }
}

const restartVD = async (device) => {
  setActionLoading(device.id, true)
  try {
    const res = await restartVirtualDevice(device.id)
    if (res.data.success) { ElMessage.success('设备已重启'); await fetchVirtualDevices() }
    else { ElMessage.error(res.data.message || '重启失败') }
  } catch (error) { ElMessage.error('重启失败') }
  finally { setActionLoading(device.id, false) }
}

const handleBatchStart = async () => {
  batchStarting.value = true
  try {
    const res = await batchStartDevices([])
    if (res.data.success) { ElMessage.success(res.data.message || '批量启动完成'); await fetchVirtualDevices() }
    else { ElMessage.error(res.data.message || '批量启动失败') }
  } catch (error) { ElMessage.error('批量启动失败') }
  finally { batchStarting.value = false }
}

const handleBatchStop = async () => {
  batchStopping.value = true
  try {
    const res = await batchStopDevices([])
    if (res.data.success) { ElMessage.success(res.data.message || '批量停止完成'); await fetchVirtualDevices() }
    else { ElMessage.error(res.data.message || '批量停止失败') }
  } catch (error) { ElMessage.error('批量停止失败') }
  finally { batchStopping.value = false }
}

const handleDeleteVD = async (device) => {
  try {
    await ElMessageBox.confirm(`确定要删除虚拟设备 ${device.name} 吗？`, '删除虚拟设备', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await deleteVirtualDevice(device.id)
    if (res.status === 204 || res.status === 200) { ElMessage.success('虚拟设备已删除'); await fetchVirtualDevices() }
    else { ElMessage.error(res.data?.message || '删除失败') }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const setActionLoading = (id, val) => { actionLoading.value = { ...actionLoading.value, [id]: val } }

// ========== Tab 切换 ==========
const onTabChange = (tabName) => {
  if (tabName === 'virtual' && virtualDevices.value.length === 0) {
    fetchVirtualDevices()
  }
}

// ========== 工具函数 ==========
const formatDate = formatDateTime
const getStatusType = getDeviceStatusType
const getStatusText = getDeviceStatusText

const getConnectionType = (type) => {
  if (type === 'emulator' || type === 'usb') return 'local'
  return 'remote'
}

const getConnectionTypeName = (type) => {
  const map = { emulator: '模拟器', remote_emulator: '远程设备', real_device: 'USB真机', remote: '远程设备', usb: 'USB连接' }
  return map[type] || type
}

const isRemoteDevice = (type) => type === 'remote_emulator' || type === 'remote'

const virtualStatusType = (status) => {
  const map = { running: 'success', stopped: 'info', paused: 'warning', error: 'danger' }
  return map[status] || 'info'
}

// ========== 生命周期 ==========
onMounted(() => {
  getDevices()
  refreshTimer.value = setInterval(() => { if (activeTab.value === 'real') getDevices() }, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer.value) clearInterval(refreshTimer.value)
})
</script>

<style scoped lang="scss">
.device-management {
  padding: 20px;
}

.device-header {
  margin-bottom: 0;
  h3 {
    margin: 0;
    font-size: 20px;
    color: #303133;
  }
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0 4px;
}

.tab-stats {
  display: flex;
  align-items: center;
  gap: 4px;
  .stat-item {
    color: #606266;
    font-size: 14px;
    b { color: #409eff; }
  }
}

.device-actions {
  display: flex;
  gap: 10px;
}

.dialog-footer {
  text-align: right;
}
</style>
