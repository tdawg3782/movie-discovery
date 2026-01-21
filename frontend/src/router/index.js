import { createRouter, createWebHistory } from 'vue-router'
import DiscoverView from '../views/DiscoverView.vue'
import WatchlistView from '../views/WatchlistView.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
