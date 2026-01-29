import { createRouter, createWebHistory } from 'vue-router'
import DiscoverView from '../views/DiscoverView.vue'
import WatchlistView from '../views/WatchlistView.vue'
import LibraryView from '../views/LibraryView.vue'

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
    path: '/library',
    name: 'library',
    component: LibraryView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
