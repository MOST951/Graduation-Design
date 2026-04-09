<template>
  <div class="not-found-page">
    <div class="not-found-content">
      <div class="error-code">404</div>
      <h1>页面不存在</h1>
      <p>抱歉，您访问的页面不存在或已被删除</p>
      
      <div class="actions">
        <el-button type="primary" :icon="HomeFilled" @click="goHome">
          返回首页
        </el-button>
        <el-button :icon="Back" @click="goBack">
          返回上一页
        </el-button>
      </div>
      
      <el-divider />
      
      <div class="suggestions">
        <h3>您可能想访问：</h3>
        <el-space wrap>
          <el-button link @click="navigateTo('/dashboard')">
            <el-icon><Odometer /></el-icon>
            仪表板
          </el-button>
          <el-button link @click="navigateTo('/collection')">
            <el-icon><Download /></el-icon>
            数据采集
          </el-button>
          <el-button link @click="navigateTo('/analysis')">
            <el-icon><DataAnalysis /></el-icon>
            数据分析
          </el-button>
          <el-button link @click="navigateTo('/visualization')">
            <el-icon><DataLine /></el-icon>
            可视化
          </el-button>
        </el-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import {
  HomeFilled, Back, Odometer, Download, DataAnalysis, DataLine,
} from '@element-plus/icons-vue';

const router = useRouter();

const goHome = () => {
  router.push('/dashboard');
};

const goBack = () => {
  router.back();
};

const navigateTo = (path: string) => {
  router.push(path);
};
</script>

<style scoped lang="scss">
.not-found-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.not-found-content {
  text-align: center;
  padding: 60px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
}

.error-code {
  font-size: 120px;
  font-weight: bold;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 20px;
}

h1 {
  font-size: 32px;
  margin: 0 0 16px;
  color: #303133;
}

p {
  font-size: 16px;
  color: #909399;
  margin-bottom: 32px;
}

.actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 32px;
}

.suggestions {
  h3 {
    font-size: 18px;
    margin-bottom: 16px;
    color: #606266;
  }
}
</style>
