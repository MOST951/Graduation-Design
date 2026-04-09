<template>
  <el-dialog
    v-model="visible"
    title="爬虫配置"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
      <!-- 基本信息 -->
      <el-divider content-position="left">基本信息</el-divider>
      
      <el-form-item label="任务名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入任务名称" />
      </el-form-item>
      
      <el-form-item label="关键词" prop="keywords">
        <el-tag
          v-for="(keyword, index) in form.keywords"
          :key="index"
          closable
          @close="handleRemoveKeyword(index)"
          style="margin-right: 8px"
        >
          {{ keyword.word }}
        </el-tag>
        <el-input
          v-if="keywordInputVisible"
          ref="keywordInputRef"
          v-model="keywordInput"
          size="small"
          style="width: 120px"
          @keyup.enter="handleAddKeyword"
          @blur="handleAddKeyword"
        />
        <el-button
          v-else
          size="small"
          @click="showKeywordInput"
        >
          + 添加关键词
        </el-button>
      </el-form-item>
      
      <el-form-item label="时间范围" prop="dateRange">
        <el-date-picker
          v-model="form.dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          style="width: 100%"
        />
      </el-form-item>
      
      <el-form-item label="热搜榜单">
        <el-input v-model="form.hotTopic" placeholder="例如：微博热搜、抖音热榜" />
      </el-form-item>
      
      <!-- 数据源配置 -->
      <el-divider content-position="left">数据源配置</el-divider>
      
      <el-form-item label="数据源" prop="dataSources">
        <el-checkbox-group v-model="form.dataSources">
          <el-checkbox label="weibo">
            <el-icon><ChatDotRound /></el-icon>
            微博
          </el-checkbox>
          <el-checkbox label="wechat">
            <el-icon><ChatLineRound /></el-icon>
            微信
          </el-checkbox>
          <el-checkbox label="douyin">
            <el-icon><VideoCamera /></el-icon>
            抖音
          </el-checkbox>
          <el-checkbox label="zhihu">
            <el-icon><Reading /></el-icon>
            知乎
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      
      <el-form-item label="采集数量">
        <el-input-number v-model="form.maxCount" :min="100" :max="100000" :step="100" />
        <span style="margin-left: 8px; color: #909399">条</span>
      </el-form-item>
      
      <!-- 反爬策略 -->
      <el-divider content-position="left">反爬策略</el-divider>
      
      <el-form-item label="请求间隔">
        <el-input-number v-model="form.requestInterval" :min="1" :max="60" />
        <span style="margin-left: 8px; color: #909399">秒</span>
      </el-form-item>
      
      <el-form-item label="IP代理池">
        <el-switch v-model="form.useProxy" />
        <span style="margin-left: 8px; color: #909399">
          {{ form.useProxy ? '已启用' : '未启用' }}
        </span>
      </el-form-item>
      
      <el-form-item label="代理地址" v-if="form.useProxy">
        <el-input
          v-model="form.proxyUrl"
          placeholder="http://proxy.example.com:8080"
        />
      </el-form-item>
      
      <el-form-item label="Headers伪装">
        <el-switch v-model="form.fakeHeaders" />
        <span style="margin-left: 8px; color: #909399">
          {{ form.fakeHeaders ? '已启用' : '未启用' }}
        </span>
      </el-form-item>
      
      <el-form-item label="User-Agent" v-if="form.fakeHeaders">
        <el-select v-model="form.userAgent" style="width: 100%">
          <el-option
            label="Chrome (Windows)"
            value="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          />
          <el-option
            label="Safari (Mac)"
            value="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
          />
          <el-option
            label="Firefox (Linux)"
            value="Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
          />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      
      <el-form-item v-if="form.userAgent === 'custom'" label="自定义UA">
        <el-input
          v-model="form.customUserAgent"
          type="textarea"
          :rows="2"
          placeholder="请输入自定义User-Agent"
        />
      </el-form-item>
      
      <!-- 高级设置 -->
      <el-divider content-position="left">高级设置</el-divider>
      
      <el-form-item label="重试次数">
        <el-input-number v-model="form.retryCount" :min="0" :max="10" />
      </el-form-item>
      
      <el-form-item label="超时时间">
        <el-input-number v-model="form.timeout" :min="5" :max="300" />
        <span style="margin-left: 8px; color: #909399">秒</span>
      </el-form-item>
      
      <el-form-item label="并发数">
        <el-input-number v-model="form.concurrency" :min="1" :max="10" />
      </el-form-item>
      
      <el-form-item label="数据去重">
        <el-switch v-model="form.deduplicate" />
      </el-form-item>
      
      <el-form-item label="自动保存">
        <el-switch v-model="form.autoSave" />
        <span style="margin-left: 8px; color: #909399">
          每采集1000条自动保存
        </span>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button @click="handleSave(false)">保存配置</el-button>
      <el-button type="primary" @click="handleSave(true)">
        保存并立即开始
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import {
  ChatDotRound, ChatLineRound, VideoCamera, Reading,
} from '@element-plus/icons-vue';

interface Props {
  modelValue: boolean;
  editData?: any;
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void;
  (e: 'save', data: any, startNow: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(props.modelValue);
const formRef = ref();
const keywordInputVisible = ref(false);
const keywordInputRef = ref();
const keywordInput = ref('');

const form = reactive({
  name: '',
  keywords: [] as Array<{ word: string; weight: number }>,
  dateRange: [],
  hotTopic: '',
  dataSources: ['weibo'],
  maxCount: 10000,
  requestInterval: 3,
  useProxy: false,
  proxyUrl: '',
  fakeHeaders: true,
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  customUserAgent: '',
  retryCount: 3,
  timeout: 30,
  concurrency: 3,
  deduplicate: true,
  autoSave: true,
});

const rules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
  ],
  keywords: [
    {
      required: true,
      validator: (rule: any, value: any, callback: any) => {
        if (form.keywords.length === 0) {
          callback(new Error('请至少添加一个关键词'));
        } else {
          callback();
        }
      },
      trigger: 'change',
    },
  ],
  dataSources: [
    {
      required: true,
      validator: (rule: any, value: any, callback: any) => {
        if (form.dataSources.length === 0) {
          callback(new Error('请至少选择一个数据源'));
        } else {
          callback();
        }
      },
      trigger: 'change',
    },
  ],
};

watch(() => props.modelValue, (val) => {
  visible.value = val;
  if (val && props.editData) {
    Object.assign(form, props.editData);
  }
});

watch(visible, (val) => {
  emit('update:modelValue', val);
});

const showKeywordInput = () => {
  keywordInputVisible.value = true;
  nextTick(() => {
    keywordInputRef.value?.focus();
  });
};

const handleAddKeyword = () => {
  if (keywordInput.value) {
    form.keywords.push({
      word: keywordInput.value,
      weight: 1,
    });
    keywordInput.value = '';
  }
  keywordInputVisible.value = false;
};

const handleRemoveKeyword = (index: number) => {
  form.keywords.splice(index, 1);
};

const handleClose = () => {
  visible.value = false;
  formRef.value?.resetFields();
};

const handleSave = async (startNow: boolean) => {
  try {
    await formRef.value?.validate();
    
    const data = {
      ...form,
      userAgent: form.userAgent === 'custom' ? form.customUserAgent : form.userAgent,
    };
    
    emit('save', data, startNow);
    ElMessage.success(startNow ? '配置已保存，任务即将开始' : '配置已保存');
    handleClose();
  } catch (error) {
    ElMessage.warning('请完善必填项');
  }
};
</script>

<style scoped lang="scss">
:deep(.el-divider__text) {
  font-weight: bold;
  color: #409eff;
}
</style>
