/**
 * 前端数据连通性测试脚本
 * 运行: node test-connectivity.js
 */

const http = require('http');
const https = require('https');

const API_BASE = 'http://localhost:5000/api';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// HTTP请求封装
function request(url, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || 80,
      path: urlObj.pathname + urlObj.search,
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000,
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        try {
          resolve({
            status: res.statusCode,
            data: JSON.parse(body),
          });
        } catch {
          resolve({
            status: res.statusCode,
            data: body,
          });
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });

    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

// 测试用例
const tests = [
  {
    name: '1. 热搜API连通性 (GET /analysis/hot-search/live)',
    url: `${API_BASE}/analysis/hot-search/live`,
    method: 'GET',
    validate: (res) => res.status === 200 && res.data.success,
  },
  {
    name: '2. 热搜备用API (GET /weibo/hotsearch)',
    url: `${API_BASE}/weibo/hotsearch`,
    method: 'GET',
    validate: (res) => res.status === 200,
  },
  {
    name: '3. 双维度排序API (GET /topics/ranked)',
    url: `${API_BASE}/topics/ranked`,
    method: 'GET',
    validate: (res) => res.status === 200,
  },
  {
    name: '4. 双维度配置API (GET /topics/dual-dimension/config)',
    url: `${API_BASE}/topics/dual-dimension/config`,
    method: 'GET',
    validate: (res) => res.status === 200,
  },
  {
    name: '5. 情感分析API (POST /sentiment/analyze)',
    url: `${API_BASE}/sentiment/analyze`,
    method: 'POST',
    data: { text: '这是一个测试文本，用于验证情感分析功能' },
    validate: (res) => res.status === 200,
  },
  {
    name: '6. 数据采集API (POST /weibo/collect)',
    url: `${API_BASE}/weibo/collect`,
    method: 'POST',
    data: { keywords: ['测试'], pages: 1, crawl_hot: false },
    validate: (res) => res.status === 200 || res.status === 201,
  },
  {
    name: '7. 数据流概览API (GET /weibo/dataflow/overview)',
    url: `${API_BASE}/weibo/dataflow/overview`,
    method: 'GET',
    validate: (res) => res.status === 200,
  },
  {
    name: '8. Spark状态API (GET /weibo/spark/info)',
    url: `${API_BASE}/weibo/spark/info`,
    method: 'GET',
    validate: (res) => res.status === 200,
  },
];

async function runTests() {
  log('cyan', '\n========================================');
  log('cyan', '   前端数据连通性测试');
  log('cyan', '========================================\n');

  let passed = 0;
  let failed = 0;
  const results = [];

  for (const test of tests) {
    process.stdout.write(`${test.name}... `);
    const startTime = Date.now();

    try {
      const res = await request(test.url, test.method, test.data);
      const latency = Date.now() - startTime;
      const success = test.validate(res);

      if (success) {
        log('green', `✅ 成功 (${latency}ms)`);
        passed++;
        results.push({ name: test.name, status: 'pass', latency });
      } else {
        log('red', `❌ 失败 (状态码: ${res.status})`);
        failed++;
        results.push({ name: test.name, status: 'fail', error: `HTTP ${res.status}` });
      }

      // 显示部分响应数据
      if (res.data && typeof res.data === 'object') {
        const preview = JSON.stringify(res.data).substring(0, 100);
        log('blue', `   响应: ${preview}...`);
      }
    } catch (error) {
      log('red', `❌ 错误: ${error.message}`);
      failed++;
      results.push({ name: test.name, status: 'error', error: error.message });
    }

    console.log('');
  }

  // 汇总
  log('cyan', '========================================');
  log('cyan', '   测试汇总');
  log('cyan', '========================================');
  log('green', `通过: ${passed}`);
  log('red', `失败: ${failed}`);
  log('yellow', `连通率: ${((passed / tests.length) * 100).toFixed(1)}%`);
  console.log('');

  // 评估
  const connectivity = (passed / tests.length) * 100;
  if (connectivity >= 80) {
    log('green', '✅ 数据连通性良好，可以正常使用');
  } else if (connectivity >= 50) {
    log('yellow', '⚠️ 部分API不可用，功能可能受限');
  } else {
    log('red', '❌ 数据连通性差，请检查后端服务');
  }

  return { passed, failed, results };
}

// 检查后端服务是否启动
async function checkBackendService() {
  log('cyan', '检查后端服务状态...\n');

  try {
    await request('http://localhost:5000/api/health', 'GET');
    log('green', '✅ 后端服务已启动\n');
    return true;
  } catch (error) {
    log('yellow', '⚠️ 后端服务可能未启动，尝试继续测试...\n');
    return false;
  }
}

// 主函数
async function main() {
  console.log('');
  log('cyan', '=== 微博情感分析系统 - 前端数据连通性测试 ===');
  console.log('');

  await checkBackendService();
  await runTests();

  console.log('');
  log('cyan', '测试完成！');
  log('blue', '如需启动后端服务，请运行:');
  log('blue', '  cd backend && python app.py');
  console.log('');
}

main().catch(console.error);
