<template>
  <el-drawer
    v-model="visible"
    :title="isEdit ? '编辑爬虫配置' : '新建爬虫任务'"
    size="600px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="top"
      class="crawler-form"
    >
      <!-- 1. 基础配置 -->
      <div class="section-title">基础配置</div>
      
      <el-form-item label="任务名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入任务名称" maxlength="50" show-word-limit />
      </el-form-item>

      <el-form-item label="关键词" prop="keywords">
        <div class="keywords-container">
          <el-tag
            v-for="(kw, index) in form.keywords"
            :key="index"
            closable
            :type="kw.weight > 1 ? 'warning' : ''"
            class="keyword-tag"
            @close="removeKeyword(index)"
          >
            {{ kw.word }}
            <span v-if="kw.weight > 1" class="weight-badge">×{{ kw.weight }}</span>
          </el-tag>
          <el-popover
            v-model:visible="keywordPopoverVisible"
            placement="bottom"
            :width="280"
            trigger="click"
          >
            <template #reference>
              <el-button size="small" type="primary" plain>+ 添加关键词</el-button>
            </template>
            <div class="keyword-input-area">
              <el-input v-model="newKeyword.word" placeholder="关键词" style="margin-bottom: 8px;" />
              <el-slider v-model="newKeyword.weight" :min="1" :max="5" :step="1" show-stops :marks="weightMarks" />
              <div class="weight-label">权重: {{ newKeyword.weight }}</div>
              <el-button type="primary" size="small" @click="addKeyword" style="margin-top: 10px;">确认添加</el-button>
            </div>
          </el-popover>
        </div>
      </el-form-item>

      <el-form-item label="时间范围" prop="dateRange">
        <el-date-picker
          v-model="form.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 100%;"
          :shortcuts="dateShortcuts"
        />
      </el-form-item>

      <el-form-item label="数据量限制" prop="dataLimit">
        <el-input-number
          v-model="form.dataLimit"
          :min="100"
          :max="100000"
          :step="100"
          controls-position="right"
          style="width: 100%;"
        />
        <div class="form-tip">最大采集数据条数，0表示不限制</div>
      </el-form-item>

      <!-- 2. 平台选择 -->
      <div class="section-title">平台选择</div>

      <el-form-item label="数据源平台" prop="platforms">
        <el-checkbox-group v-model="form.platforms">
          <el-checkbox label="weibo">
            <el-icon><ChatDotRound /></el-icon> 微博
          </el-checkbox>
          <el-checkbox label="wechat">
            <el-icon><ChatLineRound /></el-icon> 微信
          </el-checkbox>
          <el-checkbox label="douyin">
            <el-icon><VideoCamera /></el-icon> 抖音
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <!-- 微博子选项 -->
      <el-form-item v-if="form.platforms.includes('weibo')" label="微博数据类型" prop="weiboOptions">
        <el-checkbox-group v-model="form.weiboOptions">
          <el-checkbox label="hotSearch">热搜榜</el-checkbox>
          <el-checkbox label="userProfile">用户主页</el-checkbox>
          <el-checkbox label="topic">话题</el-checkbox>
          <el-checkbox label="comment">评论</el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <!-- 3. 高级配置 -->
      <el-collapse v-model="activeCollapse" class="advanced-collapse">
        <el-collapse-item title="高级配置" name="advanced">
          <el-form-item label="请求间隔 (ms)">
            <el-slider
              v-model="form.requestInterval"
              :min="500"
              :max="5000"
              :step="100"
              show-input
              :marks="intervalMarks"
            />
          </el-form-item>

          <el-form-item label="代理设置">
            <div class="proxy-setting">
              <el-switch v-model="form.useProxy" active-text="启用代理" />
              <el-input
                v-if="form.useProxy"
                v-model="form.proxyList"
                type="textarea"
                :rows="3"
                placeholder="每行一个代理地址，格式: ip:port 或 http://ip:port"
                style="margin-top: 10px;"
              />
            </div>
          </el-form-item>

          <el-form-item label="其他选项">
            <div class="other-options">
              <el-switch v-model="form.rotateUserAgent" active-text="User-Agent轮换" style="margin-right: 20px;" />
              <el-switch v-model="form.downloadMedia" active-text="下载图片/视频" />
            </div>
          </el-form-item>
        </el-collapse-item>
      </el-collapse>

      <!-- 4. 定时任务配置 -->
      <div class="section-title">定时任务</div>

      <el-form-item label="定时执行">
        <el-switch v-model="form.enableSchedule" active-text="启用定时任务" />
      </el-form-item>

      <template v-if="form.enableSchedule">
        <el-form-item label="Cron表达式" prop="cronExpression">
          <el-input v-model="form.cronExpression" placeholder="例如: 0 0 * * * (每小时执行)">
            <template #append>
              <el-popover placement="bottom" :width="320" trigger="click">
                <template #reference>
                  <el-button>可视化编辑</el-button>
                </template>
                <div class="cron-editor">
                  <el-form label-width="60px" size="small">
                    <el-form-item label="频率">
                      <el-select v-model="cronHelper.frequency" @change="updateCron">
                        <el-option label="每分钟" value="minute" />
                        <el-option label="每小时" value="hour" />
                        <el-option label="每天" value="day" />
                        <el-option label="每周" value="week" />
                        <el-option label="每月" value="month" />
                      </el-select>
                    </el-form-item>
                    <el-form-item v-if="cronHelper.frequency === 'hour'" label="分钟">
                      <el-input-number v-model="cronHelper.minute" :min="0" :max="59" @change="updateCron" />
                    </el-form-item>
                    <el-form-item v-if="['day', 'week', 'month'].includes(cronHelper.frequency)" label="时间">
                      <el-time-select
                        v-model="cronHelper.time"
                        start="00:00"
                        step="01:00"
                        end="23:00"
                        @change="updateCron"
                      />
                    </el-form-item>
                    <el-form-item v-if="cronHelper.frequency === 'week'" label="星期">
                      <el-select v-model="cronHelper.dayOfWeek" @change="updateCron">
                        <el-option label="周一" :value="1" />
                        <el-option label="周二" :value="2" />
                        <el-option label="周三" :value="3" />
                        <el-option label="周四" :value="4" />
                        <el-option label="周五" :value="5" />
                        <el-option label="周六" :value="6" />
                        <el-option label="周日" :value="0" />
                      </el-select>
                    </el-form-item>
                    <el-form-item v-if="cronHelper.frequency === 'month'" label="日期">
                      <el-input-number v-model="cronHelper.dayOfMonth" :min="1" :max="31" @change="updateCron" />
                    </el-form-item>
                  </el-form>
                  <div class="cron-preview">
                    生成的表达式: <code>{{ form.cronExpression }}</code>
                  </div>
                </div>
              </el-popover>
            </template>
          </el-input>
          <div class="form-tip">{{ cronDescription }}</div>
        </el-form-item>

        <el-form-item label="执行次数限制">
          <el-input-number
            v-model="form.maxExecutions"
            :min="0"
            :max="1000"
            controls-position="right"
          />
          <span class="form-tip" style="margin-left: 10px;">0表示不限制</span>
        </el-form-item>
      </template>
    </el-form>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="drawer-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSave(false)" :loading="saving">保存</el-button>
        <el-button type="success" @click="handleSave(true)" :loading="saving">保存并启动</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { ChatDotRound, ChatLineRound, VideoCamera } from '@element-plus/icons-vue';

// Props & Emits
const props = defineProps<{
  modelValue: boolean;
  editData?: any;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'save', data: any, startNow: boolean): void;
}>();

// 可见性
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

const isEdit = computed(() => !!props.editData);

// 表单引用
const formRef = ref<FormInstance>();
const saving = ref(false);
const activeCollapse = ref<string[]>([]);

// 表单数据
const form = reactive({
  name: '',
  keywords: [] as { word: string; weight: number }[],
  dateRange: null as [Date, Date] | null,
  dataLimit: 1000,
  platforms: ['weibo'] as string[],
  weiboOptions: ['hotSearch', 'topic'] as string[],
  requestInterval: 1000,
  useProxy: false,
  proxyList: '',
  rotateUserAgent: true,
  downloadMedia: false,
  enableSchedule: false,
  cronExpression: '0 * * * *',
  maxExecutions: 0,
});

// 关键词输入
const keywordPopoverVisible = ref(false);
const newKeyword = reactive({ word: '', weight: 1 });
const weightMarks = { 1: '1', 2: '2', 3: '3', 4: '4', 5: '5' };

function addKeyword() {
  if (!newKeyword.word.trim()) {
    ElMessage.warning('请输入关键词');
    return;
  }
  if (form.keywords.some(k => k.word === newKeyword.word.trim())) {
    ElMessage.warning('关键词已存在');
    return;
  }
  form.keywords.push({ word: newKeyword.word.trim(), weight: newKeyword.weight });
  newKeyword.word = '';
  newKeyword.weight = 1;
  keywordPopoverVisible.value = false;
}

function removeKeyword(index: number) {
  form.keywords.splice(index, 1);
}

// 日期快捷选项
const dateShortcuts = [
  { text: '最近一周', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 7); return [start, end]; } },
  { text: '最近一月', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 30); return [start, end]; } },
  { text: '最近三月', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 90); return [start, end]; } },
];

// 请求间隔标记
const intervalMarks = { 500: '快', 2000: '中', 5000: '慢' };

// Cron 可视化编辑
const cronHelper = reactive({
  frequency: 'hour',
  minute: 0,
  time: '08:00',
  dayOfWeek: 1,
  dayOfMonth: 1,
});

function updateCron() {
  const [hour, minute] = (cronHelper.time || '00:00').split(':').map(Number);
  switch (cronHelper.frequency) {
    case 'minute':
      form.cronExpression = '* * * * *';
      break;
    case 'hour':
      form.cronExpression = `${cronHelper.minute} * * * *`;
      break;
    case 'day':
      form.cronExpression = `${minute} ${hour} * * *`;
      break;
    case 'week':
      form.cronExpression = `${minute} ${hour} * * ${cronHelper.dayOfWeek}`;
      break;
    case 'month':
      form.cronExpression = `${minute} ${hour} ${cronHelper.dayOfMonth} * *`;
      break;
  }
}

const cronDescription = computed(() => {
  const cron = form.cronExpression;
  if (cron === '* * * * *') return '每分钟执行一次';
  if (/^\d+ \* \* \* \*$/.test(cron)) return `每小时的第 ${cron.split(' ')[0]} 分钟执行`;
  if (/^\d+ \d+ \* \* \*$/.test(cron)) {
    const [m, h] = cron.split(' ');
    return `每天 ${h.padStart(2, '0')}:${m.padStart(2, '0')} 执行`;
  }
  if (/^\d+ \d+ \* \* \d$/.test(cron)) {
    const [m, h, , , d] = cron.split(' ');
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `每${days[Number(d)]} ${h.padStart(2, '0')}:${m.padStart(2, '0')} 执行`;
  }
  if (/^\d+ \d+ \d+ \* \*$/.test(cron)) {
    const [m, h, day] = cron.split(' ');
    return `每月 ${day} 日 ${h.padStart(2, '0')}:${m.padStart(2, '0')} 执行`;
  }
  return '自定义表达式';
});

// 表单验证规则
const rules: FormRules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  keywords: [
    { type: 'array', required: true, message: '请至少添加一个关键词', trigger: 'change' },
  ],
  platforms: [
    { type: 'array', required: true, message: '请至少选择一个平台', trigger: 'change' },
  ],
  cronExpression: [
    { required: true, message: '请输入Cron表达式', trigger: 'blur' },
    { pattern: /^(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)$/, message: 'Cron表达式格式不正确', trigger: 'blur' },
  ],
};

// 监听编辑数据
watch(() => props.editData, (data) => {
  if (data) {
    Object.assign(form, data);
  }
}, { immediate: true });

// 关闭处理
function handleClose() {
  formRef.value?.resetFields();
  form.keywords = [];
  visible.value = false;
}

// 保存处理
async function handleSave(startNow: boolean) {
  if (!formRef.value) return;
  
  await formRef.value.validate(async (valid) => {
    if (!valid) {
      ElMessage.warning('请完善表单信息');
      return;
    }
    
    saving.value = true;
    try {
      // 模拟保存
      await new Promise(resolve => setTimeout(resolve, 500));
      
      emit('save', { ...form }, startNow);
      ElMessage.success(startNow ? '任务已保存并启动' : '任务已保存');
      handleClose();
    } finally {
      saving.value = false;
    }
  });
}
</script>

<style scoped>
.crawler-form {
  padding: 0 10px;
}
.section-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin: 20px 0 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}
.section-title:first-child {
  margin-top: 0;
}
.keywords-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.keyword-tag {
  display: inline-flex;
  align-items: center;
}
.weight-badge {
  margin-left: 4px;
  font-size: 11px;
  background: rgba(0,0,0,0.1);
  padding: 0 4px;
  border-radius: 4px;
}
.keyword-input-area {
  padding: 5px;
}
.weight-label {
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.advanced-collapse {
  margin: 15px 0;
  border: none;
}
.advanced-collapse :deep(.el-collapse-item__header) {
  background-color: #f5f7fa;
  padding: 0 15px;
  border-radius: 4px;
}
.proxy-setting, .other-options {
  width: 100%;
}
.other-options {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}
.cron-editor {
  padding: 10px 0;
}
.cron-preview {
  margin-top: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
}
.cron-preview code {
  color: #409eff;
  font-weight: bold;
}
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
