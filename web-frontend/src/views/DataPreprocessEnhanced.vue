<template>
  <div class="preprocess-module">
    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="status-left">
        <h2>数据预处理</h2>
        <el-tag v-if="dataSource === 'crawler'" type="success" size="small">实时爬虫数据</el-tag>
        <el-tag v-else-if="dataSource === 'file'" type="info" size="small">本地文件</el-tag>
        <el-tag v-else type="warning" size="small">示例数据</el-tag>
      </div>
      <div class="status-right">
        <el-statistic title="数据总量" :value="rawData.length" />
        <el-divider direction="vertical" />
        <el-statistic title="已处理" :value="processedCount" />
        <el-divider direction="vertical" />
        <el-statistic title="处理耗时" :value="processTime" suffix="ms" />
      </div>
    </div>

    <div class="preprocess-layout">
      <!-- 左侧操作面板 -->
      <div class="operation-panel">
        <!-- 数据源选择 -->
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>数据源</span>
              <el-button size="small" :icon="Refresh" circle :loading="isLoading" @click="refreshData" />
            </div>
          </template>
          
          <el-radio-group v-model="dataSource" @change="handleDataSourceChange">
            <el-radio label="crawler">实时爬取</el-radio>
            <el-radio label="file">本地文件</el-radio>
            <el-radio label="sample">示例数据</el-radio>
          </el-radio-group>
          
          <!-- 爬虫配置 - 选择采集任务 -->
          <template v-if="dataSource === 'crawler'">
            <el-divider />
            <el-form label-position="top" size="small">
              <el-form-item label="选择采集任务">
                <el-select 
                  v-model="selectedTaskId" 
                  placeholder="选择已完成的采集任务"
                  style="width: 100%"
                  :loading="loadingTasks"
                  @change="loadTaskData"
                >
                  <el-option
                    v-for="task in completedTasks"
                    :key="task.id"
                    :label="formatTaskLabel(task)"
                    :value="task.id"
                  >
                    <div class="task-option">
                      <span class="task-keywords">{{ task.keywords?.join(', ') || '热搜' }}</span>
                      <span class="task-meta">
                        <el-tag size="small" type="success">{{ task.collected }}条</el-tag>
                        <span class="task-time">{{ formatTaskTime(task.end_time) }}</span>
                      </span>
                    </div>
                  </el-option>
                </el-select>
                <div class="task-actions">
                  <el-button text size="small" :icon="Refresh" :loading="loadingTasks" @click="loadCrawlTasks">
                    刷新任务列表
                  </el-button>
                  <el-text v-if="crawlTasks.length > 0" type="info" size="small">
                    共 {{ completedTasks.length }} 个已完成任务
                  </el-text>
                </div>
              </el-form-item>
              
              <el-alert 
                v-if="completedTasks.length === 0 && !loadingTasks" 
                title="暂无采集任务" 
                description="请先在「数据采集」模块创建采集任务"
                type="warning" 
                :closable="false"
                show-icon
              />
              
              <el-divider v-if="selectedTaskId">已选任务信息</el-divider>
              <template v-if="selectedTaskId && selectedTaskInfo">
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item label="任务ID">{{ selectedTaskInfo.id?.slice(-12) }}</el-descriptions-item>
                  <el-descriptions-item label="关键词">{{ selectedTaskInfo.keywords?.join(', ') || '热搜' }}</el-descriptions-item>
                  <el-descriptions-item label="数据量">{{ selectedTaskInfo.collected }} 条</el-descriptions-item>
                  <el-descriptions-item label="采集时间">{{ formatTaskTime(selectedTaskInfo.end_time) }}</el-descriptions-item>
                </el-descriptions>
              </template>
            </el-form>
          </template>
          
          <!-- 文件上传 -->
          <template v-if="dataSource === 'file'">
            <el-divider />
            <el-upload
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleFileUpload"
              accept=".json,.csv,.txt"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">拖拽文件到此处或<em>点击上传</em></div>
              <template #tip>
                <div class="el-upload__tip">支持 JSON/CSV/TXT 格式</div>
              </template>
            </el-upload>
          </template>
        </el-card>

        <!-- 清洗规则 -->
        <el-card class="panel-card">
          <template #header><span>数据清洗规则</span></template>
          <el-checkbox-group v-model="cleanRules" class="cleaning-rules">
            <div class="rule-category">
              <h4>基础清洗</h4>
              <div class="rule-item"><el-checkbox label="removeDuplicates">去重</el-checkbox><el-tag size="small" type="info">{{ duplicateCount }} 条</el-tag></div>
              <div class="rule-item"><el-checkbox label="removeNoise">去除噪声</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="normalizeWhitespace">规范空白字符</el-checkbox></div>
            </div>
            
            <div class="rule-category">
              <h4>文本处理</h4>
              <div class="rule-item"><el-checkbox label="traditional2simplified">繁体转简体</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="fullwidth2halfwidth">全角转半角</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="segmentation">中文分词</el-checkbox></div>
            </div>
            
            <div class="rule-category">
              <h4>内容过滤</h4>
              <div class="rule-item"><el-checkbox label="removeStopwords">过滤停用词</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="removeEmoji">移除表情符号</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="removeUrl">移除 URL 链接</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="removeAt">移除 @用户</el-checkbox></div>
              <div class="rule-item"><el-checkbox label="removeHashtag">移除 #话题</el-checkbox></div>
            </div>
          </el-checkbox-group>
        </el-card>

        <!-- 文本规范化 -->
        <el-card class="panel-card">
          <template #header><span>文本规范化</span></template>
          <el-form label-position="top" size="small">
            <el-form-item label="繁简转换">
              <el-switch v-model="normalizeConfig.traditional2simplified" active-text="繁→简" />
              <span class="norm-desc">将繁体字统一转换为简体</span>
            </el-form-item>
            <el-form-item label="全半角转换">
              <el-switch v-model="normalizeConfig.fullwidth2halfwidth" active-text="全→半" />
              <span class="norm-desc">将全角字符转为半角</span>
            </el-form-item>
            <el-form-item label="表情处理方式">
              <el-radio-group v-model="normalizeConfig.emojiMode">
                <el-radio label="remove">直接删除</el-radio>
                <el-radio label="totext">转为文字</el-radio>
                <el-radio label="keep">保留</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
          <div v-if="normalizeConfig.emojiMode === 'totext'" class="emoji-preview">
            <span class="emoji-sample">😊 → [微笑]</span>
            <span class="emoji-sample">😢 → [哭泣]</span>
            <span class="emoji-sample">👍 → [赞]</span>
          </div>
        </el-card>

        <!-- 停用词统计 -->
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>停用词统计</span>
              <div class="header-actions">
                <el-tag size="small">{{ stopwordList.length }} 个</el-tag>
                <el-button size="small" :icon="Setting" @click="showStopWordDialog = true">管理</el-button>
              </div>
            </div>
          </template>
          <div class="stopword-cloud">
            <el-tag
              v-for="sw in stopwordList.slice(0, 30)"
              :key="sw.word"
              size="small"
              :style="{ fontSize: Math.min(16, 10 + sw.count * 0.5) + 'px', opacity: Math.min(1, 0.4 + sw.count * 0.05) }"
              class="sw-tag"
              effect="plain"
            >
              {{ sw.word }} <sup>{{ sw.count }}</sup>
            </el-tag>
          </div>
          <div class="stopword-summary">
            正文中停用词占比: <strong>{{ stopwordRatio }}%</strong>
          </div>
        </el-card>

        <!-- 分词配置 -->
        <el-card class="panel-card">
          <template #header><span>分词处理</span></template>
          <el-form label-position="top" size="small">
            <el-form-item label="分词工具">
              <el-radio-group v-model="segmentTool">
                <el-radio label="jieba">jieba分词</el-radio>
                <el-radio label="hanlp">HanLP</el-radio>
                <el-radio label="pkuseg">pkuseg</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="自定义词典">
              <el-upload action="#" :auto-upload="false" :on-change="handleDictUpload" :show-file-list="false">
                <el-button size="small" :icon="Upload">上传词典</el-button>
              </el-upload>
              <span v-if="customDictName" class="dict-name">{{ customDictName }}</span>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 特征提取 -->
        <el-card class="panel-card">
          <template #header><span>特征提取</span></template>
          <el-form label-position="top" size="small">
            <el-form-item label="提取方法">
              <el-select v-model="extractMethod" style="width: 100%">
                <el-option label="TF-IDF" value="tfidf" />
                <el-option label="Word2Vec" value="word2vec" />
                <el-option label="BERT嵌入" value="bert" />
                <el-option label="FastText" value="fasttext" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="extractMethod !== 'tfidf'" label="向量维度">
              <el-input-number v-model="vectorSize" :min="50" :max="768" style="width: 100%" />
            </el-form-item>
            <el-form-item v-if="extractMethod === 'tfidf'" label="最大特征数">
              <el-input-number v-model="maxFeatures" :min="100" :max="10000" style="width: 100%" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 执行按钮 -->
        <el-button type="primary" size="large" :loading="processing" style="width: 100%; margin-top: 16px" @click="handleProcess">
          <el-icon><Operation /></el-icon>
          开始处理
        </el-button>
        <el-progress v-if="processing" :percentage="progress" :status="progress === 100 ? 'success' : undefined" style="margin-top: 12px" />
      </div>

      <!-- 右侧预览区 -->
      <div class="preview-panel">
        <el-tabs v-model="activePreview" type="border-card">
          <!-- 原始数据 -->
          <el-tab-pane label="原始数据" name="original">
            <div class="data-toolbar">
              <el-input v-model="searchText" placeholder="搜索内容..." :prefix-icon="Search" clearable style="width: 300px" />
              <el-select v-model="sentimentFilter" placeholder="情感筛选" clearable style="width: 120px">
                <el-option label="全部" value="" />
                <el-option label="正面" value="positive" />
                <el-option label="负面" value="negative" />
                <el-option label="中性" value="neutral" />
              </el-select>
              <span class="data-count">显示 {{ filteredData.length }} / {{ rawData.length }} 条</span>
            </div>
            <el-table v-loading="isLoading" :data="paginatedData" :max-height="tableMaxHeight" stripe>
              <el-table-column type="index" width="50" />
              <el-table-column label="内容" min-width="300">
                <template #default="{ row }">
                  <div class="weibo-content">
                    <div class="weibo-text">{{ row.text || row.content }}</div>
                    <div class="weibo-meta">
                      <span v-if="row.screen_name || row.user?.screen_name">@{{ row.screen_name || row.user?.screen_name }}</span>
                      <span v-if="row.created_at">{{ formatTime(row.created_at) }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="互动" width="150">
                <template #default="{ row }">
                  <div class="interaction-stats">
                    <span><el-icon><ChatDotRound /></el-icon>{{ row.comments_count || 0 }}</span>
                    <span><el-icon><Refresh /></el-icon>{{ row.reposts_count || 0 }}</span>
                    <span><el-icon><Star /></el-icon>{{ row.attitudes_count || 0 }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="情感" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.sentiment" :type="getSentimentType(row.sentiment)" size="small">
                    {{ getSentimentLabel(row.sentiment) }}
                  </el-tag>
                  <span v-else class="text-muted">未分析</span>
                </template>
              </el-table-column>
              <el-table-column label="关键词" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.keyword" size="small" type="warning">{{ row.keyword }}</el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="filteredData.length"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              style="margin-top: 16px; justify-content: flex-end"
            />
          </el-tab-pane>

          <!-- 处理对比 -->
          <el-tab-pane label="处理对比" name="compare">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-card header="处理前">
                  <el-select v-model="compareIndex" placeholder="选择数据" style="width: 100%; margin-bottom: 12px">
                    <el-option v-for="(item, idx) in rawData.slice(0, 20)" :key="idx" :label="`第${idx + 1}条: ${item.text?.slice(0, 30)}...`" :value="idx" />
                  </el-select>
                  <div class="compare-text original">{{ compareOriginal }}</div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card header="处理后">
                  <div class="process-steps">
                    <el-tag v-for="rule in cleanRules" :key="rule" size="small" style="margin-right: 4px">{{ getRuleName(rule) }}</el-tag>
                  </div>
                  <div class="compare-text processed">{{ compareProcessed }}</div>
                </el-card>
              </el-col>
            </el-row>
            <el-card header="处理步骤详情" style="margin-top: 16px">
              <el-timeline>
                <el-timeline-item v-for="(step, idx) in processSteps" :key="idx" :timestamp="step.time" :type="step.type">
                  <div class="step-content">
                    <div class="step-title">{{ step.name }}</div>
                    <div class="step-desc">{{ step.description }}</div>
                    <div v-if="step.count" class="step-count">处理了 {{ step.count }} 处</div>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </el-tab-pane>

          <!-- 分词结果 -->
          <el-tab-pane label="分词结果" name="segment">
            <el-row :gutter="16">
              <el-col :span="16">
                <el-card header="分词可视化">
                  <div class="segment-result">
                    <el-tag v-for="(word, idx) in segmentWords" :key="idx" :type="getWordType(word)" class="word-tag" :effect="isStopword(word) ? 'plain' : 'light'">
                      {{ word.word }}<span v-if="word.pos" class="word-pos">/{{ word.pos }}</span>
                    </el-tag>
                  </div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card header="词频统计TOP20">
                  <div ref="wordFreqChartRef" class="mini-chart"></div>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top: 16px">
              <el-col :span="12">
                <el-card header="分词统计">
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="总词数">{{ segmentStats.totalWords }}</el-descriptions-item>
                    <el-descriptions-item label="唯一词数">{{ segmentStats.uniqueWords }}</el-descriptions-item>
                    <el-descriptions-item label="平均词长">{{ segmentStats.avgWordLength }}</el-descriptions-item>
                    <el-descriptions-item label="停用词数">{{ segmentStats.stopwordCount }}</el-descriptions-item>
                    <el-descriptions-item label="名词占比">{{ segmentStats.nounRatio }}%</el-descriptions-item>
                    <el-descriptions-item label="动词占比">{{ segmentStats.verbRatio }}%</el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card header="词性分布">
                  <div ref="posChartRef" class="mini-chart"></div>
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>

          <!-- 特征向量 -->
          <el-tab-pane label="特征向量" name="features">
            <el-alert :title="`特征提取方法: ${extractMethod.toUpperCase()} | 维度: ${extractMethod === 'tfidf' ? maxFeatures : vectorSize}`" type="info" :closable="false" style="margin-bottom: 16px" />
            <el-row :gutter="16">
              <el-col :span="16">
                <el-card header="特征向量预览">
                  <div class="feature-preview">
                    <pre>{{ JSON.stringify(featureVector, null, 2) }}</pre>
                  </div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card header="特征统计">
                  <el-descriptions :column="1" border>
                    <el-descriptions-item label="特征维度">{{ featureStats.dimension }}</el-descriptions-item>
                    <el-descriptions-item label="非零特征">{{ featureStats.nonZero }}</el-descriptions-item>
                    <el-descriptions-item label="稀疏度">{{ featureStats.sparsity }}%</el-descriptions-item>
                    <el-descriptions-item label="最大值">{{ featureStats.maxValue }}</el-descriptions-item>
                    <el-descriptions-item label="最小值">{{ featureStats.minValue }}</el-descriptions-item>
                    <el-descriptions-item label="均值">{{ featureStats.meanValue }}</el-descriptions-item>
                  </el-descriptions>
                </el-card>
                <el-card header="重要特征TOP10" style="margin-top: 16px">
                  <div class="top-features">
                    <div v-for="(feat, idx) in topFeatures" :key="idx" class="feature-item">
                      <span class="feature-name">{{ feat.name }}</span>
                      <el-progress :percentage="feat.importance" :stroke-width="8" :show-text="false" />
                      <span class="feature-value">{{ feat.value.toFixed(4) }}</span>
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>

          <!-- 质量报告 -->
          <el-tab-pane label="质量报告" name="quality">
            <el-row :gutter="16" class="quality-metrics">
              <el-col :span="6">
                <div class="quality-card">
                  <el-progress type="dashboard" :percentage="qualityScore" :width="120" :color="getQualityColor(qualityScore)">
                    <template #default><span class="quality-value">{{ qualityScore }}</span><span class="quality-label">质量评分</span></template>
                  </el-progress>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="quality-card">
                  <el-progress type="dashboard" :percentage="completeness" :width="120" :color="SUCCESS">
                    <template #default><span class="quality-value">{{ completeness }}%</span><span class="quality-label">完整性</span></template>
                  </el-progress>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="quality-card">
                  <el-progress type="dashboard" :percentage="accuracy" :width="120" :color="PRIMARY">
                    <template #default><span class="quality-value">{{ accuracy }}%</span><span class="quality-label">准确性</span></template>
                  </el-progress>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="quality-card">
                  <el-progress type="dashboard" :percentage="consistency" :width="120" :color="WARNING">
                    <template #default><span class="quality-value">{{ consistency }}%</span><span class="quality-label">一致性</span></template>
                  </el-progress>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top: 16px">
              <el-col :span="12">
                <el-card header="发现的问题">
                  <el-table :data="qualityIssues" size="small">
                    <el-table-column prop="type" label="问题类型" width="120" />
                    <el-table-column prop="count" label="数量" width="80" />
                    <el-table-column label="严重程度" width="100">
                      <template #default="{ row }">
                        <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="description" label="描述" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card header="优化建议">
                  <el-timeline>
                    <el-timeline-item v-for="(rec, idx) in recommendations" :key="idx" :type="rec.priority === 'high' ? 'danger' : rec.priority === 'medium' ? 'warning' : 'info'">
                      <div class="recommendation-item">
                        <div class="rec-title">{{ rec.title }}</div>
                        <div class="rec-desc">{{ rec.description }}</div>
                        <el-button v-if="rec.action" size="small" type="primary" @click="applyRecommendation(rec)">应用</el-button>
                      </div>
                    </el-timeline-item>
                  </el-timeline>
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 停用词管理对话框 -->
    <el-dialog v-model="showStopWordDialog" title="停用词管理" width="600px">
      <div class="stopword-management">
        <div class="stopword-actions">
          <el-input
            v-model="newStopWord"
            placeholder="输入要添加的停用词"
            style="width: 200px"
            @keyup.enter="addStopWord"
          >
            <template #append>
              <el-button @click="addStopWord">添加</el-button>
            </template>
          </el-input>
          <el-upload
            action="#"
            :auto-upload="false"
            :on-change="handleStopWordFileUpload"
            :show-file-list="false"
            accept=".txt"
          >
            <el-button :icon="Upload">导入文件</el-button>
          </el-upload>
          <el-button :icon="Download" @click="exportStopWords">导出</el-button>
        </div>
        
        <el-divider />
        
        <div class="stopword-list">
          <el-table :data="stopWords" max-height="300" size="small">
            <el-table-column label="停用词" prop="word" />
            <el-table-column label="出现频次" prop="count" width="100" />
            <el-table-column label="操作" width="100">
              <template #default="{ $index }">
                <el-button size="small" type="danger" @click="removeStopWord($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showStopWordDialog = false">取消</el-button>
        <el-button type="primary" @click="saveStopWords">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 处理对比页的差异高亮开关 -->
    <div v-if="activePreview === 'compare'" class="diff-controls">
      <el-switch
        v-model="showDiffHighlight"
        active-text="高亮差异"
        inactive-text="普通视图"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { SUCCESS, PRIMARY, WARNING, DANGER, INFO } from '@/styles/colors';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Upload, Operation, Refresh, Search, ChatDotRound, Star, Setting, Download,
} from '@element-plus/icons-vue';
import { 
  getHotSearch, 
  searchWeibo, 
  getCrawlTasks, 
  getCrawlTaskData,
  type WeiboData, 
  type HotSearchItem,
  type CrawlTask,
  type CrawlTaskDataResponse
} from '@/api/weibo';

// ==================== 状态定义 ====================
const isLoading = ref(false);
const isCrawling = ref(false);
const processing = ref(false);
const progress = ref(0);
const processTime = ref(0);
const processedCount = ref(0);

// 数据源
const dataSource = ref('sample');
const crawlerKeyword = ref('');
const crawlerSources = ref(['hotsearch', 'search']);
const crawlerPages = ref(3);
const customDictName = ref('');

// 采集任务相关
const crawlTasks = ref<CrawlTask[]>([]);
const selectedTaskId = ref<string>('');
const loadingTasks = ref(false);

// 原始数据
const rawData = ref<WeiboData[]>([]);
const hotSearchData = ref<HotSearchItem[]>([]);

// 清洗规则
const cleanRules = ref(['removeDuplicates', 'removeSpecial', 'removeUrl', 'removeEmoji']);
const segmentTool = ref('jieba');

// 文本规范化配置
const normalizeConfig = reactive({
  traditional2simplified: true,
  fullwidth2halfwidth: true,
  emojiMode: 'remove' as 'remove' | 'totext' | 'keep',
});

// 停用词统计
const STOPWORDS = ['的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '他', '她', '什么', '而', '为', '出', '对', '与', '能', '并', '它', '被', '还', '那', '地', '得'];

const stopwordList = computed(() => {
  const allText = rawData.value.map(d => d.text || '').join(' ');
  const counts: Record<string, number> = {};
  STOPWORDS.forEach(sw => {
    const regex = new RegExp(sw, 'g');
    const matches = allText.match(regex);
    if (matches && matches.length > 0) {
      counts[sw] = matches.length;
    }
  });
  return Object.entries(counts)
    .map(([word, count]) => ({ word, count }))
    .sort((a, b) => b.count - a.count);
});

const stopwordRatio = computed(() => {
  if (rawData.value.length === 0) return 0;
  const allText = rawData.value.map(d => d.text || '').join('');
  const totalChars = allText.length;
  if (totalChars === 0) return 0;
  let swChars = 0;
  stopwordList.value.forEach(sw => { swChars += sw.word.length * sw.count; });
  return Math.min(100, Math.round(swChars / totalChars * 100));
});
const extractMethod = ref('tfidf');
const vectorSize = ref(128);
const maxFeatures = ref(1000);

// 预览
const activePreview = ref('original');
const searchText = ref('');
const sentimentFilter = ref('');
const currentPage = ref(1);
const pageSize = ref(10);
const compareIndex = ref(0);
const windowHeight = ref(window.innerHeight);
const tableMaxHeight = computed(() => Math.max(420, windowHeight.value - 360));

// 
const showStopWordDialog = ref(false);
const newStopWord = ref('');
const stopWords = ref<{word: string, count: number}[]>([]);
const showDiffHighlight = ref(false);

// 图表引用
const wordFreqChartRef = ref<HTMLElement>();
const posChartRef = ref<HTMLElement>();

// ==================== 计算属性 ====================
const duplicateCount = computed(() => {
  const texts = rawData.value.map(d => d.text);
  return texts.length - new Set(texts).size;
});

const filteredData = computed(() => {
  let result = rawData.value;
  if (searchText.value) {
    const keyword = searchText.value.toLowerCase();
    result = result.filter(d => d.text?.toLowerCase().includes(keyword));
  }
  if (sentimentFilter.value) {
    result = result.filter(d => d.sentiment === sentimentFilter.value);
  }
  return result;
});

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredData.value.slice(start, start + pageSize.value);
});

const compareOriginal = computed(() => {
  return rawData.value[compareIndex.value]?.text || '请先加载数据';
});

const compareProcessed = computed(() => {
  let text = compareOriginal.value;
  if (cleanRules.value.includes('removeUrl')) {
    text = text.replace(/https?:\/\/[^\s]+/g, '');
  }
  if (cleanRules.value.includes('removeEmoji')) {
    text = text.replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{2600}-\u{26FF}]/gu, '');
  }
  if (cleanRules.value.includes('removeAt')) {
    text = text.replace(/@[\w\u4e00-\u9fa5]+/g, '');
  }
  if (cleanRules.value.includes('removeHashtag')) {
    text = text.replace(/#[^#]+#/g, '');
  }
  if (cleanRules.value.includes('removeSpecial')) {
    text = text.replace(/[^\w\u4e00-\u9fa5\s]/g, '');
  }
  if (cleanRules.value.includes('normalizeWhitespace')) {
    text = text.replace(/\s+/g, ' ').trim();
  }
  return text || '处理后为空';
});

// 分词结果
const segmentWords = computed(() => {
  const text = compareProcessed.value;
  // 简单模拟分词
  const words = text.split(/\s+/).filter(w => w.length > 0);
  return words.map(w => ({
    word: w,
    pos: getRandomPos(),
  }));
});

const segmentStats = computed(() => {
  const words = segmentWords.value;
  const stopwords = words.filter(w => isStopword(w.word));
  const nouns = words.filter(w => w.pos === 'n');
  const verbs = words.filter(w => w.pos === 'v');
  return {
    totalWords: words.length,
    uniqueWords: new Set(words.map(w => w.word)).size,
    avgWordLength: words.length > 0 ? (words.reduce((sum, w) => sum + w.word.length, 0) / words.length).toFixed(2) : '0',
    stopwordCount: stopwords.length,
    nounRatio: words.length > 0 ? Math.round(nouns.length / words.length * 100) : 0,
    verbRatio: words.length > 0 ? Math.round(verbs.length / words.length * 100) : 0,
  };
});

// 特征向量
const featureVector = computed(() => ({
  method: extractMethod.value.toUpperCase(),
  dimension: extractMethod.value === 'tfidf' ? maxFeatures.value : vectorSize.value,
  sample_vector: Array.from({ length: 10 }, () => Math.random().toFixed(4)),
  sparse: extractMethod.value === 'tfidf',
}));

const featureStats = computed(() => ({
  dimension: extractMethod.value === 'tfidf' ? maxFeatures.value : vectorSize.value,
  nonZero: Math.floor(Math.random() * 200 + 100),
  sparsity: (Math.random() * 30 + 60).toFixed(1),
  maxValue: (Math.random() * 0.5 + 0.5).toFixed(4),
  minValue: (Math.random() * 0.01).toFixed(4),
  meanValue: (Math.random() * 0.1 + 0.05).toFixed(4),
}));

const topFeatures = computed(() => [
  { name: '情感', importance: 85, value: 0.8523 },
  { name: '热度', importance: 72, value: 0.7234 },
  { name: '时间', importance: 65, value: 0.6512 },
  { name: '互动', importance: 58, value: 0.5834 },
  { name: '用户', importance: 45, value: 0.4521 },
]);

// 质量指标
const qualityScore = ref(85);
const completeness = ref(92);
const accuracy = ref(88);
const consistency = ref(85);
// 避免弹窗重复触发的标志：每次从高分（≥90）跌到低分（<80）时只提示一次
const qualityWarned = ref(false);

const qualityIssues = ref([
  { type: '重复数据', count: 0, severity: 'medium', description: '发现重复记录' },
  { type: '空值', count: 0, severity: 'high', description: '部分字段为空' },
  { type: '格式异常', count: 0, severity: 'low', description: '时间格式不统一' },
]);

const recommendations = ref([
  { title: '去除重复数据', description: '建议启用去重规则以提高数据质量', priority: 'high', action: 'removeDuplicates' },
  { title: '清理特殊字符', description: '移除URL和表情符号可提高分析准确性', priority: 'medium', action: 'removeSpecial' },
  { title: '补充缺失值', description: '部分用户信息缺失，建议补充或标记', priority: 'low', action: null },
]);

const processSteps = ref([
  { name: '数据加载', description: '从数据源加载原始数据', time: '0ms', type: 'success', count: 0 },
  { name: '去重处理', description: '移除重复的微博内容', time: '0ms', type: 'success', count: 0 },
  { name: '文本清洗', description: '去除URL、表情、特殊字符', time: '0ms', type: 'success', count: 0 },
  { name: '分词处理', description: '使用jieba进行中文分词', time: '0ms', type: 'success', count: 0 },
  { name: '特征提取', description: '提取TF-IDF特征向量', time: '0ms', type: 'success', count: 0 },
]);

// ==================== 工具函数 ====================
const formatTime = (time: string) => {
  if (!time) return '';
  const date = new Date(time);
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
};

const getSentimentType = (sentiment: string) => {
  const types: Record<string, any> = { positive: 'success', negative: 'danger', neutral: 'info' };
  return types[sentiment] || 'info';
};

const getSentimentLabel = (sentiment: string) => {
  const labels: Record<string, string> = { positive: '正面', negative: '负面', neutral: '中性' };
  return labels[sentiment] || '未知';
};

const getWordType = (word: { word: string; pos: string }) => {
  if (word.pos === 'n') return 'primary';
  if (word.pos === 'v') return 'success';
  if (word.pos === 'a') return 'warning';
  return '';
};

const isStopword = (word: string) => {
  const stopwords = ['的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'];
  return stopwords.includes(word);
};

const getRandomPos = () => {
  const pos = ['n', 'v', 'a', 'd', 'p', 'c', 'u', 'x'];
  return pos[Math.floor(Math.random() * pos.length)];
};

const getRuleName = (rule: string) => {
  const names: Record<string, string> = {
    removeDuplicates: '去重',
    removeSpecial: '去特殊符号',
    removeStopwords: '去停用词',
    removeEmoji: '去表情',
    removeUrl: '去URL',
    removeAt: '去@用户',
    removeHashtag: '去话题',
    normalizeWhitespace: '规范空白',
  };
  return names[rule] || rule;
};

const getSeverityType = (severity: string) => {
  const types: Record<string, any> = { high: 'danger', medium: 'warning', low: 'info' };
  return types[severity] || 'info';
};

const updateQualityMetrics = () => {
  const total = rawData.value.length;
  if (total === 0) return;

  // 完整性：非空text字段比例
  const nonEmpty = rawData.value.filter(d => d.text && d.text.trim().length > 0).length;
  completeness.value = Math.round((nonEmpty / total) * 100);

  // 重复检测
  const textSet = new Set(rawData.value.map(d => d.text));
  const duplicates = total - textSet.size;
  qualityIssues.value[0].count = duplicates;

  // 空值检测
  const nullCount = rawData.value.filter(d => !d.text || !d.user?.screen_name).length;
  qualityIssues.value[1].count = nullCount;

  // 格式异常
  const formatIssues = rawData.value.filter(d => d.created_at && isNaN(Date.parse(d.created_at))).length;
  qualityIssues.value[2].count = formatIssues;

  // 准确性 & 一致性
  accuracy.value = Math.round(((total - nullCount) / total) * 100);
  consistency.value = Math.round(((total - formatIssues) / total) * 100);

  // 综合质量分
  qualityScore.value = Math.round((completeness.value + accuracy.value + consistency.value) / 3);

  // 质量低于 80% 阈值时弹窗告警，引导用户调整预处理规则
  if (qualityScore.value < 80 && !qualityWarned.value) {
    qualityWarned.value = true;
    ElMessageBox.alert(
      `当前数据质量评分 ${qualityScore.value} 分（低于 80 分阈值）。\n\n` +
      `主要问题：\n` +
      `  · 重复数据 ${qualityIssues.value[0].count} 条\n` +
      `  · 空值 ${qualityIssues.value[1].count} 条\n` +
      `  · 格式异常 ${qualityIssues.value[2].count} 条\n\n` +
      `建议启用「去重 + 去噪 + 补全」规则后重新处理。`,
      '数据质量告警',
      { type: 'warning', confirmButtonText: '前往调整规则' }
    ).catch(() => {});
  }
  // 恢复高质量时重置标志
  if (qualityScore.value >= 90) {
    qualityWarned.value = false;
  }
};

const getQualityColor = (score: number) => {
  if (score >= 80) return SUCCESS;
  if (score >= 60) return WARNING;
  return DANGER;
};

// ==================== 数据加载 ====================
const loadSampleData = () => {
  rawData.value = [
    { id: '1', mid: '1', text: '今天天气真好，心情也很不错！😊 #美好生活# http://t.cn/xxx', source: '微博', created_at: new Date().toISOString(), user: { id: '1', screen_name: '快乐小明', followers_count: 1000, friends_count: 500, statuses_count: 200, verified: false, verified_type: -1 }, reposts_count: 23, comments_count: 45, attitudes_count: 128, sentiment: 'positive', sentiment_score: 0.85, crawl_time: new Date().toISOString() },
    { id: '2', mid: '2', text: '这个产品质量太差了，非常失望... @某品牌官方', source: '微博', created_at: new Date().toISOString(), user: { id: '2', screen_name: '消费者小红', followers_count: 500, friends_count: 300, statuses_count: 100, verified: false, verified_type: -1 }, reposts_count: 56, comments_count: 89, attitudes_count: 234, sentiment: 'negative', sentiment_score: -0.72, crawl_time: new Date().toISOString() },
    { id: '3', mid: '3', text: '刚看完这部电影，剧情还可以吧，不功不过', source: '微博', created_at: new Date().toISOString(), user: { id: '3', screen_name: '影评人老王', followers_count: 5000, friends_count: 200, statuses_count: 500, verified: true, verified_type: 0 }, reposts_count: 12, comments_count: 34, attitudes_count: 67, sentiment: 'neutral', sentiment_score: 0.1, crawl_time: new Date().toISOString() },
    { id: '4', mid: '4', text: '强烈推荐这家餐厅！味道超级棒，服务也很好！#美食推荐#', source: '微博', created_at: new Date().toISOString(), user: { id: '4', screen_name: '美食达人', followers_count: 10000, friends_count: 800, statuses_count: 1000, verified: true, verified_type: 0 }, reposts_count: 89, comments_count: 156, attitudes_count: 567, sentiment: 'positive', sentiment_score: 0.92, crawl_time: new Date().toISOString() },
    { id: '5', mid: '5', text: '等了一个小时外卖还没到，差评！客服态度也很差', source: '微博', created_at: new Date().toISOString(), user: { id: '5', screen_name: '普通用户', followers_count: 200, friends_count: 150, statuses_count: 50, verified: false, verified_type: -1 }, reposts_count: 34, comments_count: 67, attitudes_count: 123, sentiment: 'negative', sentiment_score: -0.85, crawl_time: new Date().toISOString() },
  ] as WeiboData[];
  updateQualityMetrics();
};

const handleDataSourceChange = async () => {
  rawData.value = [];
  selectedTaskId.value = '';
  
  if (dataSource.value === 'sample') {
    loadSampleData();
  } else if (dataSource.value === 'crawler') {
    // 自动加载采集任务列表
    await loadCrawlTasks();
  }
};

// ==================== 采集任务相关 ====================

// 已完成的采集任务
const completedTasks = computed(() => {
  return crawlTasks.value.filter(t => t.status === 'completed');
});

// 当前选中的任务信息
const selectedTaskInfo = computed(() => {
  return crawlTasks.value.find(t => t.id === selectedTaskId.value);
});

// 加载采集任务列表
const loadCrawlTasks = async () => {
  loadingTasks.value = true;
  try {
    const response = await getCrawlTasks();
    crawlTasks.value = response.tasks;
    
    // 自动选择最新的已完成任务
    const latestCompleted = response.tasks.find(t => t.status === 'completed');
    if (latestCompleted && !selectedTaskId.value) {
      selectedTaskId.value = latestCompleted.id;
      await loadTaskData(); // 自动加载数据
    }
    
    if (response.completed > 0) {
      ElMessage.success(`找到 ${response.completed} 个已完成的采集任务`);
    } else if (response.running > 0) {
      ElMessage.info(`有 ${response.running} 个任务正在运行中`);
    }
  } catch (e: any) {
    console.error('加载任务列表失败:', e);
    ElMessage.warning('加载任务列表失败');
  } finally {
    loadingTasks.value = false;
  }
};

// 加载选中任务的数据
const loadTaskData = async () => {
  if (!selectedTaskId.value) return;
  
  isLoading.value = true;
  try {
    const response = await getCrawlTaskData(selectedTaskId.value, 1, 1000);
    rawData.value = response.items;
    
    ElMessage.success(`已加载 ${response.items.length} 条采集数据`);
    updateQualityMetrics();
  } catch (e: any) {
    console.error('加载任务数据失败:', e);
    ElMessage.warning('加载任务数据失败: ' + (e.message || '未知错误'));
  } finally {
    isLoading.value = false;
  }
};

// 格式化任务标签
const formatTaskLabel = (task: CrawlTask) => {
  const keywords = task.keywords?.join(', ') || '热搜';
  return `${keywords} (${task.collected}条)`;
};

// 格式化任务时间
const formatTaskTime = (timeStr?: string) => {
  if (!timeStr) return '未知';
  try {
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', { 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  } catch {
    return timeStr;
  }
};

const refreshData = async () => {
  if (dataSource.value === 'crawler') {
    if (selectedTaskId.value) {
      await loadTaskData();
    } else {
      await loadCrawlTasks();
    }
  } else if (dataSource.value === 'sample') {
    loadSampleData();
  }
};

const fetchHotSearch = async () => {
  isLoading.value = true;
  try {
    hotSearchData.value = await getHotSearch();
    ElMessage.success(`获取到 ${hotSearchData.value.length} 条热搜`);
  } catch (e: any) {
    ElMessage.warning('获取热搜失败，使用模拟数据');
    // 模拟热搜数据
    hotSearchData.value = [
      { rank: 1, title: '春节档电影票房', hot_value: 9876543, category: '娱乐', crawl_time: new Date().toISOString() },
      { rank: 2, title: '科技创新成果', hot_value: 8765432, category: '科技', crawl_time: new Date().toISOString() },
      { rank: 3, title: '健康生活方式', hot_value: 7654321, category: '健康', crawl_time: new Date().toISOString() },
    ];
  } finally {
    isLoading.value = false;
  }
};

const startCrawl = async () => {
  if (!crawlerKeyword.value && !crawlerSources.value.includes('hotsearch')) {
    ElMessage.warning('请输入关键词或选择热搜数据源');
    return;
  }
  
  isCrawling.value = true;
  isLoading.value = true;
  
  try {
    const keywords = crawlerKeyword.value.split(/[,，]/).map(k => k.trim()).filter(k => k);
    
    // 获取热搜
    if (crawlerSources.value.includes('hotsearch')) {
      await fetchHotSearch();
    }
    
    // 搜索关键词
    if (keywords.length > 0) {
      for (const keyword of keywords) {
        const result = await searchWeibo(keyword, 1, 'all', true);
        rawData.value.push(...result.data);
      }
    }
    
    // 如果没有数据，使用模拟数据
    if (rawData.value.length === 0) {
      loadSampleData();
      ElMessage.info('爬虫暂不可用，已加载示例数据');
    } else {
      ElMessage.success(`成功获取 ${rawData.value.length} 条微博数据`);
    }
    
    updateQualityMetrics();
  } catch (e: any) {
    ElMessage.warning('爬取失败，使用示例数据');
    loadSampleData();
  } finally {
    isCrawling.value = false;
    isLoading.value = false;
  }
};

const handleFileUpload = (file: any) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const content = e.target?.result as string;
      if (file.name.endsWith('.json')) {
        const data = JSON.parse(content);
        rawData.value = Array.isArray(data) ? data : [data];
      } else {
        // CSV或TXT，按行解析
        const lines = content.split('\n').filter(l => l.trim());
        rawData.value = lines.map((line, idx) => ({
          id: String(idx),
          mid: String(idx),
          text: line,
          source: '文件导入',
          created_at: new Date().toISOString(),
          user: { id: '0', screen_name: '未知', followers_count: 0, friends_count: 0, statuses_count: 0, verified: false, verified_type: -1 },
          reposts_count: 0,
          comments_count: 0,
          attitudes_count: 0,
          crawl_time: new Date().toISOString(),
        })) as WeiboData[];
      }
      ElMessage.success(`成功导入 ${rawData.value.length} 条数据`);
      updateQualityMetrics();
    } catch (err) {
      ElMessage.warning('文件解析失败');
    }
  };
  reader.readAsText(file.raw);
};

const handleDictUpload = async (file: any) => {
  try {
    const formData = new FormData();
    formData.append('dictionary', file.raw);
    
    const response = await fetch('/api/preprocess/upload-dictionary', {
      method: 'POST',
      body: formData
    });
    
    if (response.ok) {
      customDictName.value = file.name;
      ElMessage.success(`词典 ${file.name} 上传并加载成功`);
    } else {
      throw new Error('Upload failed');
    }
  } catch (error) {
    ElMessage.warning('词典上传失败');
    console.error('Dictionary upload error:', error);
  }
};

// ==================== 
const handleProcess = async () => {
  if (rawData.value.length === 0) {
    ElMessage.warning('请先加载数据');
    return;
  }
  
  try {
    processing.value = true;
    progress.value = 0;
    const startTime = Date.now();
    
    // 
    const response = await fetch('/api/preprocess/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data: rawData.value,
        rules: cleanRules.value,
        config: normalizeConfig,
        segment_tool: segmentTool.value,
        custom_dict: customDictName.value,
        stopwords: stopWords.value.map(sw => sw.word)
      })
    });
    
    const result = await response.json();
    const jobId = result.job_id;
    
    // 
    const pollProgress = async () => {
      try {
        const statusResponse = await fetch(`/api/preprocess/status/${jobId}`);
        const status = await statusResponse.json();
        
        progress.value = status.progress || 0;
        
        if (status.status === 'completed') {
          processedCount.value = status.processed_count || rawData.value.length;
          processTime.value = Date.now() - startTime;
          processing.value = false;
          
          // 
          if (status.processed_data) {
            // 
            processSteps.value = status.steps || processSteps.value;
          }
          
          ElMessage.success('数据处理完成');
          initCharts();
        } else if (status.status === 'failed') {
          processing.value = false;
          ElMessage.warning(`处理失败：${status.error || '未知错误'}`);
        } else {
          // 
          setTimeout(pollProgress, 1000);
        }
      } catch (error) {
        console.error('Error polling progress:', error);
        setTimeout(pollProgress, 2000);
      }
    };
    
    // 
    pollProgress();
    
  } catch (error) {
    processing.value = false;
    ElMessage.warning('启动处理失败');
    console.error('Processing error:', error);
  }
};

const addStopWord = () => {
  if (newStopWord.value.trim() && !stopWords.value.find(sw => sw.word === newStopWord.value.trim())) {
    stopWords.value.push({ word: newStopWord.value.trim(), count: 0 });
    newStopWord.value = '';
    ElMessage.success('已添加停用词');
  }
};

const removeStopWord = (index: number) => {
  stopWords.value.splice(index, 1);
  ElMessage.success('已移除停用词');
};

const handleStopWordFileUpload = (file: any) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const content = e.target?.result as string;
      const words = content.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(word => ({ word, count: 0 }));
      
      // 
      const existingWords = stopWords.value.map(sw => sw.word);
      const newWords = words.filter(w => !existingWords.includes(w.word));
      stopWords.value.push(...newWords);
      
      ElMessage.success(`已导入 ${newWords.length} 个停用词`);
    } catch (err) {
      ElMessage.warning('文件解析失败');
    }
  };
  reader.readAsText(file.raw);
};

const exportStopWords = () => {
  const content = stopWords.value.map(sw => sw.word).join('\n');
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'stopwords.txt';
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success('停用词已导出');
};

const saveStopWords = async () => {
  try {
    // 
    await fetch('/api/preprocess/stopwords', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stopwords: stopWords.value.map(sw => sw.word) })
    });
    ElMessage.success('停用词保存成功');
    showStopWordDialog.value = false;
  } catch (error) {
    ElMessage.warning('停用词保存失败');
  }
};

const applyRecommendation = (rec: any) => {
  if (rec.action && !cleanRules.value.includes(rec.action)) {
    cleanRules.value.push(rec.action);
    ElMessage.success(`已应用建议：${rec.title}`);
  }
};

// ==================== 图表 ====================
const initCharts = () => {
  nextTick(() => {
    // 词频图表
    if (wordFreqChartRef.value) {
      const chart = echarts.init(wordFreqChartRef.value);
      chart.setOption({
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: ['情感', '分析', '微博', '数据', '用户', '热度', '话题', '评论', '转发', '点赞'].reverse() },
        series: [{ type: 'bar', data: [120, 98, 87, 76, 65, 54, 43, 32, 21, 10], itemStyle: { color: PRIMARY } }],
      });
    }
    
    // 词性分布图表
    if (posChartRef.value) {
      const chart = echarts.init(posChartRef.value);
      chart.setOption({
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          data: [
            { value: 35, name: '名词', itemStyle: { color: PRIMARY } },
            { value: 25, name: '动词', itemStyle: { color: SUCCESS } },
            { value: 20, name: '形容词', itemStyle: { color: WARNING } },
            { value: 20, name: '其他', itemStyle: { color: INFO } },
          ],
        }],
      });
    }
  });
};

// ==================== 生命周期 ====================
onMounted(async () => {
  // 默认使用爬虫数据源（从数据库加载）
  dataSource.value = 'crawler';
  
  // 自动加载采集任务列表
  await loadCrawlTasks();
  
  // 如果没有任务，降级到示例数据
  if (completedTasks.value.length === 0) {
    dataSource.value = 'sample';
    loadSampleData();
  }
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.preprocess-module {
  padding: $spacing-md;
  background: $bg-page;
  min-height: calc(100vh - 120px);
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-base $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  margin-bottom: $spacing-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  .status-left {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    h2 { margin: 0; font-size: $font-size-extra-large; }
  }
  
  .status-right {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }
}

.preprocess-layout {
  display: flex;
  gap: $spacing-base;
  align-items: flex-start;
}

.operation-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.panel-card {
  :deep(.el-card__header) {
    padding: 12px 16px;
    font-weight: 500;
  }
  :deep(.el-card__body) {
    padding: 16px;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.rule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.dict-name {
  margin-left: $spacing-xs;
  color: $success-color;
  font-size: $font-size-extra-small;
}

.preview-panel {
  flex: 1;
  min-width: 0;
  position: sticky;
  top: $spacing-base;
}

.data-toolbar {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-base;
  .data-count {
    margin-left: auto;
    color: $text-secondary;
    font-size: $font-size-small;
  }
}

.weibo-content {
  .weibo-text { line-height: 1.6; }
  .weibo-meta {
    margin-top: $spacing-xxs;
    font-size: $font-size-extra-small;
    color: $text-secondary;
    display: flex;
    gap: $spacing-sm;
  }
}

.interaction-stats {
  display: flex;
  gap: $spacing-sm;
  font-size: $font-size-extra-small;
  color: $text-regular;
  span { display: flex; align-items: center; gap: $spacing-xxs; }
}

.text-muted { color: $text-secondary; }

.compare-text {
  padding: $spacing-base;
  border-radius: $border-radius-base;
  min-height: 150px;
  line-height: 1.8;
  font-size: $font-size-base;
  &.original { background: rgba($danger-color, 0.06); }
  &.processed { background: rgba($success-color, 0.06); }
}

.process-steps {
  margin-bottom: 12px;
}

.step-content {
  .step-title { font-weight: $font-weight-medium; }
  .step-desc { font-size: $font-size-extra-small; color: $text-secondary; }
  .step-count { font-size: $font-size-extra-small; color: $primary-color; margin-top: $spacing-xxs; }
}

.segment-result {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  padding: $spacing-base;
  background: $bg-page;
  border-radius: $border-radius-base;
  min-height: 150px;
}

.word-tag {
  .word-pos { font-size: 10px; color: $text-secondary; margin-left: 2px; }
}

.mini-chart {
  height: 200px;
}

.feature-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: $spacing-base;
  border-radius: $border-radius-base;
  font-family: monospace;
  font-size: $font-size-extra-small;
  max-height: 300px;
  overflow: auto;
  pre { margin: 0; }
}

.top-features {
  .feature-item {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    margin-bottom: $spacing-xs;
    .feature-name { width: 50px; font-size: $font-size-extra-small; }
    .el-progress { flex: 1; }
    .feature-value { width: 60px; font-size: $font-size-extra-small; color: $text-secondary; text-align: right; }
  }
}

.quality-metrics {
  .quality-card {
    text-align: center;
    padding: $spacing-md;
    background: $bg-white;
    border-radius: $border-radius-base;
    .quality-value { font-size: 24px; font-weight: $font-weight-semibold; display: block; }
    .quality-label { font-size: $font-size-extra-small; color: $text-secondary; }
  }
}

.recommendation-item {
  .rec-title { font-weight: $font-weight-medium; margin-bottom: $spacing-xxs; }
  .rec-desc { font-size: $font-size-extra-small; color: $text-secondary; margin-bottom: $spacing-xs; }
}

// 采集任务选择样式
.task-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  
  .task-keywords {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .task-meta {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    
    .task-time {
      font-size: $font-size-extra-small;
      color: $text-secondary;
    }
  }
}

.task-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.norm-desc {
  display: block;
  font-size: $font-size-tiny;
  color: $text-secondary;
  margin-top: 2px;
}

.emoji-preview {
  display: flex;
  gap: $spacing-sm;
  padding: $spacing-xs;
  background: rgba($warning-color, 0.08);
  border-radius: $border-radius-small;
  margin-top: $spacing-xxs;

  .emoji-sample {
    font-size: $font-size-extra-small;
    color: $warning-color;
  }
}

.stopword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: $spacing-xs 0;

  .sw-tag {
    cursor: default;
    sup {
      font-size: 9px;
      color: $text-placeholder;
      margin-left: 2px;
    }
  }
}

.stopword-summary {
  margin-top: $spacing-xs;
  font-size: $font-size-extra-small;
  color: $text-regular;
  text-align: center;
  padding: 6px;
  background: $bg-page;
  border-radius: $border-radius-xs;

  strong {
    color: $warning-color;
    font-size: $font-size-base;
  }
}

// 
.cleaning-rules {
  .rule-category {
    margin-bottom: 16px;
    
    h4 {
      margin: 0 0 8px 0;
      font-size: $font-size-base;
      color: $text-primary;
      border-bottom: 1px solid $border-lighter;
      padding-bottom: 4px;
    }
  }
}

// 
.stopword-management {
  .stopword-actions {
    display: flex;
    gap: $spacing-sm;
    align-items: center;
    margin-bottom: $spacing-base;
  }
  
  .stopword-list {
    max-height: 300px;
    overflow-y: auto;
  }
}

// 
.diff-controls {
  position: sticky;
  top: 0;
  background: $bg-white;
  padding: $spacing-base;
  border-bottom: 1px solid $border-base;
  z-index: 10;
  display: flex;
  justify-content: center;
}

// 
.header-actions {
  display: flex;
  gap: $spacing-xs;
  align-items: center;
}
</style>
