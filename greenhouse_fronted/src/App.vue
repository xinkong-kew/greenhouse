<template>
  <div id="app-container" :class="{ 'mobile-mode': isMobile }">
    <!-- PC 导航栏 -->
    <nav class="navbar" v-if="!isMobile">
      <div class="nav-inner">
        <router-link to="/" class="logo">
          <span class="logo-glow">🌿</span>
          <span class="logo-text">智能温室监控系统</span>
        </router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link" active-class="active">
            <span class="nav-icon">🏠</span> 首页
          </router-link>
          <router-link to="/control" class="nav-link" active-class="active">
            <span class="nav-icon">⚙️</span> 控制面板
          </router-link>
          <router-link to="/history" class="nav-link" active-class="active">
            <span class="nav-icon">📊</span> 历史数据
          </router-link>
        </div>
        <button class="view-toggle" @click="toggleMobile" title="切换手机模式">
          📱
        </button>
      </div>
    </nav>

    <!-- 手机模式顶部栏 -->
    <nav class="navbar mobile-navbar" v-if="isMobile">
      <div class="nav-inner">
        <router-link to="/" class="logo">
          <span class="logo-glow">🌿</span>
          <span class="logo-text">智能温室</span>
        </router-link>
        <button class="view-toggle active" @click="toggleMobile" title="返回电脑模式">
          💻
        </button>
      </div>
    </nav>

    <main class="main-content">
      <div class="page-wrapper">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </div>
    </main>

    <!-- 手机模式底部导航栏 -->
    <nav class="mobile-bottom-nav" v-if="isMobile">
      <router-link to="/" class="mb-nav-link" active-class="active">
        <span class="mb-icon">🏠</span>
        <span class="mb-label">首页</span>
      </router-link>
      <router-link to="/control" class="mb-nav-link" active-class="active">
        <span class="mb-icon">⚙️</span>
        <span class="mb-label">控制</span>
      </router-link>
      <router-link to="/history" class="mb-nav-link" active-class="active">
        <span class="mb-icon">📊</span>
        <span class="mb-label">历史</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const isMobile = ref(false)

function toggleMobile() {
  isMobile.value = !isMobile.value
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif;
  background: #0a0e1a;
  color: #c8d6e5;
  line-height: 1.5;
  height: 100vh;
}

/* 背景科技网格 */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

#app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* ========== 手机模式 ========== */
#app-container.mobile-mode {
  max-width: 420px;
  margin: 0 auto;
  min-height: 100vh;
  box-shadow: 0 0 40px rgba(0, 255, 136, 0.08);
  border-left: 1px solid rgba(0, 255, 136, 0.1);
  border-right: 1px solid rgba(0, 255, 136, 0.1);
}

#app-container.mobile-mode .main-content {
  padding: 10px 10px 70px;
  overflow-y: auto;
  flex: 1;
  -webkit-overflow-scrolling: touch;
}

#app-container.mobile-mode .page-wrapper {
  max-width: 100%;
  height: auto;
  min-height: 0;
}

/* 手机模式下 body 允许滚动 */
body:has(#app-container.mobile-mode) {
  overflow-y: auto;
}

/* ========== Navbar ========== */
.navbar {
  background: rgba(10, 14, 26, 0.95);
  border-bottom: 1px solid rgba(0, 255, 136, 0.15);
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.mobile-navbar {
  padding: 0 16px;
}

.nav-inner {
  max-width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: #00ff88;
  font-size: 18px;
  font-weight: 700;
}

.logo-glow {
  font-size: 24px;
  filter: drop-shadow(0 0 6px rgba(0, 255, 136, 0.5));
}

.nav-links {
  display: flex;
  gap: 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  color: rgba(200, 214, 229, 0.7);
  text-decoration: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.nav-link:hover {
  background: rgba(0, 255, 136, 0.08);
  color: #00ff88;
}

.nav-link.active {
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  box-shadow: 0 0 12px rgba(0, 255, 136, 0.1);
}

.nav-icon {
  font-size: 14px;
}

/* ========== 视图切换按钮 ========== */
.view-toggle {
  background: rgba(0, 255, 136, 0.08);
  border: 1px solid rgba(0, 255, 136, 0.2);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1;
  margin-left: 8px;
}

.view-toggle:hover {
  background: rgba(0, 255, 136, 0.16);
  border-color: rgba(0, 255, 136, 0.4);
  box-shadow: 0 0 12px rgba(0, 255, 136, 0.15);
}

.view-toggle.active {
  background: rgba(0, 255, 136, 0.15);
  border-color: rgba(0, 255, 136, 0.4);
}

/* ========== 手机底部导航栏 ========== */
.mobile-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 420px;
  display: flex;
  background: rgba(10, 14, 26, 0.98);
  border-top: 1px solid rgba(0, 255, 136, 0.15);
  backdrop-filter: blur(10px);
  z-index: 100;
  padding: 6px 0;
  padding-bottom: max(6px, env(safe-area-inset-bottom));
}

.mb-nav-link {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 0;
  color: rgba(200, 214, 229, 0.4);
  text-decoration: none;
  border-radius: 8px;
  font-size: 10px;
  transition: all 0.2s;
}

.mb-nav-link:hover {
  color: rgba(200, 214, 229, 0.7);
}

.mb-nav-link.active {
  color: #00ff88;
}

.mb-icon {
  font-size: 20px;
}

.mb-label {
  font-size: 10px;
  font-weight: 500;
}

/* ========== Main Content ========== */
.main-content {
  flex: 1;
  width: 100%;
  padding: 16px 20px;
  overflow: hidden;
  min-height: 0;
}

.page-wrapper {
  max-width: 100%;
  margin: 0 auto;
  height: 100%;
}

/* ========== Glowing Card ========== */
.glow-card {
  background: rgba(15, 20, 40, 0.85);
  border: 1px solid rgba(0, 255, 136, 0.12);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(0, 255, 136, 0.05);
  transition: border-color 0.3s, box-shadow 0.3s;
}

.glow-card:hover {
  border-color: rgba(0, 255, 136, 0.25);
  box-shadow: 0 4px 24px rgba(0, 255, 136, 0.08), inset 0 1px 0 rgba(0, 255, 136, 0.08);
}

.glow-card-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(0, 255, 136, 0.8);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 255, 136, 0.08);
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ========== Scrollbar ========== */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: rgba(15, 20, 40, 0.5);
}
::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 136, 0.3);
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 255, 136, 0.5);
}

/* ========== Status Colors ========== */
.status-on {
  color: #00ff88;
  font-weight: 600;
}
.status-off {
  color: rgba(200, 214, 229, 0.3);
  font-weight: 600;
}
.status-alarm {
  color: #ff4757;
  font-weight: 600;
}

/* ========== Button Base ========== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 16px;
  border: 1px solid rgba(0, 255, 136, 0.2);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(0, 255, 136, 0.06);
  color: #00ff88;
}

.btn:hover {
  background: rgba(0, 255, 136, 0.14);
  border-color: rgba(0, 255, 136, 0.4);
  box-shadow: 0 0 12px rgba(0, 255, 136, 0.1);
}

.btn-secondary {
  background: rgba(200, 214, 229, 0.06);
  color: rgba(200, 214, 229, 0.7);
  border-color: rgba(200, 214, 229, 0.15);
}

.btn-secondary:hover {
  background: rgba(200, 214, 229, 0.12);
  color: #c8d6e5;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

/* ========== Responsive ========== */
@media (max-width: 1024px) {
  .main-content {
    padding: 12px;
  }
}
</style>