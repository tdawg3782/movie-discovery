import { createRouter, createWebHistory } from 'vue-router'
import DiscoverView from '../views/DiscoverView.vue'
import WatchlistView from '../views/WatchlistView.vue'
import MediaDetailView from '../views/MediaDetailView.vue'
import PersonView from '../views/PersonView.vue'
import CollectionView from '../views/CollectionView.vue'

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
    path: '/movie/:id',
    name: 'MovieDetail',
    component: MediaDetailView,
    meta: { mediaType: 'movie' }
  },
  {
    path: '/tv/:id',
    name: 'ShowDetail',
    component: MediaDetailView,
    meta: { mediaType: 'tv' }
  },
  {
    path: '/person/:id',
    name: 'Person',
    component: PersonView
  },
  {
    path: '/collection/:id',
    name: 'Collection',
    component: CollectionView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
