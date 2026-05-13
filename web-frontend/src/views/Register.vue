<template>
  <div class="register-page">
    <!-- 左侧品牌区域 -->
    <div class="brand-section">
      <div class="brand-content">
        <!-- 4 个跟随鼠标的卡通吉祥物 (替代原 logo) -->
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
      </div>
      
      <!-- 动态背景装饰 -->
      <div class="bg-decoration">
        <div class="circle circle-1"></div>
        <div class="circle circle-2"></div>
        <div class="circle circle-3"></div>
      </div>
    </div>
    
    <!-- 右侧注册区域 -->
    <div class="register-section">
      <div class="register-box">
        <div class="register-header">
          <h2>创建账号</h2>
          <p class="register-desc">注册以使用舆情分析系统</p>
        </div>

        <el-form 
          ref="registerFormRef" 
          :model="registerForm" 
          :rules="registerRules" 
          class="register-form"
          @keyup.enter="handleRegister"
        >
          <!-- 邮箱 -->
          <el-form-item prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱地址"
              :prefix-icon="Message"
              size="large"
              clearable
            />
          </el-form-item>

          <!-- 验证码 -->
          <el-form-item prop="code">
            <div class="code-input-wrapper">
              <el-input
                v-model="registerForm.code"
                placeholder="请输入验证码"
                :prefix-icon="Key"
                size="large"
                maxlength="6"
              />
              <el-button
                type="primary"
                :disabled="countdown > 0 || sendingCode"
                :loading="sendingCode"
                class="send-code-btn"
                size="large"
                @click="sendCode"
              >
                {{ countdown > 0 ? `${countdown}s后重发` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <!-- 用户名（可选） -->
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="用户名（可选，默认使用邮箱前缀）"
              :prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>

          <!-- 密码 -->
          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              :type="passwordVisible ? 'text' : 'password'"
              placeholder="请设置密码（6-32位，包含字母和数字）"
              :prefix-icon="Lock"
              size="large"
            >
              <template #suffix>
                <el-icon class="password-toggle" @click="passwordVisible = !passwordVisible">
                  <View v-if="passwordVisible" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <!-- 确认密码 -->
          <el-form-item prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              :type="confirmPasswordVisible ? 'text' : 'password'"
              placeholder="请确认密码"
              :prefix-icon="Lock"
              size="large"
            >
              <template #suffix>
                <el-icon class="password-toggle" @click="confirmPasswordVisible = !confirmPasswordVisible">
                  <View v-if="confirmPasswordVisible" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <!-- 同意条款 -->
          <el-form-item prop="agreement">
            <el-checkbox v-model="registerForm.agreement">
              我已阅读并同意 <el-link type="primary" :underline="false">服务条款</el-link> 和 <el-link type="primary" :underline="false">隐私政策</el-link>
            </el-checkbox>
          </el-form-item>

          <el-button
            type="primary"
            :loading="loading"
            class="register-button"
            size="large"
            @click="handleRegister"
          >
            <span v-if="!loading">注 册</span>
            <span v-else>注册中...</span>
          </el-button>
        </el-form>

        <div class="login-link">
          <span>已有账号？</span>
          <el-link type="primary" :underline="false" @click="goToLogin">立即登录</el-link>
        </div>

        <div class="register-footer">
          <p>本科毕业设计 · 微博舆情分析系统</p>
          <p class="copyright">© 2026 罗森 · 学号 2022407443</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { User, Lock, View, Hide, DataAnalysis, TrendCharts, Histogram, Cpu, Message, Key } from '@element-plus/icons-vue';
import apiClient from '@/api/index';
import { useAuthStore } from '@/store/auth';
import MascotEyes from '@/components/MascotEyes.vue';

const router = useRouter();
const authStore = useAuthStore();

// 表单状态
const registerFormRef = ref<FormInstance>();
const loading = ref(false);
const passwordVisible = ref(false);
const confirmPasswordVisible = ref(false);

// 验证码相关
const sendingCode = ref(false);
const countdown = ref(0);
let countdownTimer: number | null = null;

// 注册表单
const registerForm = reactive({
  email: '',
  code: '',
  username: '',
  password: '',
  confirmPassword: '',
  agreement: false
});

// 自定义验证器
const validatePassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请设置密码'));
  } else if (value.length < 6) {
    callback(new Error('密码长度不能少于6位'));
  } else if (value.length > 32) {
    callback(new Error('密码长度不能超过32位'));
  } else if (!/[a-zA-Z]/.test(value)) {
    callback(new Error('密码必须包含字母'));
  } else if (!/\d/.test(value)) {
    callback(new Error('密码必须包含数字'));
  } else {
    callback();
  }
};

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请确认密码'));
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback();
  }
};

const validateAgreement = (rule: any, value: boolean, callback: any) => {
  if (!value) {
    callback(new Error('请阅读并同意服务条款'));
  } else {
    callback();
  }
};

// 验证规则
const registerRules = reactive<FormRules>({
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ],
  username: [
    { min: 2, max: 20, message: '用户名长度为2-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ],
  agreement: [
    { validator: validateAgreement, trigger: 'change' }
  ]
});

// 发送验证码
const sendCode = async () => {
  // 先验证邮箱
  try {
    await registerFormRef.value?.validateField('email');
  } catch {
    return;
  }
  
  sendingCode.value = true;
  try {
    const response = await apiClient.post('/auth/send-code', {
      email: registerForm.email,
      type: 'register'
    });
    
    if (response.data.code === 200) {
      ElMessage.success('验证码已发送');
      
      // 开发环境显示验证码
      if (response.data.data?.debug_code) {
        ElMessage.info({ message: `开发模式验证码: ${response.data.data.debug_code}`, duration: 10000, showClose: true });
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
      ElMessage.warning(response.data.message || '发送失败');
    }
  } catch (error: any) {
    const msg = error.response?.data?.message || '发送验证码失败';
    ElMessage.warning(msg);
  } finally {
    sendingCode.value = false;
  }
};

// 注册处理
const handleRegister = () => {
  registerFormRef.value?.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      
      try {
        const response = await apiClient.post('/auth/register', {
          email: registerForm.email,
          code: registerForm.code,
          username: registerForm.username || undefined,
          password: registerForm.password
        });
        
        if (response.data.code === 200) {
          ElMessage.success('注册成功！');
          
          const userData = response.data.data;
          authStore.setToken(userData.accessToken);
          authStore.setUser(userData.user);
          localStorage.setItem('isLoggedIn', 'true');
          localStorage.setItem('username', userData.user.username);
          localStorage.setItem('userEmail', userData.user.email);
          localStorage.setItem('userRole', userData.user.role);
          localStorage.setItem('accessToken', userData.accessToken);
          
          router.push('/dashboard');
        } else {
          ElMessage.warning(response.data.message || '注册失败');
        }
      } catch (error: any) {
        const msg = error.response?.data?.message || '注册失败';
        ElMessage.warning(msg);
      } finally {
        loading.value = false;
      }
    }
  });
};

// 跳转登录
const goToLogin = () => {
  router.push('/login');
};

// 清理定时器
onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
  }
});
</script>

<style scoped lang="scss">
.register-page {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

// 左侧品牌区域
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
  
  // 吉祥物置于左侧品牌区顶部，环境光效果更明显
  .mascot-brand {
    width: 260px;
    margin: 0 auto 20px;
    display: block;
    filter: drop-shadow(0 6px 24px rgba(0, 0, 0, 0.25));
  }

  .logo-wrapper {
    margin-bottom: 24px;
    
    .brand-logo {
      width: 100px;
      height: 100px;
      filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.2));
      animation: float 3s ease-in-out infinite;
    }
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
}

// 背景装饰
.bg-decoration {
  position: absolute;
  inset: 0;
  overflow: hidden;
  
  .circle {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
  }
  
  .circle-1 {
    width: 400px;
    height: 400px;
    top: -100px;
    left: -100px;
    animation: pulse 4s ease-in-out infinite;
  }
  
  .circle-2 {
    width: 300px;
    height: 300px;
    bottom: -50px;
    right: -50px;
    animation: pulse 5s ease-in-out infinite 1s;
  }
  
  .circle-3 {
    width: 200px;
    height: 200px;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation: pulse 6s ease-in-out infinite 2s;
  }
}

// 右侧注册区域
.register-section {
  width: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: white;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
}

.register-box {
  width: 100%;
  max-width: 400px;
}

.register-header {
  text-align: center;
  margin-bottom: 18px;
  
  h2 {
    font-size: 26px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px 0;
  }
  
  .register-desc {
    color: var(--color-text-secondary);
    font-size: 14px;
    margin: 0;
  }
}

.register-form {
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
    color: var(--color-text-secondary);
    
    &:hover {
      color: #667eea;
    }
  }
}

// 验证码输入
.code-input-wrapper {
  display: flex;
  gap: 12px;
  width: 100%;
  
  .el-input {
    flex: 1;
  }
  
  .send-code-btn {
    width: 120px;
    flex-shrink: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    
    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
    }
    
    &:disabled {
      background: #c0c4cc;
      color: white;
    }
  }
}

.register-button {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  margin-top: 8px;
  
  &:hover {
    background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
  }
}

.login-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #606266;
}

.register-footer {
  margin-top: 24px;
  text-align: center;
  
  p {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-secondary);
    
    &.copyright {
      margin-top: 4px;
      font-size: 11px;
      color: #c0c4cc;
    }
  }
}

// 动画
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.1; }
  50% { transform: scale(1.1); opacity: 0.15; }
}

// 响应式
@media (max-width: 900px) {
  .register-page {
    flex-direction: column;
  }
  
  .brand-section {
    padding: 30px 20px;
    
    .features-list {
      display: none;
    }
    
    .brand-title {
      font-size: 22px;
    }
  }
  
  .register-section {
    width: 100%;
    flex: 1;
  }
}
</style>
