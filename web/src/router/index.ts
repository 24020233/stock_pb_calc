import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const LoginPage = () => import('../pages/LoginPage.vue')
const AccountsPage = () => import('../pages/AccountsPage.vue')
const ArticlesPage = () => import('../pages/ArticlesPage.vue')
const SectorsPage = () => import('../pages/SectorsPage.vue')
const PicksHistoryPage = () => import('../pages/PicksHistoryPage.vue')
const PicksPage = () => import('../pages/PicksPage.vue')
const MovementRulesPage = () => import('../pages/MovementRulesPage.vue')
const FundamentalRulesPage = () => import('../pages/FundamentalRulesPage.vue')
const TechnicalRulesPage = () => import('../pages/TechnicalRulesPage.vue')

export const router = createRouter({
  history: createWebHistory((import.meta as any).env?.BASE_URL || '/'),
  routes: [
    { path: '/', redirect: '/articles' },
    { path: '/login', component: LoginPage },
    { path: '/accounts', component: AccountsPage },
    { path: '/articles', component: ArticlesPage },
    { path: '/sectors', component: SectorsPage },
    { path: '/picks-history', component: PicksHistoryPage },
    { path: '/picks', component: PicksPage },
    { path: '/settings/movement', component: MovementRulesPage },
    { path: '/settings/fundamental', component: FundamentalRulesPage },
    { path: '/settings/technical', component: TechnicalRulesPage },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  auth.hydrateToHttp()

  if (to.path !== '/login' && !auth.isAuthed) {
    return { path: '/login', query: { next: to.fullPath } }
  }

  if (to.path === '/login' && auth.isAuthed) {
    return { path: '/accounts' }
  }

  return true
})
