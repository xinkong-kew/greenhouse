<template>
  <div class="login-page">
    <!-- 粒子背景 -->
    <div class="particles">
      <div v-for="i in 30" :key="i" class="particle" :style="particleStyle(i)"></div>
    </div>

    <!-- 浮动叶子装饰 -->
    <div class="floating-leaves">
      <div class="leaf" v-for="i in 6" :key="'leaf-'+i" :style="leafStyle(i)">
        <svg viewBox="0 0 20 20" width="100%" height="100%" fill="none">
          <path d="M10 18 C6 14 3 10 3 7 C3 4 6 2 10 2 C14 2 17 4 17 7 C17 10 14 14 10 18Z" 
                fill="#00ff88" opacity="0.6"/>
          <path d="M10 18 L10 6" stroke="#0a0e1a" stroke-width="0.8" stroke-linecap="round" opacity="0.2"/>
        </svg>
      </div>
    </div>

    <!-- 顶部标题 -->
    <div class="header-brand">
      <div class="brand-icon">
        <svg viewBox="0 0 40 40" width="48" height="48" fill="none">
          <defs>
            <linearGradient id="leafGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#00ff88"/>
              <stop offset="100%" stop-color="#00d4ff"/>
            </linearGradient>
          </defs>
          <!-- 叶子 -->
          <path d="M20 36 C12 28 6 20 6 14 C6 8 12 4 20 4 C28 4 34 8 34 14 C34 20 28 28 20 36Z" 
                fill="url(#leafGrad)" opacity="0.9"/>
          <!-- 叶脉 -->
          <path d="M20 36 L20 12" stroke="#0a0e1a" stroke-width="1.5" stroke-linecap="round" opacity="0.3"/>
          <path d="M20 20 C16 16 12 14 10 14" stroke="#0a0e1a" stroke-width="1" stroke-linecap="round" opacity="0.2"/>
          <path d="M20 20 C24 16 28 14 30 14" stroke="#0a0e1a" stroke-width="1" stroke-linecap="round" opacity="0.2"/>
          <!-- 光晕 -->
          <circle cx="20" cy="20" r="18" fill="none" stroke="#00ff88" stroke-width="0.5" opacity="0.2">
            <animate attributeName="r" values="18;22;18" dur="3s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.2;0.5;0.2" dur="3s" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>
      <div class="brand-text">
        <span class="brand-title">绿耕智控—大棚环境感知与远程调控系统</span>
        <span class="brand-subtitle">Greenhouse Smart Control System</span>
      </div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card" :class="{ 'shake': shakeCard }">
      <!-- 装饰光晕 -->
      <div class="card-glow"></div>

      <!-- 模式切换标签 -->
      <div class="tab-bar">
        <button
          class="tab-btn"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          <span class="tab-icon-tab">
            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
              <path d="M10 2a4 4 0 100 8 4 4 0 000-8zM3 14a5 5 0 0110 0v1H3v-1z"/>
              <circle cx="17" cy="6" r="2" fill="currentColor" opacity="0.6"/>
            </svg>
          </span>
          <span>登录</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          <span class="tab-icon-tab">
            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
              <rect x="3" y="3" width="14" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>
              <line x1="10" y1="7" x2="10" y2="13" stroke="currentColor" stroke-width="1.5"/>
              <line x1="7" y1="10" x2="13" y2="10" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </span>
          <span>注册</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: mode === 'forgot' }"
          @click="switchMode('forgot')"
        >
          <span class="tab-icon-tab">
            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
              <rect x="4" y="9" width="12" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/>
              <path d="M6 9V6a4 4 0 118 0v3" fill="none" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="10" cy="13" r="1" fill="currentColor"/>
            </svg>
          </span>
          <span>找回密码</span>
        </button>
      </div>

      <!-- 过渡动画容器 -->
      <transition name="form-fade" mode="out-in">
        <!-- ===== 登录模式 ===== -->
        <div class="form-container" key="login" v-if="mode === 'login'">
          <div class="form-title">
            <span class="form-title-icon">
              <svg viewBox="0 0 20 20" width="22" height="22" fill="none">
                <path d="M10 18 C6 14 3 10 3 7 C3 4 6 2 10 2 C14 2 17 4 17 7 C17 10 14 14 10 18Z" fill="#00ff88" opacity="0.8"/>
                <path d="M10 18 L10 6" stroke="#0a0e1a" stroke-width="0.8" stroke-linecap="round" opacity="0.2"/>
              </svg>
            </span>
            <span>欢迎回来</span>
          </div>
          <div class="form-group" :class="{ 'has-error': loginErrors.username }">
            <label class="form-label">
              <span class="label-icon">👤</span> 用户名
            </label>
            <input
              class="form-input"
              v-model="loginForm.username"
              placeholder="请输入用户名"
              @focus="clearLoginError('username')"
              @keydown.enter="handleLogin"
            />
            <span class="error-msg" v-if="loginErrors.username">{{ loginErrors.username }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': loginErrors.password }">
            <label class="form-label">
              <span class="label-icon">🔐</span> 密码
            </label>
            <div class="password-wrapper">
              <input
                class="form-input"
                :type="showLoginPwd ? 'text' : 'password'"
                v-model="loginForm.password"
                placeholder="请输入密码"
                @focus="clearLoginError('password')"
                @keydown.enter="handleLogin"
              />
              <button class="pwd-toggle" @click="showLoginPwd = !showLoginPwd" type="button">
                {{ showLoginPwd ? '🙈' : '👁️' }}
              </button>
            </div>
            <span class="error-msg" v-if="loginErrors.password">{{ loginErrors.password }}</span>
          </div>
          <div class="form-options">
            <label class="remember-me">
              <input type="checkbox" v-model="loginForm.remember" />
              <span class="checkmark"></span>
              <span>记住我</span>
            </label>
            <button class="link-btn" @click="switchMode('forgot')">忘记密码？</button>
          </div>
          <button class="submit-btn" @click="handleLogin" :disabled="loginLoading">
            <span class="btn-loader" v-if="loginLoading"></span>
            <span v-else>🚀 登录</span>
          </button>
          <div class="form-footer">
            还没有账号？
            <button class="link-btn" @click="switchMode('register')">立即注册</button>
          </div>
        </div>

        <!-- ===== 注册模式 ===== -->
        <div class="form-container" key="register" v-if="mode === 'register'">
          <div class="form-title">
            <span class="form-title-icon">
              <svg viewBox="0 0 20 20" width="22" height="22" fill="none">
                <rect x="3" y="3" width="14" height="14" rx="2" fill="none" stroke="#00ff88" stroke-width="1.5" opacity="0.8"/>
                <line x1="10" y1="7" x2="10" y2="13" stroke="#00ff88" stroke-width="1.5" opacity="0.8"/>
                <line x1="7" y1="10" x2="13" y2="10" stroke="#00ff88" stroke-width="1.5" opacity="0.8"/>
              </svg>
            </span>
            <span>创建账号</span>
          </div>
          <div class="form-group" :class="{ 'has-error': regErrors.username }">
            <label class="form-label">
              <span class="label-icon">👤</span> 用户名
            </label>
            <input
              class="form-input"
              v-model="regForm.username"
              placeholder="请输入用户名（至少3位）"
              @focus="clearRegError('username')"
              @keydown.enter="handleRegister"
            />
            <span class="error-msg" v-if="regErrors.username">{{ regErrors.username }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': regErrors.password }">
            <label class="form-label">
              <span class="label-icon">🔐</span> 密码
            </label>
            <div class="password-wrapper">
              <input
                class="form-input"
                :type="showRegPwd ? 'text' : 'password'"
                v-model="regForm.password"
                placeholder="请输入密码（至少6位）"
                @focus="clearRegError('password')"
                @keydown.enter="handleRegister"
              />
              <button class="pwd-toggle" @click="showRegPwd = !showRegPwd" type="button">
                {{ showRegPwd ? '🙈' : '👁️' }}
              </button>
            </div>
            <span class="error-msg" v-if="regErrors.password">{{ regErrors.password }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': regErrors.confirm }">
            <label class="form-label">
              <span class="label-icon">✅</span> 确认密码
            </label>
            <div class="password-wrapper">
              <input
                class="form-input"
                :type="showRegConfirm ? 'text' : 'password'"
                v-model="regForm.confirm"
                placeholder="请再次输入密码"
                @focus="clearRegError('confirm')"
                @keydown.enter="handleRegister"
              />
              <button class="pwd-toggle" @click="showRegConfirm = !showRegConfirm" type="button">
                {{ showRegConfirm ? '🙈' : '👁️' }}
              </button>
            </div>
            <span class="error-msg" v-if="regErrors.confirm">{{ regErrors.confirm }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': regErrors.email }">
            <label class="form-label">
              <span class="label-icon">📧</span> 邮箱（选填）
            </label>
            <input
              class="form-input"
              v-model="regForm.email"
              placeholder="用于找回密码"
              @focus="clearRegError('email')"
              @keydown.enter="handleRegister"
            />
            <span class="error-msg" v-if="regErrors.email">{{ regErrors.email }}</span>
          </div>
          <button class="submit-btn" @click="handleRegister" :disabled="regLoading">
            <span class="btn-loader" v-if="regLoading"></span>
            <span v-else>
              <svg viewBox="0 0 16 16" width="16" height="16" fill="none" style="vertical-align:middle;margin-right:4px">
                <rect x="2" y="2" width="12" height="12" rx="2" fill="none" stroke="#00ff88" stroke-width="1.5" opacity="0.8"/>
                <line x1="8" y1="5" x2="8" y2="11" stroke="#00ff88" stroke-width="1.5" opacity="0.8"/>
                <line x1="5" y1="8" x2="11" y2="8" stroke="#00ff88" stroke-width="1.5" opacity="0.8"/>
              </svg>
              注册</span>
          </button>
          <div class="form-footer">
            已有账号？
            <button class="link-btn" @click="switchMode('login')">立即登录</button>
          </div>
        </div>

        <!-- ===== 找回密码模式 ===== -->
        <div class="form-container" key="forgot" v-if="mode === 'forgot'">
          <div class="form-title">
            <span class="form-title-icon">🔒</span>
            <span>找回密码</span>
          </div>
          <div class="forgot-desc">
            输入你的用户名和注册时填写的邮箱，我们将重置密码。
          </div>
          <div class="form-group" :class="{ 'has-error': forgotErrors.username }">
            <label class="form-label">
              <span class="label-icon">👤</span> 用户名
            </label>
            <input
              class="form-input"
              v-model="forgotForm.username"
              placeholder="请输入用户名"
              @focus="clearForgotError('username')"
              @keydown.enter="handleForgot"
            />
            <span class="error-msg" v-if="forgotErrors.username">{{ forgotErrors.username }}</span>
          </div>
          <div class="form-group" :class="{ 'has-error': forgotErrors.email }">
            <label class="form-label">
              <span class="label-icon">📧</span> 邮箱
            </label>
            <input
              class="form-input"
              v-model="forgotForm.email"
              placeholder="请输入注册邮箱"
              @focus="clearForgotError('email')"
              @keydown.enter="handleForgot"
            />
            <span class="error-msg" v-if="forgotErrors.email">{{ forgotErrors.email }}</span>
          </div>
          <button class="submit-btn" @click="handleForgot" :disabled="forgotLoading">
            <span class="btn-loader" v-if="forgotLoading"></span>
            <span v-else>📧 发送重置链接</span>
          </button>
          <div class="form-footer">
            <button class="link-btn" @click="switchMode('login')">← 返回登录</button>
          </div>
        </div>
      </transition>

      <!-- 成功/失败提示 -->
      <transition name="toast-fade">
        <div class="toast" :class="toastType" v-if="toastVisible">
          <span class="toast-icon">{{ toastType === 'success' ? '✅' : '❌' }}</span>
          <span class="toast-text">{{ toastMessage }}</span>
        </div>
      </transition>
    </div>

    <!-- 底部信息 -->
    <div class="footer-info">
      <span class="footer-logo">
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none" style="vertical-align:middle;margin-right:2px">
          <path d="M8 14 C5 11 3 8 3 6 C3 3 5 2 8 2 C11 2 13 3 13 6 C13 8 11 11 8 14Z" fill="#00ff88" opacity="0.5"/>
        </svg>
        绿耕智控 v2.0</span>
      <span class="footer-dot">·</span>
      <span>© 2026 All Rights Reserved</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ===== 模式切换 =====
const mode = ref('login')
function switchMode(newMode) {
  mode.value = newMode
  clearAllErrors()
  shakeCard.value = false
}

// ===== 粒子背景 =====
function particleStyle(i) {
  const size = 2 + Math.random() * 4
  const left = Math.random() * 100
  const delay = Math.random() * 8
  const duration = 6 + Math.random() * 8
  const opacity = 0.2 + Math.random() * 0.5
  return {
    width: size + 'px',
    height: size + 'px',
    left: left + '%',
    bottom: '-10px',
    animationDelay: delay + 's',
    animationDuration: duration + 's',
    opacity,
    background: Math.random() > 0.5 ? '#00ff88' : '#00d4ff',
    boxShadow: `0 0 ${size * 2}px ${Math.random() > 0.5 ? '#00ff88' : '#00d4ff'}`
  }
}

// ===== 浮动叶子 =====
function leafStyle(i) {
  const left = 5 + (i - 1) * 18 + Math.random() * 8
  const delay = (i - 1) * 2 + Math.random() * 2
  const duration = 10 + Math.random() * 8
  const size = 18 + Math.random() * 14
  return {
    left: left + '%',
    animationDelay: delay + 's',
    animationDuration: duration + 's',
    fontSize: size + 'px'
  }
}

// ===== 登录表单 =====
const loginForm = reactive({ username: '', password: '', remember: false })
const loginErrors = reactive({ username: '', password: '' })
const loginLoading = ref(false)
const showLoginPwd = ref(false)

function clearLoginError(field) { loginErrors[field] = '' }

function validateLogin() {
  let valid = true
  if (!loginForm.username.trim()) {
    loginErrors.username = '请输入用户名'
    valid = false
  }
  if (!loginForm.password) {
    loginErrors.password = '请输入密码'
    valid = false
  }
  return valid
}

function handleLogin() {
  if (!validateLogin()) return
  loginLoading.value = true

  fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: loginForm.username.trim(), password: loginForm.password })
  })
  .then(r => r.json())
  .then(data => {
    loginLoading.value = false
    if (!data.success) {
      if (data.error.includes('不存在')) loginErrors.username = data.error
      else loginErrors.password = data.error
      triggerShake()
      return
    }
    localStorage.setItem('greenhouse_current_user', JSON.stringify({
      username: data.user.username,
      email: data.user.email || '',
      loginTime: new Date().toISOString()
    }))
    showToast('登录成功！欢迎回来', 'success')
    setTimeout(() => router.push('/'), 800)
  })
  .catch(() => {
    loginLoading.value = false
    showToast('网络错误，请稍后重试', 'error')
  })
}

// ===== 注册表单 =====
const regForm = reactive({ username: '', password: '', confirm: '', email: '' })
const regErrors = reactive({ username: '', password: '', confirm: '', email: '' })
const regLoading = ref(false)
const showRegPwd = ref(false)
const showRegConfirm = ref(false)

function clearRegError(field) { regErrors[field] = '' }

function validateRegister() {
  let valid = true
  if (!regForm.username.trim() || regForm.username.trim().length < 3) {
    regErrors.username = '用户名至少3位'
    valid = false
  }
  if (!regForm.password || regForm.password.length < 6) {
    regErrors.password = '密码至少6位'
    valid = false
  }
  if (regForm.password !== regForm.confirm) {
    regErrors.confirm = '两次密码不一致'
    valid = false
  }
  if (regForm.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regForm.email)) {
    regErrors.email = '邮箱格式不正确'
    valid = false
  }
  return valid
}

function handleRegister() {
  if (!validateRegister()) return
  regLoading.value = true

  fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: regForm.username.trim(),
      password: regForm.password,
      email: regForm.email.trim()
    })
  })
  .then(r => r.json())
  .then(data => {
    regLoading.value = false
    if (!data.success) {
      regErrors.username = data.error || '注册失败'
      triggerShake()
      return
    }
    showToast('注册成功！请登录', 'success')
    regForm.username = ''; regForm.password = ''; regForm.confirm = ''; regForm.email = ''
    setTimeout(() => { mode.value = 'login' }, 1000)
  })
  .catch(() => {
    regLoading.value = false
    showToast('网络错误，请稍后重试', 'error')
  })
}

// ===== 找回密码 =====
const forgotForm = reactive({ username: '', email: '' })
const forgotErrors = reactive({ username: '', email: '' })
const forgotLoading = ref(false)

function clearForgotError(field) { forgotErrors[field] = '' }

function validateForgot() {
  let valid = true
  if (!forgotForm.username.trim()) {
    forgotErrors.username = '请输入用户名'
    valid = false
  }
  if (!forgotForm.email.trim()) {
    forgotErrors.email = '请输入邮箱'
    valid = false
  }
  return valid
}

function handleForgot() {
  if (!validateForgot()) return
  forgotLoading.value = true

  fetch('/api/auth/forgot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: forgotForm.username.trim(), email: forgotForm.email.trim() })
  })
  .then(r => r.json())
  .then(data => {
    forgotLoading.value = false
    if (!data.success) {
      if (data.error.includes('不存在')) forgotErrors.username = data.error
      else forgotErrors.email = data.error
      triggerShake()
      return
    }
    showToast('密码已重置为 123456，请登录后修改', 'success')
    forgotForm.username = ''; forgotForm.email = ''
    setTimeout(() => { mode.value = 'login' }, 1500)
  })
  .catch(() => {
    forgotLoading.value = false
    showToast('网络错误，请稍后重试', 'error')
  })
}

// ===== 通用工具 =====
const shakeCard = ref(false)
const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

function triggerShake() {
  shakeCard.value = true
  setTimeout(() => { shakeCard.value = false }, 500)
}

function showToast(msg, type) {
  toastMessage.value = msg
  toastType.value = type
  toastVisible.value = true
  setTimeout(() => { toastVisible.value = false }, 3000)
}

function clearAllErrors() {
  Object.keys(loginErrors).forEach(k => loginErrors[k] = '')
  Object.keys(regErrors).forEach(k => regErrors[k] = '')
  Object.keys(forgotErrors).forEach(k => forgotErrors[k] = '')
}

// 如果已登录，直接跳转首页
onMounted(() => {
  const currentUser = localStorage.getItem('greenhouse_current_user')
  if (currentUser) {
    router.push('/')
  }
})
</script>

<style scoped>
/* ===== 页面容器 ===== */
.login-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #0a0e1a;
  padding: 20px;
  z-index: 1000;
}

/* ===== 粒子背景 ===== */
.particles {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.particle {
  position: absolute;
  border-radius: 50%;
  animation: particleRise linear infinite;
}

@keyframes particleRise {
  0% {
    transform: translateY(0) translateX(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 0.6;
  }
  100% {
    transform: translateY(-100vh) translateX(30px) scale(0.3);
    opacity: 0;
  }
}

/* ===== 浮动叶子 ===== */
.floating-leaves {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.leaf {
  position: absolute;
  top: -40px;
  animation: leafFall linear infinite;
  opacity: 0.15;
  filter: drop-shadow(0 0 4px rgba(0, 255, 136, 0.3));
}

@keyframes leafFall {
  0% {
    transform: translateY(0) rotate(0deg) scale(0.8);
    opacity: 0;
  }
  10% {
    opacity: 0.2;
  }
  90% {
    opacity: 0.1;
  }
  100% {
    transform: translateY(100vh) rotate(720deg) scale(1.2);
    opacity: 0;
  }
}

/* ===== 顶部品牌 ===== */
.header-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 30px;
  z-index: 1;
  position: relative;
  animation: brandFadeIn 1s ease-out;
}

@keyframes brandFadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.brand-icon {
  font-size: 48px;
  animation: brandPulse 3s ease-in-out infinite;
  filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.4));
}

@keyframes brandPulse {
  0%, 100% { transform: scale(1); filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.4)); }
  50% { transform: scale(1.08); filter: drop-shadow(0 0 30px rgba(0, 255, 136, 0.6)); }
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 26px;
  font-weight: 800;
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
}

.brand-subtitle {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.4);
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-top: 2px;
}

/* ===== 登录卡片 ===== */
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  background: rgba(15, 20, 40, 0.85);
  border: 1px solid rgba(0, 255, 136, 0.15);
  border-radius: 20px;
  padding: 32px 28px 28px;
  backdrop-filter: blur(20px);
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(0, 255, 136, 0.08),
    0 0 60px rgba(0, 255, 136, 0.03);
  animation: cardEntry 0.8s ease-out;
  overflow: hidden;
}

@keyframes cardEntry {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.login-card.shake {
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-6px); }
  20%, 40%, 60%, 80% { transform: translateX(6px); }
}

/* 装饰光晕 */
.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    ellipse at 30% 20%,
    rgba(0, 255, 136, 0.03) 0%,
    transparent 60%
  );
  pointer-events: none;
  animation: glowRotate 12s linear infinite;
}

@keyframes glowRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== 标签栏 ===== */
.tab-bar {
  display: flex;
  background: rgba(0, 255, 136, 0.04);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 24px;
  border: 1px solid rgba(0, 255, 136, 0.06);
  position: relative;
  z-index: 1;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 8px;
  background: transparent;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(200, 214, 229, 0.4);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.tab-btn:hover {
  color: rgba(200, 214, 229, 0.7);
}

.tab-btn.active {
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  box-shadow: 0 0 16px rgba(0, 255, 136, 0.08);
}

.tab-icon-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
}

.tab-icon-tab svg {
  width: 16px;
  height: 16px;
  opacity: 0.8;
  transition: opacity 0.3s;
}

.tab-btn.active .tab-icon-tab svg {
  opacity: 1;
  filter: drop-shadow(0 0 4px rgba(0, 255, 136, 0.4));
}

/* ===== 表单容器 ===== */
.form-container {
  position: relative;
  z-index: 1;
}

/* 过渡动画 */
.form-fade-enter-active {
  animation: formIn 0.35s ease-out;
}
.form-fade-leave-active {
  animation: formOut 0.25s ease-in;
}

@keyframes formIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes formOut {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(-20px);
  }
}

.form-title {
  font-size: 20px;
  font-weight: 700;
  color: #c8d6e5;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-title-icon {
  font-size: 22px;
}

/* ===== 表单组 ===== */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(200, 214, 229, 0.7);
  margin-bottom: 6px;
}

.label-icon {
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(0, 255, 136, 0.03);
  border: 1px solid rgba(0, 255, 136, 0.12);
  border-radius: 10px;
  font-size: 14px;
  color: #c8d6e5;
  outline: none;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #00ff88;
  box-shadow: 0 0 16px rgba(0, 255, 136, 0.1), inset 0 0 16px rgba(0, 255, 136, 0.03);
  background: rgba(0, 255, 136, 0.06);
}

.form-input::placeholder {
  color: rgba(200, 214, 229, 0.2);
}

.has-error .form-input {
  border-color: #ff4757;
  box-shadow: 0 0 12px rgba(255, 71, 87, 0.1);
}

.error-msg {
  display: block;
  font-size: 12px;
  color: #ff4757;
  margin-top: 4px;
  padding-left: 4px;
  animation: errorSlideIn 0.2s ease-out;
}

@keyframes errorSlideIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ===== 密码切换 ===== */
.password-wrapper {
  position: relative;
}

.password-wrapper .form-input {
  padding-right: 44px;
}

.pwd-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.pwd-toggle:hover {
  opacity: 1;
}

/* ===== 表单选项 ===== */
.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.remember-me {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(200, 214, 229, 0.5);
  cursor: pointer;
  user-select: none;
}

.remember-me input {
  display: none;
}

.checkmark {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(0, 255, 136, 0.2);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  position: relative;
}

.remember-me input:checked + .checkmark {
  background: rgba(0, 255, 136, 0.15);
  border-color: #00ff88;
}

.remember-me input:checked + .checkmark::after {
  content: '✓';
  color: #00ff88;
  font-size: 12px;
  font-weight: 700;
}

/* ===== 链接按钮 ===== */
.link-btn {
  background: none;
  border: none;
  color: #00d4ff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  padding: 2px 4px;
}

.link-btn:hover {
  color: #00ff88;
  text-shadow: 0 0 8px rgba(0, 255, 136, 0.3);
}

/* ===== 提交按钮 ===== */
.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, rgba(0, 255, 136, 0.15), rgba(0, 212, 255, 0.1));
  border: 1px solid rgba(0, 255, 136, 0.25);
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  color: #00ff88;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  position: relative;
  overflow: hidden;
}

.submit-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.submit-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.submit-btn:hover:not(:disabled) {
  border-color: rgba(0, 255, 136, 0.5);
  box-shadow: 0 0 24px rgba(0, 255, 136, 0.15), inset 0 0 20px rgba(0, 255, 136, 0.05);
  transform: translateY(-1px);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载旋转器 */
.btn-loader {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(0, 255, 136, 0.2);
  border-top-color: #00ff88;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 表单底部 ===== */
.form-footer {
  text-align: center;
  font-size: 13px;
  color: rgba(200, 214, 229, 0.4);
  margin-top: 16px;
}

/* ===== 找回密码说明 ===== */
.forgot-desc {
  font-size: 13px;
  color: rgba(200, 214, 229, 0.5);
  margin-bottom: 16px;
  padding: 10px 12px;
  background: rgba(0, 212, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.08);
  border-radius: 8px;
  line-height: 1.5;
}

/* ===== Toast 提示 ===== */
.toast {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  z-index: 10;
  white-space: nowrap;
}

.toast.success {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.2);
  color: #00ff88;
  box-shadow: 0 4px 20px rgba(0, 255, 136, 0.1);
}

.toast.error {
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid rgba(255, 71, 87, 0.2);
  color: #ff4757;
  box-shadow: 0 4px 20px rgba(255, 71, 87, 0.1);
}

.toast-fade-enter-active {
  animation: toastIn 0.3s ease-out;
}
.toast-fade-leave-active {
  animation: toastOut 0.3s ease-in;
}

@keyframes toastIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes toastOut {
  from {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  to {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
}

/* ===== 底部信息 ===== */
.footer-info {
  position: fixed;
  bottom: 16px;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(200, 214, 229, 0.2);
  animation: footerFadeIn 1.5s ease-out;
}

@keyframes footerFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.footer-dot {
  opacity: 0.3;
}

/* ===== 响应式 ===== */
@media (max-width: 480px) {
  .login-card {
    padding: 24px 18px 20px;
    border-radius: 16px;
  }

  .brand-icon {
    font-size: 36px;
  }

  .brand-title {
    font-size: 20px;
  }

  .tab-btn {
    font-size: 12px;
    padding: 8px 6px;
  }

  .tab-icon-tab {
    width: 16px;
    height: 16px;
  }

  .tab-icon-tab svg {
    width: 14px;
    height: 14px;
  }

  .form-title {
    font-size: 18px;
  }

  .form-input {
    padding: 10px 12px;
    font-size: 13px;
  }

  .submit-btn {
    padding: 12px;
    font-size: 14px;
  }

  .header-brand {
    margin-bottom: 20px;
  }

  .toast {
    font-size: 12px;
    padding: 8px 14px;
  }
}
</style>