/**
 * 闂団偓濮瑰倸鍨庨弸鎰侀崸妤冩祲閸?API
 */
import request from '@/utils/api'

// ==================== 閻㈢喐鍨氱悰灞艰礋闁板秶鐤?====================

// 閼惧嘲褰囬幍鈧張澶屾晸閹存劘顢戞稉娲帳缂?
export function getGenerationConfigs(params) {
  return request({
    url: '/requirement-analysis/generation-config/',
    method: 'get',
    params
  })
}

// 閼惧嘲褰囬悽鐔稿灇鐞涘奔璐熼柊宥囩枂鐠囷附鍎?
export function getGenerationConfigDetail(id) {
  return request({
    url: `/requirement-analysis/generation-config/${id}/`,
    method: 'get'
  })
}

// 閸掓稑缂撻悽鐔稿灇鐞涘奔璐熼柊宥囩枂
export function createGenerationConfig(data) {
  return request({
    url: '/requirement-analysis/generation-config/',
    method: 'post',
    data
  })
}

// 閺囧瓨鏌婇悽鐔稿灇鐞涘奔璐熼柊宥囩枂
export function updateGenerationConfig(id, data) {
  return request({
    url: `/requirement-analysis/generation-config/${id}/`,
    method: 'put',
    data
  })
}

// 閸掔娀娅庨悽鐔稿灇鐞涘奔璐熼柊宥囩枂
export function deleteGenerationConfig(id) {
  return request({
    url: `/requirement-analysis/generation-config/${id}/`,
    method: 'delete'
  })
}

// 閼惧嘲褰囧ú鏄忕┈閻ㄥ嫮鏁撻幋鎰攽娑撴椽鍘ょ純?
export function getActiveGenerationConfig() {
  return request({
    url: '/requirement-analysis/generation-config/active/',
    method: 'get'
  })
}

// ==================== AI 濡€崇€烽柊宥囩枂 ====================

// 閼惧嘲褰囬幍鈧張?AI 濡€崇€烽柊宥囩枂
export function getAIModelConfigs(params) {
  return request({
    url: '/requirement-analysis/ai-models/',
    method: 'get',
    params
  })
}

// 閼惧嘲褰囧ú鏄忕┈閻?AI 濡€崇€烽柊宥囩枂
export function getActiveAIModelConfig(modelType, role) {
  return request({
    url: '/requirement-analysis/ai-models/active/',
    method: 'get',
    params: { model_type: modelType, role }
  })
}

// 閸掓稑缂?AI 濡€崇€烽柊宥囩枂
export function createAIModelConfig(data) {
  return request({
    url: '/requirement-analysis/ai-models/',
    method: 'post',
    data
  })
}

// 閺囧瓨鏌?AI 濡€崇€烽柊宥囩枂
export function updateAIModelConfig(id, data) {
  return request({
    url: `/requirement-analysis/ai-models/${id}/`,
    method: 'put',
    data
  })
}

// 閸掔娀娅?AI 濡€崇€烽柊宥囩枂
export function deleteAIModelConfig(id) {
  return request({
    url: `/requirement-analysis/ai-models/${id}/`,
    method: 'delete'
  })
}

// 閼惧嘲褰?AI 闁板秶鐤嗛幀缁樻殶閿涘牏鏁ゆ禍搴ゎ潡閺嶅浄绱?
export function getAIModelConfigCount() {
  return request({
    url: '/requirement-analysis/ai-models/count/',
    method: 'get'
  })
}

// ==================== 閹绘劗銇氱拠宥夊帳缂?====================

// 閼惧嘲褰囬幍鈧張澶嬪絹缁€楦跨槤闁板秶鐤?
export function getPromptConfigs(params) {
  return request({
    url: '/requirement-analysis/prompts/',
    method: 'get',
    params
  })
}

// 閼惧嘲褰囧ú鏄忕┈閻ㄥ嫭褰佺粈楦跨槤闁板秶鐤?
export function getActivePromptConfig(promptType) {
  return request({
    url: '/requirement-analysis/prompts/active/',
    method: 'get',
    params: { prompt_type: promptType }
  })
}

// 閸掓稑缂撻幓鎰仛鐠囧秹鍘ょ純?
export function createPromptConfig(data) {
  return request({
    url: '/requirement-analysis/prompts/',
    method: 'post',
    data
  })
}

// 閺囧瓨鏌婇幓鎰仛鐠囧秹鍘ょ純?
export function updatePromptConfig(id, data) {
  return request({
    url: `/requirement-analysis/prompts/${id}/`,
    method: 'put',
    data
  })
}

// 閸掔娀娅庨幓鎰仛鐠囧秹鍘ょ純?
export function deletePromptConfig(id) {
  return request({
    url: `/requirement-analysis/prompts/${id}/`,
    method: 'delete'
  })
}

// ==================== 鐎电厧鍙嗛懛顏勫З閸栨牗绁寸拠?====================

// 鐏忓挜I閻㈢喐鍨氶惃鍕ゴ鐠囨洜鏁ゆ笟瀣嚤閸忋儱鍩孶I閼奉亜濮╅崠鏍侀崸?
export function importToAutomation(taskId, caseIndices) {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/import-to-automation/`,
    method: 'post',
    data: { case_indices: caseIndices }
  })
}

// 鐏忓棝鍣扮痪鍐叉倵閻ㄥ嫮鏁ゆ笟瀣絺闁礁鍩孶I閼奉亜濮╅崠鏍ㄥ⒔鐞涘矉绱欓悪顒傜彌閹笛嗩攽閿涘瞼鏁撻幋鎰秿鐏炲繐鎷伴惇鐔风杽缂佹挻鐏夐敍?
export function importAdoptedToAutomation(taskId, testCasesData) {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/import-to-automation/`,
    method: 'post',
    data: { test_cases: testCasesData }
  })
}

// ==================== 瀹搞儰缍斿ù浣侯吀閻?====================

// 閹绘劒姘﹂棁鈧Ч鍌濈槑鐎?
export function submitTaskReview(taskId, notes = '') {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/submit_review/`,
    method: 'post',
    data: { notes }
  })
}

// 鐎光剝澹掗柅姘崇箖
export function approveTask(taskId, notes = '') {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/approve/`,
    method: 'post',
    data: { notes }
  })
}

// 妞瑰啿娲栨禒璇插
export function rejectTask(taskId, notes) {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/reject/`,
    method: 'post',
    data: { notes }
  })
}

// 閺嶅洩顔囬幍褑顢戝ù瀣槸
export function markTaskExecuted(taskId) {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/mark_executed/`,
    method: 'post'
  })
}

// 閺嶅洩顔囨禒璇插鐎瑰本鍨?
export function markTaskDone(taskId) {
  return request({
    url: `/requirement-analysis/testcase-generation/${taskId}/mark_done/`,
    method: 'post'
  })
}

// 閼惧嘲褰囧銉ょ稊濞翠胶绮虹拋?
export function getWorkflowStats(params) {
  return request({
    url: '/requirement-analysis/testcase-generation/workflow_stats/',
    method: 'get',
    params
  })
}

// 閹靛綊鍣洪崚鐘绘珟濞村鐦悽銊ょ伐閻㈢喐鍨氭禒璇插
export function batchDeleteTasks(payload) {
  const data = Array.isArray(payload) ? { ids: payload } : payload
  return request({
    url: '/requirement-analysis/testcase-generation/batch_delete/',
    method: 'post',
    data
  })
}
