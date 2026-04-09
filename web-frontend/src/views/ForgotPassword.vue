<template>
  <div class="forgot-page">
    <!-- 左侧品牌区域 -->
    <div class="brand-section">
      <div class="brand-content">
        <div class="logo-wrapper">
          <img src="/logo.svg" alt="Logo" class="brand-logo" />
        </div>
        <h1 class="brand-title">微博舆情分析系统</h1>
        <p class="brand-subtitle">Weibo Sentiment Analysis Platform</p>
      </div>
      
      <!-- 动态背景装饰 -->
      <div class="bg-decoration">
        <div class="circle circle-1"></div>
        <div class="circle circle-2"></div>
        <div class="circle circle-3"></div>
      </div>
    </div>
    
    <!-- 右侧重置密码区域 -->
    <div class="forgot-section">
      <div class="forgot-box">
        <!-- 步骤指示器 -->
        <el-steps :active="currentStep" finish-status="success" simple class="steps-indicator">
          <el-step title="验证邮箱" />
          <el-step title="重置密码" />
          <el-step title="完成" />
        </el-steps>

        <!-- 步骤1：验证邮箱 -->
        <div v-show="currentStep === 0" class="step-content">
          <div class="step-header">
            <h2>找回密码</h2>
            <p class="step-desc">请输入您注册时使用的邮箱地址</p>
          </div>

          <el-form ref="emailFormRef" :model="emailForm" :rules="emailRules" class="forgot-form">
            <el-form-item prop="email">
              <el-input
                v-model="emailForm.email"
                placeholder="请输入邮箱地址"
                :prefix-icon="Message"
                size="large"
                clearable
              />
            </el-form-item>

            <el-form-item prop="code">
              <div class="code-input-wrapper">
                <el-input
                  v-model="emailForm.code"
                  placeholder="请输入验证码"
                  :prefix-icon="Key"
                  size="large"
                  maxlength="6"
                />
                <el-button
                  type="primary"
                  :disabled="countdown > 0 || sendingCode"
                  :loading="sendingCode"
                  @click="sendCode"
                  class="send-code-btn"
                  size="large"
                >
                  {{ countdown > 0 ? `${countdown}s后重发` : '获取验证码' }}
                </el-button>
              </div>
            </el-form-item>

            <el-button
              type="primary"
              @click="verifyEmail"
              :loading="verifying"
              class="action-button"
              size="large"
            >
              下一步
            </el-button>
          </el-form>
        </div>

        <!-- 步骤2：设置新密码 -->
        <div v-show="currentStep === 1" class="step-content">
          <div class="step-header">
            <h2>设置新密码</h2>
            <p class="step-desc">请设置您的新密码</p>
          </div>

          <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" class="forgot-form">
            <el-form-item prop="password">
              <el-input
                v-model="passwordForm.password"
                :type="passwordVisible ? 'text' : 'password'"
                placeholder="请设置新密码（6-32位，包含字母和数字）"
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

            <el-form-item prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                :type="confirmPasswordVisible ? 'text' : 'password'"
                placeholder="请确认新密码"
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

            <el-button
              type="primary"
              @click="resetPassword"
              :loading="resetting"
              class="action-button"
              size="large"
            >
              重置密码
            </el-button>
          </el-form>
        </div>

        <!-- 步骤3：完成 -->
        <div v-show="currentStep === 2" class="step-content success-content">
          <div class="success-icon">
            <el-icon :size="64" color="#67c23a"><CircleCheck /></el-icon>
          </div>
          <h2>密码重置成功</h2>
          <p class="success-desc">您的密码已成功重置，请使用新密码登录</p>
          <el-button
            type="primary"
            @click="goToLogin"
            class="action-button"
            size="large"
          >
            立即登录
          </el-button>
        </div>

        <div class="back-link" v-if="currentStep < 2">
          <el-link type="primary" :underline="false" @click="goToLogin">
            <el-icon><ArrowLeft /></el-icon>
            返回登录
          </el-link>
        </div>

        <div class="forgot-footer">
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
import { Lock, View, Hide, Message, Key, CircleCheck, ArrowLeft } from '@element-plus/icons-vue';
import apiClient from '@/api/index';

const router = useRouter();

// 当前步骤
const currentStep = ref(0);

// 表单状态
const emailFormRef = ref<FormInstance>();
const passwordFormRef = ref<FormInstance>();
const passwordVisible = ref(false);
const confirmPasswordVisible = ref(false);

// 加载状态
const sendingCode = ref(false);
const verifying = ref(false);
const resetting = ref(false);

// 验证码倒计时
const countdown = ref(0);
let countdownTimer: number | null = null;

// 已验证的邮箱和验证码
let verifiedEmail = '';
let verifiedCode = '';

// 邮箱验证表单
const emailForm = reactive({
  email: '',
  code: ''
});

// 密码表单
const passwordForm = reactive({
  password: '',
  confirmPassword: ''
});

// 邮箱验证规则
const emailRules = reactive<FormRules>({
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ]
});

// 密码验证器
const validatePassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请设置新密码'));
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
    callback(new Error('请确认新密码'));
  } else if (value !== passwordForm.password) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback();
  }
};

// 密码验证规则
const passwordRules = reactive<FormRules>({
  password: [
    { required: true, validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
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
    // 先检查邮箱是否已注册
    const checkResponse = await apiClient.post('/auth/check-email', {
      email: emailForm.email
    });
    
    if (checkResponse.data.code === 200 && !checkResponse.data.data.exists) {
      ElMessage.error('该邮箱未注册');
      sendingCode.value = false;
      return;
    }
    
    const response = await apiClient.post('/auth/send-code', {
      email: emailForm.email,
      type: 'reset'
    });
    
    if (response.data.code === 200) {
      ElMessage.success('验证码已发送');
      
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

// 验证邮箱（进入下一步）
const verifyEmail = () => {
  emailFormRef.value?.validate(async (valid) => {
    if (valid) {
      // 保存已验证的邮箱和验证码，用于下一步重置密码
      verifiedEmail = emailForm.email;
      verifiedCode = emailForm.code;
      currentStep.value = 1;
    }
  });
};

// 重置密码
const resetPassword = () => {
  passwordFormRef.value?.validate(async (valid) => {
    if (valid) {
      resetting.value = true;
      
      try {
        const response = await apiClient.post('/auth/reset-password', {
          email: verifiedEmail,
          code: verifiedCode,
          newPassword: passwordForm.password
        });
        
        if (response.data.code === 200) {
          currentStep.value = 2;
        } else {
          ElMessage.error(response.data.message || '重置失败');
          // 如果验证码错误，返回第一步
          if (response.data.message?.includes('验证码')) {
            currentStep.value = 0;
          }
        }
      } catch (error: any) {
        const msg = error.response?.data?.message || '重置密码失败';
        ElMessage.error(msg);
        // 如果验证码错误，返回第一步
        if (msg.includes('验证码')) {
          currentStep.value = 0;
        }
      } finally {
        resetting.value = false;
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
.forgot-page {
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
    margin: 0;
    letter-spacing: 1px;
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

// 右侧重置密码区域
.forgot-section {
  width: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: white;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.1);
}

.forgot-box {
  width: 100%;
  max-width: 380px;
}

.steps-indicator {
  margin-bottom: 32px;
  
  :deep(.el-step__title) {
    font-size: 13px;
  }
}

.step-content {
  animation: fadeIn 0.3s ease;
}

.step-header {
  text-align: center;
  margin-bottom: 24px;
  
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px 0;
  }
  
  .step-desc {
    color: #909399;
    font-size: 14px;
    margin: 0;
  }
}

.forgot-form {
  .el-form-item {
    margin-bottom: 20px;
  }
  
  :deep(.el-input__wrapper) {
    padding: 4px 15px;
    border-radius: 8px;
    
    &:hover, &.is-focus {
      box-shadow: 0 0 0 1px #667eea inset;
    }
  }
  
  :deep(.el-input__inner) {
    height: 44px;
  }
  
  .password-toggle {
    cursor: pointer;
    color: #909399;
    
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

.action-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  margin-top: 8px;
  
  &:hover {
    background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
  }
}

// 成功页面
.success-content {
  text-align: center;
  padding: 20px 0;
  
  .success-icon {
    margin-bottom: 20px;
  }
  
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 12px 0;
  }
  
  .success-desc {
    color: #909399;
    font-size: 14px;
    margin: 0 0 24px 0;
  }
}

.back-link {
  text-align: center;
  margin-top: 24px;
  
  .el-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
}

.forgot-footer {
  margin-top: 32px;
  text-align: center;
  
  p {
    margin: 0;
    font-size: 12px;
    color: #909399;
    
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

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

// 响应式
@media (max-width: 900px) {
  .forgot-page {
    flex-direction: column;
  }
  
  .brand-section {
    padding: 30px 20px;
    
    .brand-title {
      font-size: 22px;
    }
  }
  
  .forgot-section {
    width: 100%;
    flex: 1;
  }
}
</style>
