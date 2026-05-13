<template>
  <div class="login-page">
    <!-- 左侧品牌区 (与注册页一致) -->
    <div class="brand-section">
      <div class="brand-content">
        <MascotEyes class="mascot-brand" />
        <h1 class="brand-title">微博舆情分析系统</h1>
        <p class="brand-subtitle">Weibo Sentiment Analysis Platform</p>

        <div class="features-list">
          <div class="feature-item">
            <el-icon><DataAnalysis /></el-icon>
            <span>情感-热度双维度分析</span>
          </div>
          <div class="feature-item">
            <el-icon><TrendCharts /></el-icon>
            <span>实时舆情监控预警</span>
          </div>
          <div class="feature-item">
            <el-icon><Histogram /></el-icon>
            <span>大数据可视化展示</span>
          </div>
          <div class="feature-item">
            <el-icon><Cpu /></el-icon>
            <span>Spark分布式处理</span>
          </div>
        </div>

        <!-- 底部技术标签 -->
        <div class="tech-tags">
          <span>Vue 3</span>
          <span>Flask</span>
          <span>Spark</span>
          <span>ChineseBERT</span>
          <span>ECharts</span>
        </div>
      </div>

      <!-- 背景装饰 -->
      <div class="bg-decoration">
        <div class="circle circle-1"></div>
        <div class="circle circle-2"></div>
        <div class="circle circle-3"></div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-section">
      <div class="login-box">
        <div class="login-header">
          <h2>欢迎回来</h2>
          <p class="login-desc">请登录以使用舆情分析系统</p>
        </div>

        <!-- 消息提示横栏 -->
        <transition name="msg-fade">
          <div
            v-if="msgVisible"
            class="msg-banner"
            :class="{ 'msg-error': msgIsError, 'msg-success': !msgIsError, 'error-shake': msgShake }"
          >
            {{ msgText }}
          </div>
        </transition>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="login-form"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="账号　学号 / 手机 / 邮箱　(例: admin)"
              :prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              :type="passwordVisible ? 'text' : 'password'"
              placeholder="密码　(6-16位字符)"
              :prefix-icon="Lock"
              size="large"
              @input="onPasswordInput"
            >
              <template #suffix>
                <el-icon class="password-toggle" @click="passwordVisible = !passwordVisible">
                  <View v-if="passwordVisible" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
            <!-- 密码强度 -->
            <div class="strength-row" v-if="loginForm.password">
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
            <el-link type="primary" :underline="false" @click="showMsg('请联系管理员', false)">联系管理员</el-link>
          </div>

          <el-button
            type="primary"
            :loading="loading"
            class="login-button"
            size="large"
            @click="handleLogin"
          >
            <span v-if="!loading">登 录</span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form>

        <!-- 演示账号 -->
        <div class="demo-tip">
          <div class="demo-row">管理员：<strong>admin</strong> / <strong>admin123</strong></div>
          <div class="demo-row">普通用户：<strong>user01</strong> / <strong>user123</strong></div>
        </div>

        <div class="register-link">
          <span>还没有账号？</span>
          <el-link type="primary" :underline="false" @click="goToRegister">立即注册</el-link>
        </div>

        <div class="login-footer">
          <p>本科毕业设计 · 微博舆情分析系统</p>
          <p class="copyright">© 2026 罗森 · 学号 2022407443</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { User, Lock, View, Hide, DataAnalysis, TrendCharts, Histogram, Cpu } from '@element-plus/icons-vue';
import apiClient from '@/api/index';
import { useAuthStore } from '@/store/auth';
import MascotEyes from '@/components/MascotEyes.vue';

const router = useRouter();
const authStore = useAuthStore();

// 表单状态
const loginFormRef = ref<FormInstance>();
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

// 密码登录验证规则
const loginRules = reactive<FormRules>({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 5, message: '密码长度不能少于5位', trigger: 'blur' }
  ],
});

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

// 跳转注册
const goToRegister = () => {
  router.push('/register');
};

</script>

<style scoped lang="scss">
/* ============================================================
   Login Page - 与 Register.vue 同款左右分栏 (统一品牌)
   ============================================================ */
.login-page {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

// ---------- 左侧品牌区域 ----------
.brand-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  padding: 40px;

  .brand-content {
    position: relative;
    z-index: 2;
    text-align: center;
    color: white;
    max-width: 500px;
  }

  .mascot-brand {
    width: 260px;
    margin: 0 auto 20px;
    display: block;
    filter: drop-shadow(0 6px 24px rgba(0, 0, 0, 0.25));
  }

  .brand-title {
    font-size: 28px;
    font-weight: 700;
    margin: 0 0 8px 0;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  }

  .brand-subtitle {
    font-size: 14px;
    opacity: 0.9;
    margin: 0 0 32px 0;
    letter-spacing: 1px;
  }

  .features-list {
    text-align: left;
    margin-bottom: 24px;

    .feature-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      margin-bottom: 6px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      backdrop-filter: blur(10px);
      transition: all 0.3s;

      &:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateX(5px);
      }

      .el-icon {
        font-size: 18px;
      }

      span {
        font-size: 14px;
      }
    }
  }

  .tech-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 12px;

    span {
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.85);
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(6px);
    }
  }
}

// ---------- 背景动态圆 ----------
.bg-decoration {
  position: absolute;
  inset: 0;
  overflow: hidden;

  .circle {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
  }
  .circle-1 { width: 400px; height: 400px; top: -100px; left: -100px; animation: pulse 4s ease-in-out infinite; }
  .circle-2 { width: 300px; height: 300px; bottom: -50px; right: -50px; animation: pulse 5s ease-in-out infinite 1s; }
  .circle-3 { width: 200px; height: 200px; top: 50%; left: 50%; transform: translate(-50%, -50%); animation: pulse 6s ease-in-out infinite 2s; }
}

// ---------- 右侧登录区 ----------
.login-section {
  width: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: white;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
}

.login-box {
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;

  h2 {
    font-size: 26px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px 0;
  }

  .login-desc {
    color: var(--color-text-secondary, #909399);
    font-size: 14px;
    margin: 0;
  }
}

// ---------- 消息横幅 ----------
.msg-banner {
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
}
.msg-error   { background: #fef0f0; color: #f56c6c; border: 1px solid #fde2e2; }
.msg-success { background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8; }
.error-shake { animation: shake 0.3s ease-in-out 0s 2; }
.msg-fade-enter-active, .msg-fade-leave-active { transition: all 0.3s ease; }
.msg-fade-enter-from, .msg-fade-leave-to { opacity: 0; transform: translateY(-8px); }

// ---------- 表单 ----------
.login-form {
  .el-form-item {
    margin-bottom: 18px;
  }

  :deep(.el-input__wrapper) {
    padding: 4px 15px;
    border-radius: 8px;

    &:hover, &.is-focus {
      box-shadow: 0 0 0 1px #667eea inset;
    }
  }

  :deep(.el-input__inner) {
    height: 42px;
  }

  .password-toggle {
    cursor: pointer;
    color: var(--color-text-secondary, #909399);

    &:hover {
      color: #667eea;
    }
  }
}

// ---------- 密码强度条 ----------
.strength-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.strength-bars { display: flex; gap: 4px; flex: 1; }
.strength-seg {
  height: 4px;
  flex: 1;
  border-radius: 4px;
  background: #ebeef5;
  transition: background 0.25s;
}
.strength-seg.str-1 { background: #f87171; }
.strength-seg.str-2 { background: #fbbf24; }
.strength-seg.str-3 { background: #34d399; }
.strength-text {
  font-size: 11px;
  color: #909399;
  flex-shrink: 0;
  min-width: 24px;
}

// ---------- 选项行 ----------
.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

// ---------- 登录按钮 ----------
.login-button {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  margin-top: 4px;

  &:hover {
    background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
  }
}

// ---------- 演示账号提示 ----------
.demo-tip {
  margin-top: 18px;
  padding: 10px 14px;
  border-radius: 8px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  font-size: 12px;
  color: #909399;

  strong {
    color: #667eea;
    font-weight: 600;
  }

  .demo-row {
    line-height: 1.8;
  }
}

// ---------- 注册链接 ----------
.register-link {
  text-align: center;
  margin-top: 18px;
  font-size: 14px;
  color: #606266;
}

// ---------- 底部 ----------
.login-footer {
  margin-top: 20px;
  text-align: center;

  p {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-secondary, #909399);

    &.copyright {
      margin-top: 4px;
      font-size: 11px;
      color: #c0c4cc;
    }
  }
}

// ---------- 动画 ----------
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.1; }
  50%      { transform: scale(1.1); opacity: 0.15; }
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25%      { transform: translateX(-5px); }
  75%      { transform: translateX(5px); }
}

// ---------- 响应式 ----------
@media (max-width: 900px) {
  .login-page {
    flex-direction: column;
  }
  .brand-section {
    padding: 30px 20px;
    .features-list, .tech-tags { display: none; }
    .brand-title { font-size: 22px; }
    .mascot-brand { width: 180px; }
  }
  .login-section {
    width: 100%;
    flex: 1;
  }
}

</style>

