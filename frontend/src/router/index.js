import { createRouter, createWebHistory } from 'vue-router'
import DiscoverView from '../views/DiscoverView.vue'
import WatchlistView from '../views/WatchlistView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  {
    path: '/',
    name: 'discover',
    component: DiscoverView
  },
  {
    path: '/watchlist',
    name: 'watchlist',
    component: WatchlistView
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
