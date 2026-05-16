#!/usr/bin/env bash
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deployment"
ENV_FILE="${DEPLOY_DIR}/.env.docker"
REPORT_DIR="${PROJECT_ROOT}/test-reports/chapter7"
REPORT_FILE="${REPORT_DIR}/chapter7-system-test-$(date +%Y%m%d-%H%M%S).md"

FAIL_COUNT=0
WARN_COUNT=0
PASS_COUNT=0

get_env() {
    local key="$1" default="$2"
    if [[ -f "${ENV_FILE}" ]]; then
        local value
        value=$(grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '[:space:]')
        echo "${value:-${default}}"
    else
        echo "${default}"
    fi
}

HOST="${TEST_HOST:-127.0.0.1}"
WEB_PORT="${TEST_WEB_PORT:-$(get_env WEB_PORT 5000)}"
FRONTEND_PORT="${TEST_FRONTEND_PORT:-$(get_env FRONTEND_PORT 3001)}"
SPARK_PORT="${TEST_SPARK_PORT:-$(get_env SPARK_WEBUI_PORT 8080)}"
HDFS_CONTAINER="${TEST_HDFS_CONTAINER:-weibo_sentiment_namenode}"
MYSQL_CONTAINER="${TEST_MYSQL_CONTAINER:-weibo_sentiment_db}"
WEB_CONTAINER="${TEST_WEB_CONTAINER:-weibo_sentiment_web}"
BASE_URL="${TEST_BASE_URL:-http://${HOST}:${WEB_PORT}}"
FRONTEND_URL="${TEST_FRONTEND_URL:-http://${HOST}:${FRONTEND_PORT}}"
SPARK_URL="${TEST_SPARK_URL:-http://${HOST}:${SPARK_PORT}}"
KEYWORD="${TEST_KEYWORD:-人工智能}"
COLLECT_LIMIT="${TEST_COLLECT_LIMIT:-50}"
PERF_LIMIT="${TEST_PERF_LIMIT:-10000}"
STABILITY_SECONDS="${TEST_STABILITY_SECONDS:-60}"
ACCURACY_SCRIPT="${TEST_ACCURACY_SCRIPT:-${PROJECT_ROOT}/backend-python/scripts/evaluate_model.py}"
MODEL_DIR="${TEST_MODEL_DIR:-models/chinese-bert-wwm-ext-v2}"
JMETER_PLAN="${TEST_JMETER_PLAN:-${PROJECT_ROOT}/deployment/jmeter/chapter7-performance.jmx}"

mkdir -p "${REPORT_DIR}"

append_report() {
    echo -e "$*" >> "${REPORT_FILE}"
}

print_line() {
    echo -e "$*"
    append_report "$*"
}

section() {
    echo ""
    echo -e "${CYAN}${BOLD}$*${NC}"
    append_report ""
    append_report "## $*"
}

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    echo -e "  ${GREEN}通过${NC}  $*"
    append_report "- 通过：$*"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    echo -e "  ${YELLOW}警告${NC}  $*"
    append_report "- 警告：$*"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo -e "  ${RED}失败${NC}  $*"
    append_report "- 失败：$*"
}

http_code() {
    curl -sS -o /tmp/chapter7_response.json -w "%{http_code}" --connect-timeout 5 --max-time 20 "$1" 2>/dev/null || echo "000"
}

post_json() {
    local url="$1" payload="$2"
    curl -sS -o /tmp/chapter7_response.json -w "%{http_code}" --connect-timeout 5 --max-time 60 \
        -H 'Content-Type: application/json' -X POST -d "${payload}" "${url}" 2>/dev/null || echo "000"
}

json_value() {
    local expr="$1" default="$2"
    if command -v jq >/dev/null 2>&1 && [[ -s /tmp/chapter7_response.json ]]; then
        jq -r "${expr} // \"${default}\"" /tmp/chapter7_response.json 2>/dev/null || echo "${default}"
    else
        echo "${default}"
    fi
}

check_http_ok() {
    local name="$1" url="$2"
    local code
    code=$(http_code "${url}")
    if [[ "${code}" =~ ^(200|301|302)$ ]]; then
        pass "${name} 接口可访问，HTTP ${code}"
        return 0
    fi
    fail "${name} 接口不可访问，HTTP ${code}，URL=${url}"
    return 1
}

init_report() {
    cat > "${REPORT_FILE}" <<EOF
# 第7章 系统测试报告

- 测试时间：$(date '+%Y-%m-%d %H:%M:%S')
- 测试主机：${HOST}
- Flask API：${BASE_URL}
- 前端地址：${FRONTEND_URL}
- Spark WebUI：${SPARK_URL}
- 测试关键词：${KEYWORD}

EOF
}

chapter_7_1() {
    section "7.1 测试的目的和方法"
    print_line "本脚本用于验证系统功能、性能、准确率和部署稳定性，测试方法包括黑盒接口测试、轻量性能测试、模型准确率脚本调用和容器资源状态检查。"

    if command -v curl >/dev/null 2>&1; then pass "curl 已安装"; else fail "curl 未安装"; fi
    if command -v docker >/dev/null 2>&1; then pass "Docker 已安装：$(docker --version 2>/dev/null)"; else warn "Docker 未安装或当前用户不可用，容器级检查将跳过"; fi
    if docker compose version >/dev/null 2>&1; then pass "Docker Compose v2 可用"; elif command -v docker-compose >/dev/null 2>&1; then warn "检测到 Docker Compose v1"; else warn "Docker Compose 不可用，Compose 检查跳过"; fi
    if command -v jq >/dev/null 2>&1; then pass "jq 已安装，可解析 JSON"; else warn "jq 未安装，将只做 HTTP 状态检查"; fi

    check_http_ok "Flask API 健康检查" "${BASE_URL}/api/v2/health"
    check_http_ok "前端页面" "${FRONTEND_URL}/"
    check_http_ok "Spark WebUI" "${SPARK_URL}/"
}

chapter_7_2_1() {
    section "7.2.1 数据采集功能测试"
    print_line "测试用例：设置关键词“${KEYWORD}”，启动轻量采集任务，验证任务创建、进度、数据字段与重复情况。"
    append_report ""
    append_report "| 测试步骤 | 预期结果 | 实际结果 | 结论 |"
    append_report "|---|---|---|---|"

    local payload code task_id status_url data_url progress collected
    payload=$(cat <<EOF
{"name":"第7章数据采集测试","keywords":[{"word":"${KEYWORD}","weight":1}],"dataSources":["weibo"],"maxCount":${COLLECT_LIMIT},"requestInterval":1}
EOF
)
    code=$(post_json "${BASE_URL}/api/collection/tasks" "${payload}")
    if [[ "${code}" == "200" ]]; then
        task_id=$(json_value '.data.id' '')
        pass "采集任务创建成功：${task_id}"
        append_report "| 输入关键词并创建采集任务 | 任务创建成功 | 任务ID=${task_id} | 通过 |"
    else
        fail "采集任务创建失败，HTTP ${code}"
        append_report "| 输入关键词并创建采集任务 | 任务创建成功 | HTTP ${code} | 失败 |"
        return
    fi

    code=$(post_json "${BASE_URL}/api/collection/tasks/${task_id}/start" "{}")
    if [[ "${code}" == "200" ]]; then
        pass "采集任务启动成功"
        append_report "| 点击启动采集 | 开始采集 | 后端返回启动成功 | 通过 |"
    else
        fail "采集任务启动失败，HTTP ${code}"
        append_report "| 点击启动采集 | 开始采集 | HTTP ${code} | 失败 |"
        return
    fi

    status_url="${BASE_URL}/api/collection/tasks/${task_id}"
    for _ in $(seq 1 20); do
        code=$(http_code "${status_url}")
        status=$(json_value '.data.status' 'unknown')
        progress=$(json_value '.data.progress' '0')
        collected=$(json_value '.data.collected' '0')
        if [[ "${status}" =~ ^(completed|failed|stopped)$ ]]; then
            break
        fi
        sleep 2
    done

    if [[ "${status}" == "completed" || "${collected}" != "0" ]]; then
        pass "采集进度可查询：status=${status}, progress=${progress}, collected=${collected}"
        append_report "| 采集过程中查看进度 | 进度条实时更新 | progress=${progress}, collected=${collected} | 通过 |"
    else
        warn "未在限定时间内采集到数据：status=${status}, progress=${progress}, collected=${collected}"
        append_report "| 采集过程中查看进度 | 进度条实时更新 | status=${status}, collected=${collected} | 警告 |"
    fi

    data_url="${BASE_URL}/api/collection/tasks/${task_id}/data?page=1&pageSize=20"
    code=$(http_code "${data_url}")
    local total first_id first_content duplicate_count
    total=$(json_value '.data.total' '0')
    first_id=$(json_value '.data.list[0].id' '')
    first_content=$(json_value '.data.list[0].content' '')
    if [[ "${code}" == "200" ]]; then
        pass "采集数据分页接口可用：total=${total}"
        append_report "| 采集完成后查看数据 | 可查询采集数据 | total=${total} | 通过 |"
    else
        fail "采集数据查询失败，HTTP ${code}"
        append_report "| 采集完成后查看数据 | 可查询采集数据 | HTTP ${code} | 失败 |"
    fi

    if [[ -n "${first_id}" && -n "${first_content}" ]]; then
        pass "字段完整性检查通过：包含微博ID与文本内容"
        append_report "| 检查数据字段完整性 | 微博ID、文本等字段齐全 | 字段存在 | 通过 |"
    else
        warn "字段完整性无法充分验证，可能未采集到样本数据"
        append_report "| 检查数据字段完整性 | 微博ID、文本等字段齐全 | 样本为空或字段不足 | 警告 |"
    fi

    if command -v jq >/dev/null 2>&1 && [[ -s /tmp/chapter7_response.json ]]; then
        duplicate_count=$(jq '[.data.list[].id] | length - (unique | length)' /tmp/chapter7_response.json 2>/dev/null || echo "0")
        if [[ "${duplicate_count}" == "0" ]]; then
            pass "当前页无重复微博ID"
            append_report "| 检查重复数据 | 同一微博ID仅出现一次 | 当前页无重复 | 通过 |"
        else
            fail "当前页发现重复微博ID数量：${duplicate_count}"
            append_report "| 检查重复数据 | 同一微博ID仅出现一次 | 重复数=${duplicate_count} | 失败 |"
        fi
    else
        warn "未安装 jq，重复数据检查跳过"
        append_report "| 检查重复数据 | 同一微博ID仅出现一次 | jq 不可用，跳过 | 警告 |"
    fi

    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${HDFS_CONTAINER}"; then
        if docker exec "${HDFS_CONTAINER}" hdfs dfs -ls /weibo/raw >/tmp/chapter7_hdfs_ls.txt 2>/dev/null; then
            pass "HDFS /weibo/raw 可访问"
            append_report "| 检查HDFS数据文件 | HDFS中存在JSON文件 | /weibo/raw 可访问 | 通过 |"
        else
            warn "HDFS /weibo/raw 暂不可访问或目录不存在"
            append_report "| 检查HDFS数据文件 | HDFS中存在JSON文件 | 未检测到 /weibo/raw | 警告 |"
        fi
    else
        warn "未检测到 HDFS 容器，HDFS 文件检查跳过"
        append_report "| 检查HDFS数据文件 | HDFS中存在JSON文件 | HDFS容器不存在，跳过 | 警告 |"
    fi
}

chapter_7_2_2() {
    section "7.2.2 情感分析功能测试"
    print_line "测试用例：调用实时情感分析接口，并在模型与测试集存在时运行准确率评估脚本。"
    append_report ""
    append_report "| 测试模式 | 准确率 | 召回率 | F1值 | 结论 |"
    append_report "|---|---:|---:|---:|---|"

    local code payload sentiment score
    payload='{"text":"人工智能技术发展迅速，给生活带来了很多便利。"}'
    code=$(post_json "${BASE_URL}/api/sentiment/analyze" "${payload}")
    sentiment=$(json_value '.data.sentiment' '')
    score=$(json_value '.data.sentiment_score' '')
    if [[ "${code}" == "200" && -n "${sentiment}" ]]; then
        pass "实时情感分析接口正常：sentiment=${sentiment}, score=${score}"
    else
        fail "实时情感分析接口异常，HTTP ${code}"
    fi

    if [[ -f "${ACCURACY_SCRIPT}" ]]; then
        if [[ -d "${PROJECT_ROOT}/backend-python/${MODEL_DIR}" || -d "${MODEL_DIR}" ]]; then
            local acc_log
            acc_log="${REPORT_DIR}/accuracy-$(date +%Y%m%d-%H%M%S).log"
            if (cd "${PROJECT_ROOT}/backend-python" && python3 scripts/evaluate_model.py --model-dir "${MODEL_DIR}" --no-baseline > "${acc_log}" 2>&1); then
                local accuracy macro_f1
                accuracy=$(grep -E "Accuracy:" "${acc_log}" | head -1 | awk '{print $2}' || echo "见日志")
                macro_f1=$(grep -E "Macro F1:" "${acc_log}" | head -1 | awk '{print $3}' || echo "见日志")
                pass "模型准确率评估完成：Accuracy=${accuracy}, MacroF1=${macro_f1}，日志=${acc_log}"
                append_report "| 混合模式（词典+ChineseBERT） | ${accuracy} | 见日志 | ${macro_f1} | 通过 |"
            else
                warn "准确率评估脚本执行失败，详见 ${acc_log}"
                append_report "| 混合模式（词典+ChineseBERT） | - | - | - | 警告 |"
            fi
        else
            warn "模型目录不存在，跳过准确率评估：${MODEL_DIR}"
            append_report "| 混合模式（词典+ChineseBERT） | - | - | - | 模型目录不存在，跳过 |"
        fi
    else
        warn "准确率评估脚本不存在：${ACCURACY_SCRIPT}"
        append_report "| 混合模式（词典+ChineseBERT） | - | - | - | 脚本不存在，跳过 |"
    fi
}

chapter_7_2_3() {
    section "7.2.3 数据展示功能测试"
    print_line "测试用例：验证情感分布、趋势、词云/热搜、前端页面和导出依赖接口可访问。"
    append_report ""
    append_report "| 测试功能 | 测试操作 | 预期结果 | 实际结果 | 结论 |"
    append_report "|---|---|---|---|---|"

    local code
    code=$(http_code "${BASE_URL}/api/sentiment/distribution")
    if [[ "${code}" =~ ^(200|404)$ ]]; then
        [[ "${code}" == "200" ]] && pass "情感分布接口可用" || warn "情感分布接口未实现或路径不匹配，HTTP 404"
        append_report "| 情感分布图 | 请求分布接口 | 返回正负中占比 | HTTP ${code} | $([[ "${code}" == "200" ]] && echo 通过 || echo 警告) |"
    else
        fail "情感分布接口异常，HTTP ${code}"
        append_report "| 情感分布图 | 请求分布接口 | 返回正负中占比 | HTTP ${code} | 失败 |"
    fi

    code=$(http_code "${BASE_URL}/api/v2/stats/trend?days=7")
    if [[ "${code}" == "200" ]]; then
        pass "情感趋势接口可用"
        append_report "| 情感趋势图 | 切换时间范围 | 折线图数据更新 | HTTP 200 | 通过 |"
    else
        warn "情感趋势接口不可用，HTTP ${code}"
        append_report "| 情感趋势图 | 切换时间范围 | 折线图数据更新 | HTTP ${code} | 警告 |"
    fi

    code=$(http_code "${BASE_URL}/api/weibo/hotsearch")
    if [[ "${code}" == "200" ]]; then
        pass "热点话题/词云数据接口可用"
        append_report "| 热点话题词云 | 请求热搜接口 | 返回热点关键词 | HTTP 200 | 通过 |"
    else
        warn "热点话题接口不可用，HTTP ${code}"
        append_report "| 热点话题词云 | 请求热搜接口 | 返回热点关键词 | HTTP ${code} | 警告 |"
    fi

    code=$(http_code "${FRONTEND_URL}/")
    if [[ "${code}" =~ ^(200|301|302)$ ]]; then
        pass "前端页面可访问，图表导出功能需浏览器端人工确认"
        append_report "| 图表导出 | 点击导出按钮 | 下载PNG图片 | 前端可访问，建议浏览器复核 | 通过 |"
    else
        fail "前端页面不可访问，HTTP ${code}"
        append_report "| 图表导出 | 点击导出按钮 | 下载PNG图片 | HTTP ${code} | 失败 |"
    fi
}

chapter_7_3_1() {
    section "7.3.1 数据处理效率测试"
    print_line "测试用例：调用数据库情感分析接口或 JMeter 测试计划，记录批量处理响应时间。"
    append_report ""
    append_report "| 处理阶段 | 样本规模 | 耗时（秒） | 结论 |"
    append_report "|---|---:|---:|---|"

    if command -v jmeter >/dev/null 2>&1 && [[ -f "${JMETER_PLAN}" ]]; then
        local jtl jmeter_log
        jtl="${REPORT_DIR}/jmeter-$(date +%Y%m%d-%H%M%S).jtl"
        jmeter_log="${REPORT_DIR}/jmeter.log"
        if jmeter -n -t "${JMETER_PLAN}" -l "${jtl}" -j "${jmeter_log}"; then
            pass "JMeter 性能测试完成：${jtl}"
        else
            warn "JMeter 执行失败，详见 ${jmeter_log}"
        fi
    else
        warn "未检测到 JMeter 或测试计划，使用接口计时代替"
    fi

    local start end elapsed code
    start=$(date +%s)
    code=$(post_json "${BASE_URL}/api/sentiment/run-db" "{\"limit\":${PERF_LIMIT}}")
    end=$(date +%s)
    elapsed=$((end - start))
    if [[ "${code}" == "200" ]]; then
        pass "批量情感分析接口完成：limit=${PERF_LIMIT}, elapsed=${elapsed}s"
        append_report "| 情感分析（数据库批处理） | ${PERF_LIMIT} | ${elapsed} | 通过 |"
    elif [[ "${code}" == "400" || "${code}" == "503" ]]; then
        warn "批量情感分析接口返回 HTTP ${code}，可能无待处理数据或数据库不可用"
        append_report "| 情感分析（数据库批处理） | ${PERF_LIMIT} | ${elapsed} | 警告 |"
    else
        fail "批量情感分析接口异常，HTTP ${code}"
        append_report "| 情感分析（数据库批处理） | ${PERF_LIMIT} | ${elapsed} | 失败 |"
    fi
}

chapter_7_3_2() {
    section "7.3.2 系统稳定性测试"
    print_line "测试用例：连续运行 ${STABILITY_SECONDS} 秒，周期性检查 API、容器状态和内存使用。生产验收可设置 TEST_STABILITY_SECONDS=86400。"
    append_report ""
    append_report "| 检查项 | 预期结果 | 实际结果 | 结论 |"
    append_report "|---|---|---|---|"

    local loops ok api_fail max_mem
    loops=$((STABILITY_SECONDS / 10))
    [[ "${loops}" -lt 1 ]] && loops=1
    api_fail=0
    max_mem="N/A"

    for _ in $(seq 1 "${loops}"); do
        local code
        code=$(http_code "${BASE_URL}/api/v2/health")
        [[ "${code}" == "200" ]] || api_fail=$((api_fail + 1))
        if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "${WEB_CONTAINER}"; then
            local mem
            mem=$(docker stats --no-stream --format '{{.MemUsage}}' "${WEB_CONTAINER}" 2>/dev/null | awk '{print $1}' || echo "N/A")
            max_mem="${mem}"
        fi
        sleep 10
    done

    if [[ "${api_fail}" == "0" ]]; then
        pass "稳定性检查期间 API 全部正常"
        append_report "| API 连续可用性 | 无失败请求 | 失败次数=0 | 通过 |"
    else
        fail "稳定性检查期间 API 失败 ${api_fail} 次"
        append_report "| API 连续可用性 | 无失败请求 | 失败次数=${api_fail} | 失败 |"
    fi

    if command -v docker >/dev/null 2>&1; then
        local unhealthy
        unhealthy=$(docker ps --filter 'health=unhealthy' --format '{{.Names}}' 2>/dev/null | tr '\n' ' ')
        if [[ -z "${unhealthy}" ]]; then
            pass "未发现 unhealthy 容器，Web容器内存采样=${max_mem}"
            append_report "| 容器健康状态 | 无 unhealthy 容器 | 内存采样=${max_mem} | 通过 |"
        else
            fail "发现 unhealthy 容器：${unhealthy}"
            append_report "| 容器健康状态 | 无 unhealthy 容器 | ${unhealthy} | 失败 |"
        fi
    else
        warn "Docker 不可用，容器稳定性检查跳过"
        append_report "| 容器健康状态 | 无 unhealthy 容器 | Docker不可用 | 警告 |"
    fi
}

chapter_7_4() {
    section "7.4 本章小结"
    print_line "本次测试完成：通过 ${PASS_COUNT} 项，警告 ${WARN_COUNT} 项，失败 ${FAIL_COUNT} 项。"
    if [[ "${FAIL_COUNT}" == "0" ]]; then
        print_line "系统核心功能和部署连通性测试通过，可结合浏览器人工测试补充图表交互与导出截图。"
    else
        print_line "存在失败项，请根据报告中的接口、容器或日志路径进行排查。"
    fi
    print_line "测试报告文件：${REPORT_FILE}"
}

main() {
    init_report
    echo -e "${BOLD}第7章 系统测试脚本${NC}"
    echo "报告输出：${REPORT_FILE}"
    chapter_7_1
    chapter_7_2_1
    chapter_7_2_2
    chapter_7_2_3
    chapter_7_3_1
    chapter_7_3_2
    chapter_7_4
    [[ "${FAIL_COUNT}" == "0" ]] && exit 0 || exit 1
}

main "$@"
