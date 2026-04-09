<template>
  <div class="login-page">
    <!-- 背景图 + 暗色遮罩 -->
    <div class="bg-layer">
      <div class="bg-img"></div>
      <div class="bg-overlay"></div>
    </div>

    <!-- 居中玻璃卡片 -->
    <div class="card-wrap">
      <div class="glass-card">
        <!-- 头部 -->
        <div class="card-header">
          <div class="brand">
            <div class="brand-icon">
              <el-icon :size="18"><TrendCharts /></el-icon>
            </div>
            <h1 class="brand-title">舆情分析系统</h1>
          </div>
          <div class="header-badge">
            <el-icon :size="14"><DataAnalysis /></el-icon>
          </div>
        </div>

        <!-- 全局消息提示 -->
        <transition name="msg-fade">
          <div
            v-if="msgVisible"
            class="msg-banner"
            :class="{ 'msg-error': msgIsError, 'msg-success': !msgIsError, 'error-shake': msgShake }"
          >
            {{ msgText }}
          </div>
        </transition>

        <!-- 登录方式切换 -->
        <div class="login-tabs">
          <div
            class="tab-item"
            :class="{ active: loginType === 'password' }"
            @click="loginType = 'password'"
          >
            <el-icon :size="14"><Lock /></el-icon>
            <span>密码登录</span>
          </div>
          <div
            class="tab-item"
            :class="{ active: loginType === 'email' }"
            @click="loginType = 'email'"
          >
            <el-icon :size="14"><Message /></el-icon>
            <span>邮箱验证码</span>
          </div>
        </div>

        <!-- ======== 密码登录表单 ======== -->
        <el-form
          v-show="loginType === 'password'"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          @keyup.enter="handleLogin"
          class="login-form"
        >
          <el-form-item prop="username">
            <label class="glass-label">账号 <span class="label-hint">(学号/手机/邮箱)</span></label>
            <el-input
              v-model="loginForm.username"
              placeholder="例如: admin / 20240001"
              :prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <label class="glass-label">密码</label>
            <el-input
              v-model="loginForm.password"
              :type="passwordVisible ? 'text' : 'password'"
              placeholder="6-16位字符"
              :prefix-icon="Lock"
              size="large"
              @input="onPasswordInput"
            >
              <template #suffix>
                <el-icon class="pwd-eye" @click="passwordVisible = !passwordVisible">
                  <View v-if="passwordVisible" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
            <!-- 密码强度指示器 -->
            <div class="strength-row">
              <div class="strength-bars">
                <div class="strength-seg" :class="pwdStrength >= 1 ? `str-${pwdStrength}` : ''"></div>
                <div class="strength-seg" :class="pwdStrength >= 2 ? `str-${pwdStrength}` : ''"></div>
                <div class="strength-seg" :class="pwdStrength >= 3 ? `str-${pwdStrength}` : ''"></div>
              </div>
              <span v-if="pwdStrength > 0" class="strength-text">
                {{ ['弱', '一般', '强'][pwdStrength - 1] }}
              </span>
            </div>
          </el-form-item>

          <div class="form-options">
            <el-checkbox v-model="loginForm.rememberMe">记住密码</el-checkbox>
            <div class="options-right">
              <a class="glass-link" @click="goToForgotPassword">忘记密码?</a>
              <a class="glass-link" @click="showMsg('请联系管理员 admin@weibo-sa.com', false)">联系管理员</a>
            </div>
          </div>

          <button
            type="button"
            class="btn-primary"
            :disabled="loading"
            @click="handleLogin"
          >
            <template v-if="!loading">
              <el-icon :size="16"><Right /></el-icon>
              <span>登录系统</span>
            </template>
            <span v-else class="btn-loading">
              <i class="spinner"></i> 登录中...
            </span>
          </button>
        </el-form>

        <!-- ======== 邮箱验证码登录表单 ======== -->
        <el-form
          v-show="loginType === 'email'"
          ref="emailFormRef"
          :model="emailForm"
          :rules="emailRules"
          @keyup.enter="handleEmailLogin"
          class="login-form"
        >
          <el-form-item prop="email">
            <label class="glass-label">邮箱</label>
            <el-input
              v-model="emailForm.email"
              placeholder="请输入邮箱地址"
              :prefix-icon="Message"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item prop="code">
            <label class="glass-label">验证码</label>
            <div class="code-row">
              <el-input
                v-model="emailForm.code"
                placeholder="6位验证码"
                :prefix-icon="Key"
                size="large"
                maxlength="6"
              />
              <button
                type="button"
                class="btn-code"
                :disabled="countdown > 0 || sendingCode"
                @click="sendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </div>
          </el-form-item>

          <button
            type="button"
            class="btn-primary"
            :disabled="loading"
            @click="handleEmailLogin"
          >
            <template v-if="!loading">
              <el-icon :size="16"><Right /></el-icon>
              <span>登录系统</span>
            </template>
            <span v-else class="btn-loading">
              <i class="spinner"></i> 登录中...
            </span>
          </button>
        </el-form>

        <!-- 演示账号提示 -->
        <div class="demo-tip">
          <span v-if="loginType === 'password'">演示账号: <strong>admin</strong> / <strong>admin123</strong></span>
          <span v-else>输入任意邮箱，验证码显示在后端控制台</span>
        </div>

        <!-- 底部 -->
        <div class="card-footer">
          <div class="footer-links">
            <span>还没有账号?</span>
            <a class="glass-link" @click="goToRegister">立即注册</a>
          </div>
          <p class="copyright">毕业设计 · 罗森 · 2022407443</p>
        </div>
      </div>

      <!-- 技术标签 -->
      <div class="tech-tags">
        <span>Vue 3</span>
        <span>Flask</span>
        <span>Spark</span>
        <span>ChineseBERT</span>
        <span>ECharts</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { User, Lock, View, Hide, DataAnalysis, TrendCharts, Histogram, Cpu, Message, Key, Right } from '@element-plus/icons-vue';
import apiClient from '@/api/index';
import { useAuthStore } from '@/store/auth';

const router = useRouter();
const authStore = useAuthStore();

// 登录方式
const loginType = ref<'password' | 'email'>('password');

// 表单状态
const loginFormRef = ref<FormInstance>();
const emailFormRef = ref<FormInstance>();
const loading = ref(false);
const passwordVisible = ref(false);

// ---- 密码强度 ----
const pwdStrength = ref(0);
const onPasswordInput = (val: string) => {
  let s = 0;
  if (val.length >= 6) s++;
  if (val.length >= 10) s++;
  if (/[A-Z]/.test(val) && /[0-9]/.test(val) && /[a-z]/.test(val)) s++;
  if (val.length >= 12 && /[^A-Za-z0-9]/.test(val)) s = Math.min(s + 1, 3);
  pwdStrength.value = Math.min(s, 3);
};

// ---- 全局消息横幅 ----
const msgVisible = ref(false);
const msgText = ref('');
const msgIsError = ref(true);
const msgShake = ref(false);
let msgTimer: number | null = null;

const showMsg = (text: string, isError = true) => {
  msgText.value = text;
  msgIsError.value = isError;
  msgVisible.value = true;
  msgShake.value = isError;
  setTimeout(() => { msgShake.value = false; }, 400);
  if (msgTimer) clearTimeout(msgTimer);
  msgTimer = window.setTimeout(() => { msgVisible.value = false; }, 3500);
};

// ---- 记住密码 localStorage ----
const STORAGE_KEY = 'weibo_sa_login';
const loadSavedCredentials = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const data = JSON.parse(saved);
      if (data.remember) {
        loginForm.username = data.username || '';
        loginForm.password = data.password || '';
        loginForm.rememberMe = true;
        onPasswordInput(loginForm.password);
      }
    }
  } catch { /* ignore */ }
};
const saveCredentials = () => {
  if (loginForm.rememberMe) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      username: loginForm.username,
      password: loginForm.password,
      remember: true
    }));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
};

onMounted(() => {
  loadSavedCredentials();
});

// 密码登录表单
const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
});

// 邮箱验证码表单
const emailForm = reactive({
  email: '',
  code: ''
});

// 验证码相关
const sendingCode = ref(false);
const countdown = ref(0);
let countdownTimer: number | null = null;

// 密码登录验证规则
const loginRules = reactive<FormRules>({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 5, message: '密码长度不能少于5位', trigger: 'blur' }
  ],
});

// 邮箱验证码验证规则
const emailRules = reactive<FormRules>({
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ],
});

// 发送验证码
const sendCode = async () => {
  // 先验证邮箱
  try {
    await emailFormRef.value?.validateField('email');
  } catch {
    return;
  }
  
  sendingCode.value = true;
  try {
    const response = await apiClient.post('/auth/send-code', {
      email: emailForm.email
    });
    
    if (response.data.code === 200) {
      ElMessage.success(response.data.message);
      
      // 开发环境显示验证码
      if (response.data.data?.debug_code) {
        ElMessage.info(`验证码: ${response.data.data.debug_code}`, { duration: 10000 });
      }
      
      // 开始倒计时
      countdown.value = 60;
      countdownTimer = window.setInterval(() => {
        countdown.value--;
        if (countdown.value <= 0) {
          if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
          }
        }
      }, 1000);
    } else {
      ElMessage.error(response.data.message || '发送失败');
    }
  } catch (error: any) {
    const msg = error.response?.data?.message || '发送验证码失败';
    ElMessage.error(msg);
  } finally {
    sendingCode.value = false;
  }
};

// 密码登录处理
const handleLogin = () => {
  loginFormRef.value?.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      
      try {
        const response = await apiClient.post('/auth/login', {
          username: loginForm.username,
          password: loginForm.password
        });
        
        if (response.data.code === 200) {
          showMsg('登录成功，正在跳转...', false);
          saveCredentials();
          
          const userData = response.data.data;
          authStore.setToken(userData.accessToken);
          authStore.setUser(userData.user);
          localStorage.setItem('isLoggedIn', 'true');
          localStorage.setItem('username', userData.user.username);
          localStorage.setItem('userRole', userData.user.role);
          localStorage.setItem('accessToken', userData.accessToken);
          
          setTimeout(() => router.push('/dashboard'), 600);
        } else {
          showMsg(response.data.message || '登录失败', true);
        }
      } catch (error: any) {
        const msg = error.response?.data?.message || '账号或密码错误，请重试';
        showMsg(msg, true);
      } finally {
        loading.value = false;
      }
    }
  });
};

// 邮箱验证码登录处理
const handleEmailLogin = () => {
  emailFormRef.value?.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      
      try {
        const response = await apiClient.post('/auth/login-by-code', {
          email: emailForm.email,
          code: emailForm.code
        });
        
        if (response.data.code === 200) {
          showMsg('登录成功，正在跳转...', false);
          
          const userData = response.data.data;
          authStore.setToken(userData.accessToken);
          authStore.setUser(userData.user);
          localStorage.setItem('isLoggedIn', 'true');
          localStorage.setItem('username', userData.user.username);
          localStorage.setItem('userEmail', userData.user.email);
          localStorage.setItem('userRole', userData.user.role);
          localStorage.setItem('accessToken', userData.accessToken);
          localStorage.setItem('loginType', 'email');
          
          setTimeout(() => router.push('/dashboard'), 600);
        } else {
          showMsg(response.data.message || '登录失败', true);
        }
      } catch (error: any) {
        const msg = error.response?.data?.message || '验证码错误';
        showMsg(msg, true);
      } finally {
        loading.value = false;
      }
    }
  });
};

// 跳转注册
const goToRegister = () => {
  router.push('/register');
};

// 跳转忘记密码
const goToForgotPassword = () => {
  router.push('/forgot-password');
};

// 清理定时器
onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
  }
});
</script>

<style scoped lang="scss">
/* ============================================================
   Glassmorphism Login — v2 (background image + strength bar)
   ============================================================ */
.login-page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  overflow: auto;
  background: #0a0f2a;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ---------- background image + overlay ---------- */
.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.bg-img {
  width: 100%; height: 100%;
  background:
    url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1920&q=80') center/cover no-repeat,
    linear-gradient(135deg, #0f0c29, #302b63, #24243e);
}

.bg-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
}

/* ---------- card wrapper ---------- */
.card-wrap {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
}

/* ---------- glass card ---------- */
.glass-card {
  width: 100%;
  max-width: 430px;
  padding: 32px 28px 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 25px 45px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(255,255,255,0.08);
  color: #fff;
  animation: fadeUp 0.5s ease-out;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ---------- card header ---------- */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 34px; height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ec4899, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
}

.brand-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0.3px;
}

.header-badge {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.65);
}

/* ---------- message banner ---------- */
.msg-banner {
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  text-align: center;
  backdrop-filter: blur(8px);
  transition: all 0.3s;
}

.msg-error {
  background: rgba(239, 68, 68, 0.3);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.msg-success {
  background: rgba(34, 197, 94, 0.3);
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.error-shake {
  animation: shake 0.3s ease-in-out 0s 2;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25%      { transform: translateX(-5px); }
  75%      { transform: translateX(5px); }
}

.msg-fade-enter-active,
.msg-fade-leave-active {
  transition: all 0.3s ease;
}
.msg-fade-enter-from,
.msg-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ---------- login tabs ---------- */
.login-tabs {
  display: flex;
  margin-bottom: 22px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.15);

  .tab-item {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 0;
    cursor: pointer;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.05);
    transition: all 0.3s;
    user-select: none;

    &:hover { color: #fff; background: rgba(255, 255, 255, 0.1); }

    &.active {
      color: #fff;
      background: linear-gradient(135deg, #165DFF 0%, #0F48C9 100%);
    }
  }
}

/* ---------- form ---------- */
.login-form {
  .el-form-item {
    margin-bottom: 20px;
  }

  :deep(.el-form-item__label) {
    display: none;
  }

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.18);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 10px;
    box-shadow: none;
    padding: 4px 14px;
    transition: all 0.2s;

    &:hover {
      border-color: rgba(255, 255, 255, 0.35);
    }

    &.is-focus {
      background: rgba(255, 255, 255, 0.25);
      border-color: #165DFF;
      box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.25);
      transform: scale(1.01);
    }
  }

  :deep(.el-input__inner) {
    height: 42px;
    color: #fff;
    font-size: 14px;

    &::placeholder { color: rgba(255, 255, 255, 0.5); }
  }

  :deep(.el-input__prefix .el-icon) {
    color: rgba(255, 255, 255, 0.5);
  }
  :deep(.el-input__suffix .el-icon) {
    color: rgba(255, 255, 255, 0.5);
  }

  :deep(.el-form-item__error) {
    color: #fca5a5;
  }
}

.glass-label {
  display: block;
  font-size: 15px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 8px;
}

.label-hint {
  font-size: 12px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.5);
}

.pwd-eye {
  cursor: pointer;
  &:hover { color: rgba(255, 255, 255, 0.9) !important; }
}

/* ---------- password strength ---------- */
.strength-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.strength-bars {
  display: flex;
  gap: 4px;
  flex: 1;
}

.strength-seg {
  height: 4px;
  flex: 1;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.15);
  transition: background 0.25s;
}

.strength-seg.str-1 { background: #f87171; }
.strength-seg.str-2 { background: #fbbf24; }
.strength-seg.str-3 { background: #34d399; }

.strength-text {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  flex-shrink: 0;
  min-width: 24px;
}

/* ---------- form options ---------- */
.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 6px;

  :deep(.el-checkbox__label) {
    color: rgba(255, 255, 255, 0.7);
    font-size: 13px;
  }

  :deep(.el-checkbox__inner) {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.5);
    border-radius: 4px;
  }

  :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
    background: #165DFF;
    border-color: #165DFF;
  }
}

.options-right {
  display: flex;
  gap: 12px;
}

.glass-link {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
  text-decoration: none;

  &:hover { color: #fff; }
}

/* ---------- primary button ---------- */
.btn-primary {
  width: 100%;
  padding: 13px 0;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #165DFF 0%, #0F48C9 100%);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  position: relative;
  overflow: hidden;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px -5px rgba(22, 93, 255, 0.5);
  }

  &:active:not(:disabled) {
    transform: translateY(1px);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
}

.btn-loading {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---------- code row ---------- */
.code-row {
  display: flex;
  gap: 10px;
  width: 100%;

  .el-input { flex: 1; }
}

.btn-code {
  flex-shrink: 0;
  width: 110px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.22);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

/* ---------- demo tip ---------- */
.demo-tip {
  margin-top: 18px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  text-align: center;

  strong {
    color: #60a5fa;
    font-weight: 600;
  }
}

/* ---------- card footer ---------- */
.card-footer {
  margin-top: 18px;
  text-align: center;
}

.footer-links {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);

  .glass-link {
    margin-left: 4px;
    color: #60a5fa;
    font-weight: 500;

    &:hover { color: #93c5fd; }
  }
}

.copyright {
  margin: 10px 0 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.25);
}

/* ---------- tech tags ---------- */
.tech-tags {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  flex-wrap: wrap;
  justify-content: center;

  span {
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.55);
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(6px);
  }
}

/* ---------- responsive ---------- */
@media (max-width: 480px) {
  .glass-card {
    padding: 24px 18px 20px;
  }

  .brand-title { font-size: 18px; }

  .tech-tags { display: none; }

  .options-right { gap: 8px; }
}
</style>
