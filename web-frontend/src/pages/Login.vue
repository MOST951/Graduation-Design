<template>
  <div class="login-page">
    <!-- 背景层 -->
    <div class="bg-layer">
      <div class="bg-gradient"></div>
      <div class="glow glow-1"></div>
      <div class="glow glow-2"></div>
      <div class="glow glow-3"></div>
    </div>
    
    <!-- 主容器 -->
    <div class="login-wrapper">
      <!-- 左侧信息区 -->
      <div class="info-panel">
        <div class="info-content">
          <!-- Logo -->
          <div class="logo-area">
            <div class="logo-icon">
              <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="40" cy="40" r="38" stroke="url(#logoGrad)" stroke-width="3" fill="rgba(255,255,255,0.1)" />
                <ellipse cx="40" cy="35" rx="18" ry="12" fill="white" opacity="0.9" />
                <circle cx="40" cy="35" r="6" fill="url(#logoGrad)" />
                <path d="M20 52 Q30 58 40 52 Q50 46 60 52" stroke="white" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.8" />
                <path d="M25 58 Q35 64 45 58 Q55 52 65 58" stroke="white" stroke-width="2" stroke-linecap="round" fill="none" opacity="0.5" />
                <defs>
                  <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#60a5fa" />
                    <stop offset="100%" stop-color="#a78bfa" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </div>
          
          <!-- 标题 -->
          <h1 class="main-title">微博舆论情感分析系统</h1>
          <p class="sub-title">Weibo Sentiment Analysis Platform</p>
          
          <!-- 功能特性 -->
          <div class="features">
            <div class="feature-item">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M3 3v18h18" />
                  <path d="M7 14l4-4 4 4 5-5" />
                </svg>
              </div>
              <span>情感-热度双维度分析</span>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M12 1v4m0 14v4M1 12h4m14 0h4" />
                  <path d="M4.22 4.22l2.83 2.83m9.9 9.9l2.83 2.83M4.22 19.78l2.83-2.83m9.9-9.9l2.83-2.83" />
                </svg>
              </div>
              <span>实时舆情监控预警</span>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                  <path d="M9 9h6v6H9z" />
                  <path d="M9 1v3m6-3v3M9 20v3m6-3v3M1 9h3m0 6H1m19-6h3m-3 6h3" />
                </svg>
              </div>
              <span>Spark 分布式处理</span>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <span>ChineseBERT 深度学习</span>
            </div>
          </div>
          
          <!-- 技术栈标签 -->
          <div class="tech-stack">
            <span class="tech-tag">Vue 3</span>
            <span class="tech-tag">Flask</span>
            <span class="tech-tag">Spark</span>
            <span class="tech-tag">ChineseBERT</span>
          </div>
        </div>
      </div>
      
      <!-- 右侧登录区 -->
      <div class="form-panel">
        <div class="form-container">
          <h2 class="form-title">欢迎登录</h2>
          <p class="form-subtitle">Welcome back</p>
          
          <el-form 
            ref="loginFormRef" 
            :model="loginForm" 
            :rules="loginRules" 
            class="login-form"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input 
                v-model="loginForm.username" 
                placeholder="请输入用户名"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input 
                v-model="loginForm.password" 
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                size="large"
                :prefix-icon="Lock"
              >
                <template #suffix>
                  <el-icon class="pwd-toggle" @click="showPassword = !showPassword">
                    <View v-if="showPassword" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>
            
            <div class="form-options">
              <el-checkbox v-model="loginForm.rememberMe">记住我</el-checkbox>
            </div>
            
            <el-button 
              type="primary" 
              native-type="submit" 
              :loading="loading"
              class="login-btn"
              size="large"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form>
          
          <!-- 演示模式入口 -->
          <div class="demo-entry" @click="handleDemoLogin">
            <span class="demo-dot"></span>
            <span class="demo-text">演示模式</span>
            <span class="demo-hint">admin / admin123</span>
          </div>
          
          <!-- 底部信息 -->
          <div class="form-footer">
            <p>本科毕业设计 · 罗森 · 2022407443</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { 
  User, Lock, View, Hide, VideoPlay,
  DataAnalysis, TrendCharts, Cpu
} from '@element-plus/icons-vue';
import apiClient from '@/api';

const router = useRouter();
const authStore = useAuthStore();

// 表单状态
const loginFormRef = ref<FormInstance>();
const loading = ref(false);
const showPassword = ref(false);

const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
});

const loginRules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 5, message: '密码长度不能少于5位', trigger: 'blur' }
  ]
});

// 正常登录
const handleLogin = async () => {
  const valid = await loginFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  
  loading.value = true;
  try {
    const response = await apiClient.post('/auth/login', { 
      username: loginForm.username, 
      password: loginForm.password 
    });
    
    if (response.data.code === 200) {
      const token = response.data.data?.accessToken;
      const user = response.data.data?.user;
      
      authStore.setToken(token);
      if (user) authStore.setUser(user);
      
      ElMessage.success('登录成功！');
      router.push('/dashboard');
    } else {
      ElMessage.error(response.data.message || '登录失败');
    }
  } catch (error: any) {
    // 后端未启动时，使用模拟登录
    if (authStore.mockLogin(loginForm.username, loginForm.password)) {
      ElMessage.success('登录成功！');
      router.push('/dashboard');
    } else {
      ElMessage.error('用户名或密码错误');
    }
  } finally {
    loading.value = false;
  }
};

// 演示模式登录
const handleDemoLogin = () => {
  loading.value = true;
  setTimeout(() => {
    authStore.mockLogin('admin', 'admin123');
    ElMessage.success('已进入演示模式');
    router.push('/dashboard');
    loading.value = false;
  }, 500);
};
</script>

<style scoped lang="scss">
// 主题色
$primary-blue: #4f6ef7;
$primary-purple: #8b5cf6;
$dark-blue: #1e1b4b;
$text-muted: #94a3b8;

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  font-family: 'Source Han Sans CN', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif;
}

// ==================== 背景层 ====================
.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  
  .bg-gradient {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4c1d95 100%);
  }
  
  .glow {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.6;
    
    &.glow-1 {
      width: 500px;
      height: 500px;
      background: radial-gradient(circle, rgba(139, 92, 246, 0.5) 0%, transparent 70%);
      top: -150px;
      left: -100px;
      animation: glowFloat1 10s ease-in-out infinite;
    }
    
    &.glow-2 {
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(79, 110, 247, 0.4) 0%, transparent 70%);
      bottom: -100px;
      right: -50px;
      animation: glowFloat2 12s ease-in-out infinite;
    }
    
    &.glow-3 {
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(167, 139, 250, 0.3) 0%, transparent 70%);
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      animation: glowFloat3 8s ease-in-out infinite;
    }
  }
}

// ==================== 主容器 ====================
.login-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  width: 960px;
  max-width: 95vw;
  min-height: 580px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 25px 100px rgba(0, 0, 0, 0.5);
  
  @media (max-width: 800px) {
    flex-direction: column;
    width: 95vw;
    max-width: 420px;
    min-height: auto;
  }
}

// ==================== 左侧信息区 ====================
.info-panel {
  flex: 1;
  padding: 50px 45px;
  background: linear-gradient(160deg, #1e3a8a 0%, #4c1d95 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: 
      radial-gradient(circle at 30% 20%, rgba(255,255,255,0.08) 0%, transparent 50%),
      radial-gradient(circle at 70% 80%, rgba(255,255,255,0.05) 0%, transparent 40%);
  }
  
  @media (max-width: 800px) {
    padding: 35px 30px;
  }
}

.info-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
}

.logo-area {
  margin-bottom: 28px;
  
  .logo-icon {
    width: 90px;
    height: 90px;
    margin: 0 auto;
    animation: logoFloat 4s ease-in-out infinite;
    
    svg {
      width: 100%;
      height: 100%;
    }
    
    @media (max-width: 800px) {
      width: 70px;
      height: 70px;
    }
  }
}

.main-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 10px 0;
  letter-spacing: 2px;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
  
  @media (max-width: 800px) {
    font-size: 22px;
  }
}

.sub-title {
  font-size: 13px;
  font-weight: 300;
  opacity: 0.75;
  margin: 0 0 35px 0;
  letter-spacing: 1px;
  font-family: 'Inter', 'Segoe UI', sans-serif;
  
  @media (max-width: 800px) {
    margin-bottom: 25px;
  }
}

.features {
  margin-bottom: 35px;
  
  @media (max-width: 800px) {
    display: none;
  }
  
  .feature-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    margin-bottom: 8px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    transition: all 0.3s ease;
    
    &:hover {
      background: rgba(255, 255, 255, 0.14);
      transform: translateX(5px);
    }
    
    .feature-icon {
      width: 22px;
      height: 22px;
      flex-shrink: 0;
      opacity: 0.9;
      
      svg {
        width: 100%;
        height: 100%;
      }
    }
    
    span {
      font-size: 14px;
      opacity: 0.9;
      letter-spacing: 0.5px;
    }
  }
}

.tech-stack {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  
  .tech-tag {
    padding: 6px 16px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
    backdrop-filter: blur(5px);
    transition: all 0.3s;
    
    &:hover {
      background: rgba(255, 255, 255, 0.2);
      transform: translateY(-2px);
    }
    
    @media (max-width: 800px) {
      padding: 5px 12px;
      font-size: 11px;
    }
  }
}

// ==================== 右侧表单区 ====================
.form-panel {
  flex: 1;
  padding: 50px 50px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  
  @media (max-width: 800px) {
    padding: 40px 30px;
  }
}

.form-container {
  width: 100%;
  max-width: 320px;
}

.form-title {
  font-size: 28px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 6px 0;
  text-align: center;
}

.form-subtitle {
  font-size: 13px;
  color: $text-muted;
  margin: 0 0 35px 0;
  text-align: center;
  font-family: 'Inter', 'Segoe UI', sans-serif;
}

.login-form {
  .el-form-item {
    margin-bottom: 20px;
  }
  
  :deep(.el-input__wrapper) {
    padding: 4px 16px;
    border-radius: 12px;
    box-shadow: 0 0 0 1px #e2e8f0 inset;
    background: #f8fafc;
    transition: all 0.25s ease;
    
    &:hover {
      box-shadow: 0 0 0 1px #cbd5e1 inset;
      background: white;
    }
    
    &.is-focus {
      box-shadow: 0 0 0 2px rgba($primary-blue, 0.25) inset;
      background: white;
    }
  }
  
  :deep(.el-input__inner) {
    height: 48px;
    font-size: 14px;
  }
  
  :deep(.el-input__prefix) {
    color: $text-muted;
  }
  
  .pwd-toggle {
    cursor: pointer;
    color: $text-muted;
    transition: color 0.2s;
    
    &:hover {
      color: $primary-blue;
    }
  }
}

.form-options {
  margin-bottom: 24px;
  
  :deep(.el-checkbox__label) {
    color: #64748b;
    font-size: 13px;
  }
}

.login-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(90deg, $primary-blue 0%, $primary-purple 100%);
  border: none;
  letter-spacing: 2px;
  transition: all 0.3s ease;
  
  &:hover {
    transform: scale(1.02);
    box-shadow: 0 10px 30px rgba($primary-purple, 0.35);
  }
  
  &:active {
    transform: scale(0.98);
  }
}

.demo-entry {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 28px;
  padding: 14px 20px;
  background: #f8fafc;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
  
  &:hover {
    background: #f1f5f9;
    
    .demo-dot {
      transform: scale(1.3);
    }
  }
  
  .demo-dot {
    width: 8px;
    height: 8px;
    background: linear-gradient(135deg, $primary-blue, $primary-purple);
    border-radius: 50%;
    transition: transform 0.2s;
  }
  
  .demo-text {
    font-size: 14px;
    color: #475569;
    font-weight: 500;
  }
  
  .demo-hint {
    font-size: 12px;
    color: #94a3b8;
    margin-left: 5px;
  }
}

.form-footer {
  margin-top: 35px;
  text-align: center;
  
  p {
    margin: 0;
    font-size: 11px;
    color: #cbd5e1;
    letter-spacing: 0.5px;
  }
}

// ==================== 动画 ====================
@keyframes logoFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

@keyframes glowFloat1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, 20px) scale(1.1); }
}

@keyframes glowFloat2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-25px, -15px) scale(1.05); }
}

@keyframes glowFloat3 {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.3; }
  50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.5; }
}
</style>
