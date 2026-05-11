# 第6章 系统实现

本章按照第五章的系统设计方案，基于Vue 3 + Element Plus前端框架、Spring Boot + Flask双后端架构以及Spark大数据处理引擎，完成各功能模块的编码实现。下面分模块介绍系统的功能设计、界面实现和核心代码。

## 6.1 注册登录模块

用户通过注册页面创建账号，填写邮箱并获取验证码后设置用户名和密码。登录时，前端将用户名和密码通过Ajax请求发送至Spring Boot后端的`/auth/login`接口，后端通过Spring Security进行身份认证，验证通过后生成JWT令牌返回前端。前端将令牌存储于本地，后续所有请求均在请求头中携带该令牌。系统采用Guava缓存记录登录失败次数，超过5次将锁定账户10分钟，防止暴力破解。具体流程如图6-1所示。

图6-1 注册登录流程图

注册登录页面采用左右分栏布局，左侧展示系统品牌信息和核心功能特性，右侧为表单输入区域。登录页面提供密码可见切换和密码强度实时指示功能，支持账号（学号/手机/邮箱）和密码登录。注册页面包含邮箱验证码校验环节，确保注册用户身份的真实性。登录成功后系统自动跳转至首页仪表盘，如图6-2和图6-3所示。

图6-2 用户登录页面
图6-3 用户注册页面

平台注册登录模块的部分核心代码如下：

```java
// AuthServiceImpl.java — 登录认证核心逻辑
@Override
public LoginResponse login(LoginRequest loginRequest) {
    String username = loginRequest.getUsername();
    checkLoginAttempts(username);
    try {
        Authentication authentication = authenticationManager.authenticate(
            new UsernamePasswordAuthenticationToken(username, loginRequest.getPassword())
        );
        SecurityContextHolder.getContext().setAuthentication(authentication);
        loginAttemptCache.invalidate(username);
        String accessToken = tokenProvider.generateToken(authentication);
        return new LoginResponse(accessToken, "Bearer");
    } catch (Exception e) {
        incrementLoginAttempts(username);
        throw new BusinessException("Invalid username or password");
    }
}

@Override
public void register(LoginRequest loginRequest) {
    if (userRepository.findByUsername(loginRequest.getUsername()).isPresent()) {
        throw new BusinessException("Username is already taken!");
    }
    User user = new User();
    user.setUsername(loginRequest.getUsername());
    user.setPassword(passwordEncoder.encode(loginRequest.getPassword()));
    user.setRoles("ROLE_USER");
    user.setStatus("ACTIVE");
    userRepository.save(user);
}
```

## 6.2 系统首页仪表盘模块

系统首页为数据概览仪表盘，以指标卡片形式展示微博总量、情感分布和用户数等核心统计数据，并提供情感分布饼图和实时数据流两个核心可视化组件。仪表盘数据通过定时轮询后端API获取，支持按"今日/本周/本月"切换统计周期。实时数据流模块以时间线形式展示最新采集的微博及其情感标签，使用户进入系统即可掌握当前舆情全貌。具体流程如图6-4所示。

图6-4 首页仪表盘数据加载流程图

首页仪表盘页面由四个指标卡片和两列图表组成，上方卡片展示微博总量、正面/中性/负面情感数量及趋势变化，下方左侧为ECharts情感分布饼图，右侧为实时数据流时间线，如图6-5所示。

图6-5 系统首页仪表盘页面

系统首页仪表盘模块的部分核心代码如下：

```vue
<!-- Dashboard.vue — 指标卡片与情感分布图 -->
<div class="metric-grid">
  <div v-for="(card, idx) in overviewCards" :key="card.title" class="metric-card">
    <div class="metric-icon-wrap" :style="{ background: card.color + '14' }">
      <i :class="card.icon" :style="{ color: card.color }"></i>
    </div>
    <div class="metric-body">
      <span class="metric-label">{{ card.title }}</span>
      <span class="metric-value">{{ formatNumber(card.value) }}</span>
      <span class="metric-trend" :class="card.trendClass">
        <i :class="card.trendIcon"></i>{{ card.trend }}
      </span>
    </div>
  </div>
</div>
```

## 6.3 数据采集模块

数据采集模块实现微博数据的自动化采集，支持关键词搜索采集和热搜榜爬取两种模式。用户在采集配置面板中输入关键词、设置采集页数，点击"启动完整流水线"后，系统依次执行数据采集→数据清洗→情感分析→三维度排序→结果入库五个阶段。采集过程中，前端通过轮询机制实时显示流水线各阶段进度和状态（pending→crawling→cleaning→analyzing→ranking→storing→completed），支持暂停和停止操作。具体流程如图6-6所示。

图6-6 数据采集流水线流程图

数据采集页面顶部为流水线阶段可视化进度条，直观展示当前执行阶段；中部为操作按钮组（启动/暂停/停止/配置）和实时状态信息；下方展示采集日志和已采集数据列表，如图6-7所示。

图6-7 数据采集模块页面

数据采集模块的部分核心代码如下：

```python
# crawler/weibo_crawler.py — 微博数据采集核心逻辑
async def crawl_keyword(self, keyword: str, pages: int = 3):
    """按关键词采集微博数据"""
    all_weibos = []
    for page in range(1, pages + 1):
        url = f"https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100103type=1&q={keyword}", "page": page}
        response = await self.session.get(url, params=params, headers=self.headers)
        data = response.json()
        cards = data.get("data", {}).get("cards", [])
        for card in cards:
            mblog = card.get("mblog", {})
            if mblog:
                weibo = self._parse_weibo(mblog)
                all_weibos.append(weibo)
        await asyncio.sleep(random.uniform(2, 5))  # 反爬延迟
    return all_weibos
```

## 6.4 数据预处理模块

数据预处理模块对采集的原始微博文本进行标准化清洗，包括去除HTML标签、URL链接、@提及、多余空白字符，以及繁简体转换和jieba分词等操作。预处理支持三种数据源：实时爬虫数据、本地文件上传和内置示例数据。处理完成后展示数据总量、已处理数量和处理耗时统计，用户可选择不同清洗规则组合并预览处理前后的文本对比效果。具体流程如图6-8所示。

图6-8 数据预处理流程图

数据预处理页面采用左右分栏布局，左侧为操作面板（数据源选择、清洗规则配置），右侧展示原始数据与处理后数据的对比表格，顶部状态栏实时显示数据总量、已处理数量和耗时，如图6-9所示。

图6-9 数据预处理模块页面

数据预处理模块的部分核心代码如下：

```python
# core/spark_engine.py — Spark数据清洗引擎
def clean_text(self, text: str) -> str:
    """文本清洗流水线"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)           # 去除HTML标签
    text = re.sub(r'http\S+|www\.\S+', '', text)  # 去除URL
    text = re.sub(r'@[\w\u4e00-\u9fff]+', '', text)  # 去除@提及
    text = re.sub(r'#([^#]+)#', r'\1', text)      # 提取话题文本
    text = re.sub(r'\s+', ' ', text).strip()       # 合并空白
    return text
```

## 6.5 情感分析模块

情感分析模块是系统的核心功能，采用自适应级联融合策略（见第四章图4-3），结合词典规则分析和ChineseBERT深度学习模型对微博文本进行情感判定。页面顶部以统计卡片展示总分析数、正面/中性/负面数量及占比和平均得分；中部支持单条文本输入实时分析和批量分析两种模式；分析结果包含情感极性、得分、置信度及词典和BERT的分项得分对比，便于用户理解判定依据。具体流程如图6-10所示。

图6-10 情感分析模块处理流程图

情感分析页面上方为五个统计指标卡片（总分析数、正面、中性、负面、平均得分），中部为文本输入区和分析模式切换（词典/BERT/混合），下方展示分析结果表格及得分分布图表，如图6-11所示。

图6-11 情感分析模块页面

情感分析模块的部分核心代码如下：

```python
# services/hybrid_analyzer.py — 自适应级联融合核心逻辑
def _fuse_results(self, text, rule_result, bert_result):
    """融合词典和BERT分析结果"""
    if self.config.fusion_method == 'adaptive':
        rule_weight, bert_weight = self._calculate_adaptive_weights(
            text, rule_result, bert_result
        )
    else:
        rule_weight, bert_weight = self.online_learner.get_current_weights()
    rule_score = rule_result.get('score', 0.0)
    bert_score = bert_result.get('score', 0.0)
    final_score = rule_weight * rule_score + bert_weight * bert_score
    # 一致性校验
    consistency = (rule_result.get('polarity') == bert_result.get('label'))
    base_confidence = rule_weight * rule_result.get('confidence', 0.5) \
                    + bert_weight * bert_result.get('confidence', 0.5)
    confidence = min(1.0, base_confidence + 0.1) if consistency \
                 else max(0.0, base_confidence - 0.1)
    polarity, label = self._determine_polarity(final_score)
    return HybridResult(text=text, score=final_score, polarity=polarity,
                        label=label, confidence=confidence, ...)
```

## 6.6 三维度排序模块

三维度排序模块实现了情感强度、互动热度和时效性的综合排序（见第四章图4-4）。页面左侧展示三维度权重配置面板和排序公式，用户可通过滑块实时调整ω₁、ω₂、ω₃三个权重参数（约束ω₁+ω₂+ω₃=1），并提供"默认配置""情感优先""热度优先"三种预设方案。右侧以四象限散点图展示分析结果，X轴为热度、Y轴为情感强度，气泡大小表示综合得分，帮助用户直观识别高情感高热度的重点关注内容。具体流程如图6-12所示。

图6-12 三维度排序模块处理流程图

三维度排序页面左侧为公式卡片和权重配置滑块面板，右侧为ECharts四象限散点图和排序结果表格，顶部提供"开始分析""参数配置""导出数据"操作按钮，如图6-13所示。

图6-13 三维度排序模块页面

三维度排序模块的部分核心代码如下：

```python
# spark/tri_dimension_model_v2.py — 三维度综合得分计算
def calculate_tri_score(self, sentiment_normalized, heat_normalized,
                        time_decay_factor=1.0):
    """Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(Δt)"""
    return (
        self.config.sentiment_weight * sentiment_normalized +
        self.config.heat_weight * heat_normalized +
        self.config.timeliness_weight * time_decay_factor
    )

@staticmethod
def calculate_time_decay(created_at, reference_time, config):
    """时间衰减: γ(Δt) = 2^(-Δt/H), H=12小时"""
    time_diff_hours = (reference_time - created_at).total_seconds() / 3600
    decay_constant = math.log(2) / config.decay_half_life_hours
    return math.exp(-decay_constant * max(0, time_diff_hours))
```

## 6.7 实时监控模块

实时监控模块通过WebSocket长连接实现舆情数据的实时推送与展示。前端与Spring Boot后端建立WebSocket连接后，新采集或分析完成的微博数据将自动推送至页面。页面中央为数据流时间线，按时间倒序展示每条微博的用户头像、内容摘要、情感标签和互动数据；支持按情感类型（全部/正面/负面）筛选和自动滚动；右侧面板展示连接状态指示灯和实时统计数据。具体流程如图6-14所示。

图6-14 实时监控模块数据流程图

实时监控页面中央为数据流时间线卡片，每条数据以情感颜色标记（正面绿色、负面红色），顶部显示WebSocket连接状态和数据来源标签，支持按关键词分Tab展示，如图6-15所示。

图6-15 实时监控模块页面

实时监控模块的部分核心代码如下：

```java
// WebSocketHandler.java — WebSocket消息推送
@ServerEndpoint("/ws/monitor")
public class WeiboWebSocketHandler {
    private static final Set<Session> sessions =
        Collections.synchronizedSet(new HashSet<>());

    @OnOpen
    public void onOpen(Session session) {
        sessions.add(session);
    }

    public static void broadcast(String message) {
        sessions.forEach(session -> {
            if (session.isOpen()) {
                session.getAsyncRemote().sendText(message);
            }
        });
    }
}
```

## 6.8 数据可视化模块

数据可视化模块提供六类可视化视图：舆情概览、情感分析、热点话题、用户画像、实时监控和传播路径。页面顶部通过Radio按钮组切换视图，支持按日期范围筛选数据。舆情概览以指标卡片和趋势折线图展示全局态势；情感分析视图提供情感分布饼图和得分直方图；热点话题视图以词云形式展示高频关键词；传播路径视图以力导向图展示信息传播网络。所有图表支持导出为PNG、PDF或Excel格式。具体流程如图6-16所示。

图6-16 数据可视化模块流程图

数据可视化页面顶部为视图切换按钮组和日期选择器，主体区域根据所选视图动态渲染对应ECharts图表，右上角提供全屏和导出功能，如图6-17所示。

图6-17 数据可视化模块页面

数据可视化模块的部分核心代码如下：

```vue
<!-- VisualizationDashboard.vue — 视图切换与图表渲染 -->
<el-radio-group v-model="currentDashboard" @change="handleDashboardChange">
  <el-radio-button label="overview">舆情概览</el-radio-button>
  <el-radio-button label="sentiment">情感分析</el-radio-button>
  <el-radio-button label="topics">热点话题</el-radio-button>
  <el-radio-button label="users">用户画像</el-radio-button>
  <el-radio-button label="realtime">实时监控</el-radio-button>
  <el-radio-button label="propagation">传播路径</el-radio-button>
</el-radio-group>
<el-dropdown @command="handleExport">
  <template #dropdown>
    <el-dropdown-item command="png">导出为图片</el-dropdown-item>
    <el-dropdown-item command="pdf">导出为PDF</el-dropdown-item>
    <el-dropdown-item command="excel">导出数据</el-dropdown-item>
  </template>
</el-dropdown>
```

## 6.9 系统管理模块

系统管理模块面向管理员角色，提供用户管理、任务日志和系统配置三个功能Tab。用户管理支持用户搜索、按状态和角色筛选、添加用户、禁用/启用账户和角色分配操作；任务日志以表格形式记录所有采集和分析任务的执行时间、状态和结果；系统配置页面允许管理员调整采集频率、模型参数等运行参数。该模块通过路由守卫实现权限控制，仅管理员角色可访问。具体流程如图6-18所示。

图6-18 系统管理模块流程图

系统管理页面以Tab面板切换三个子模块，用户管理页包含搜索筛选栏、统计卡片（总用户数/正常/禁用/管理员数量）和用户数据表格，支持行内编辑和批量操作，如图6-19所示。

图6-19 系统管理模块页面

系统管理模块的部分核心代码如下：

```java
// AdminController.java — 用户管理接口
@RestController
@RequestMapping("/admin")
public class AdminController {
    @GetMapping("/users")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseResult<Map<String, Object>> listUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<User> userPage = userRepository.findAll(
            PageRequest.of(page, size, Sort.by("createdAt").descending()));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("users", userPage.getContent());
        result.put("total", userPage.getTotalElements());
        return ResponseResult.success(result);
    }
}
```

## 6.10 本章小结

本章完成了微博舆情情感分析系统9个功能模块的编码实现：注册登录、首页仪表盘、数据采集、数据预处理、情感分析、三维度排序、实时监控、数据可视化和系统管理。前端基于Vue 3和Element Plus构建响应式交互界面，后端采用Spring Boot处理用户认证和WebSocket通信、Flask处理数据采集和情感分析业务逻辑的双后端架构。系统通过JWT令牌实现双后端统一认证，通过Spark引擎实现大规模数据清洗和处理，通过ECharts实现丰富的可视化展示。各模块功能完整，界面交互流畅，满足系统需求分析中提出的各项功能要求。
