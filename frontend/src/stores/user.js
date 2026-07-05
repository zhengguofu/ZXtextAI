import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const user = ref({
    username: 'admin',
    email: 'admin@zx.local',
    first_name: 'ZX',
    last_name: 'Platform'
  })

  const isAuthenticated = computed(() => true)

  return {
    user,
    isAuthenticated
  }
})
