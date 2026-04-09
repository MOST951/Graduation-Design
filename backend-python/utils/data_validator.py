"""
数据验证器模块
==============

确保采集数据的完整性和准确性

功能：
1. 数据完整性检查：必填字段、字段类型、数据范围
2. 数据质量指标：采集成功率、重复率、字段完整率
3. 异常数据处理：错误记录、自动修复、质量报告
4. 与前端集成：API端点、可视化仪表板、实时报警
"""

import os
import re
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DataValidator')


class ValidationLevel(Enum):
    """验证级别"""
    ERROR = 'error'      # 严重错误，数据无效
    WARNING = 'warning'  # 警告，数据可用但有问题
    INFO = 'info'        # 信息，轻微问题


class FieldType(Enum):
    """字段类型"""
    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    BOOLEAN = 'boolean'
    TIMESTAMP = 'timestamp'
    LIST = 'list'
    DICT = 'dict'


@dataclass
class ValidationRule:
    """验证规则"""
    field_name: str
    required: bool = False
    field_type: FieldType = FieldType.STRING
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    custom_validator: Optional[callable] = None
    auto_fix: bool = False
    fix_function: Optional[callable] = None


@dataclass
class ValidationError:
    """验证错误"""
    field_name: str
    error_type: str
    message: str
    level: ValidationLevel = ValidationLevel.ERROR
    original_value: Any = None
    fixed_value: Any = None
    fixed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'field_name': self.field_name,
            'error_type': self.error_type,
            'message': self.message,
            'level': self.level.value,
            'original_value': str(self.original_value)[:100] if self.original_value else None,
            'fixed_value': str(self.fixed_value)[:100] if self.fixed_value else None,
            'fixed': self.fixed
        }


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    data: Dict = field(default_factory=dict)
    fixed_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    fixed_records: int = 0
    
    # 字段完整率
    field_completeness: Dict[str, float] = field(default_factory=dict)
    
    # 错误统计
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    # 时间统计
    start_time: str = ''
    end_time: str = ''
    duration_seconds: float = 0
    
    @property
    def success_rate(self) -> float:
        """采集成功率"""
        if self.total_records == 0:
            return 0.0
        return self.valid_records / self.total_records
    
    @property
    def duplicate_rate(self) -> float:
        """数据重复率"""
        if self.total_records == 0:
            return 0.0
        return self.duplicate_records / self.total_records
    
    @property
    def fix_rate(self) -> float:
        """修复率"""
        if self.invalid_records == 0:
            return 0.0
        return self.fixed_records / (self.invalid_records + self.fixed_records)
    
    def to_dict(self) -> Dict:
        return {
            'total_records': self.total_records,
            'valid_records': self.valid_records,
            'invalid_records': self.invalid_records,
            'duplicate_records': self.duplicate_records,
            'fixed_records': self.fixed_records,
            'success_rate': round(self.success_rate * 100, 2),
            'duplicate_rate': round(self.duplicate_rate * 100, 2),
            'fix_rate': round(self.fix_rate * 100, 2),
            'field_completeness': {k: round(v * 100, 2) for k, v in self.field_completeness.items()},
            'error_counts': self.error_counts,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': round(self.duration_seconds, 2)
        }


@dataclass
class QualityAlert:
    """质量报警"""
    alert_type: str
    message: str
    severity: str  # low, medium, high, critical
    metric_name: str
    current_value: float
    threshold: float
    timestamp: str = ''
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


class WeiboDataValidator:
    """
    微博数据验证器
    
    负责验证采集的微博数据的完整性和准确性
    """
    
    # 微博数据验证规则
    WEIBO_RULES = [
        ValidationRule(
            field_name='text',
            required=True,
            field_type=FieldType.STRING,
            min_length=1,
            max_length=10000
        ),
        ValidationRule(
            field_name='id',
            required=True,
            field_type=FieldType.STRING,
            min_length=1
        ),
        ValidationRule(
            field_name='mid',
            required=False,
            field_type=FieldType.STRING
        ),
        ValidationRule(
            field_name='created_at',
            required=True,
            field_type=FieldType.TIMESTAMP,
            auto_fix=True
        ),
        ValidationRule(
            field_name='user',
            required=False,
            field_type=FieldType.DICT
        ),
        ValidationRule(
            field_name='reposts_count',
            required=False,
            field_type=FieldType.INTEGER,
            min_value=0,
            auto_fix=True
        ),
        ValidationRule(
            field_name='comments_count',
            required=False,
            field_type=FieldType.INTEGER,
            min_value=0,
            auto_fix=True
        ),
        ValidationRule(
            field_name='attitudes_count',
            required=False,
            field_type=FieldType.INTEGER,
            min_value=0,
            auto_fix=True
        ),
    ]
    
    # 质量阈值配置
    QUALITY_THRESHOLDS = {
        'success_rate': 0.8,       # 成功率阈值 80%
        'duplicate_rate': 0.3,     # 重复率阈值 30%
        'field_completeness': 0.7, # 字段完整率阈值 70%
    }
    
    def __init__(self, rules: List[ValidationRule] = None):
        self.rules = rules or self.WEIBO_RULES
        self._rules_dict = {rule.field_name: rule for rule in self.rules}
        self._seen_ids: Set[str] = set()
        self._lock = threading.Lock()
        
        # 错误日志存储
        self._error_log: List[Dict] = []
        self._error_log_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data', 'error_log.json'
        )
        
        # 质量报告存储
        self._quality_reports: List[Dict] = []
        self._quality_report_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data', 'quality_reports.json'
        )
        
        # 加载历史数据
        self._load_error_log()
        self._load_quality_reports()
    
    def _load_error_log(self):
        """加载错误日志"""
        try:
            if os.path.exists(self._error_log_file):
                with open(self._error_log_file, 'r', encoding='utf-8') as f:
                    self._error_log = json.load(f)
                logger.info(f"已加载 {len(self._error_log)} 条错误日志")
        except Exception as e:
            logger.error(f"加载错误日志失败: {e}")
    
    def _save_error_log(self):
        """保存错误日志"""
        try:
            os.makedirs(os.path.dirname(self._error_log_file), exist_ok=True)
            with open(self._error_log_file, 'w', encoding='utf-8') as f:
                # 只保留最近1000条
                json.dump(self._error_log[-1000:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存错误日志失败: {e}")
    
    def _load_quality_reports(self):
        """加载质量报告"""
        try:
            if os.path.exists(self._quality_report_file):
                with open(self._quality_report_file, 'r', encoding='utf-8') as f:
                    self._quality_reports = json.load(f)
                logger.info(f"已加载 {len(self._quality_reports)} 份质量报告")
        except Exception as e:
            logger.error(f"加载质量报告失败: {e}")
    
    def _save_quality_reports(self):
        """保存质量报告"""
        try:
            os.makedirs(os.path.dirname(self._quality_report_file), exist_ok=True)
            with open(self._quality_report_file, 'w', encoding='utf-8') as f:
                # 只保留最近100份
                json.dump(self._quality_reports[-100:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存质量报告失败: {e}")
    
    def validate_field(self, field_name: str, value: Any, rule: ValidationRule) -> List[ValidationError]:
        """验证单个字段"""
        errors = []
        
        # 检查必填
        if rule.required and (value is None or value == ''):
            errors.append(ValidationError(
                field_name=field_name,
                error_type='required',
                message=f'字段 {field_name} 是必填项',
                level=ValidationLevel.ERROR,
                original_value=value
            ))
            return errors
        
        # 如果值为空且非必填，跳过后续检查
        if value is None or value == '':
            return errors
        
        # 检查类型
        type_error = self._check_type(field_name, value, rule.field_type)
        if type_error:
            # 尝试自动修复
            if rule.auto_fix:
                fixed_value, fixed = self._auto_fix_type(value, rule.field_type)
                if fixed:
                    type_error.fixed = True
                    type_error.fixed_value = fixed_value
                    type_error.level = ValidationLevel.WARNING
            errors.append(type_error)
            if not type_error.fixed:
                return errors
            value = type_error.fixed_value
        
        # 检查范围
        if rule.min_value is not None and value < rule.min_value:
            error = ValidationError(
                field_name=field_name,
                error_type='min_value',
                message=f'字段 {field_name} 值 {value} 小于最小值 {rule.min_value}',
                level=ValidationLevel.WARNING if rule.auto_fix else ValidationLevel.ERROR,
                original_value=value
            )
            if rule.auto_fix:
                error.fixed = True
                error.fixed_value = rule.min_value
            errors.append(error)
        
        if rule.max_value is not None and value > rule.max_value:
            error = ValidationError(
                field_name=field_name,
                error_type='max_value',
                message=f'字段 {field_name} 值 {value} 大于最大值 {rule.max_value}',
                level=ValidationLevel.WARNING if rule.auto_fix else ValidationLevel.ERROR,
                original_value=value
            )
            if rule.auto_fix:
                error.fixed = True
                error.fixed_value = rule.max_value
            errors.append(error)
        
        # 检查长度（字符串）
        if isinstance(value, str):
            if rule.min_length is not None and len(value) < rule.min_length:
                errors.append(ValidationError(
                    field_name=field_name,
                    error_type='min_length',
                    message=f'字段 {field_name} 长度 {len(value)} 小于最小长度 {rule.min_length}',
                    level=ValidationLevel.ERROR,
                    original_value=value
                ))
            
            if rule.max_length is not None and len(value) > rule.max_length:
                error = ValidationError(
                    field_name=field_name,
                    error_type='max_length',
                    message=f'字段 {field_name} 长度 {len(value)} 大于最大长度 {rule.max_length}',
                    level=ValidationLevel.WARNING,
                    original_value=value
                )
                if rule.auto_fix:
                    error.fixed = True
                    error.fixed_value = value[:rule.max_length]
                errors.append(error)
        
        # 检查正则模式
        if rule.pattern and isinstance(value, str):
            if not re.match(rule.pattern, value):
                errors.append(ValidationError(
                    field_name=field_name,
                    error_type='pattern',
                    message=f'字段 {field_name} 不匹配模式 {rule.pattern}',
                    level=ValidationLevel.ERROR,
                    original_value=value
                ))
        
        # 自定义验证
        if rule.custom_validator:
            try:
                is_valid, message = rule.custom_validator(value)
                if not is_valid:
                    errors.append(ValidationError(
                        field_name=field_name,
                        error_type='custom',
                        message=message,
                        level=ValidationLevel.ERROR,
                        original_value=value
                    ))
            except Exception as e:
                logger.error(f"自定义验证器执行失败: {e}")
        
        return errors
    
    def _check_type(self, field_name: str, value: Any, expected_type: FieldType) -> Optional[ValidationError]:
        """检查字段类型"""
        type_checks = {
            FieldType.STRING: lambda v: isinstance(v, str),
            FieldType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            FieldType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            FieldType.BOOLEAN: lambda v: isinstance(v, bool),
            FieldType.LIST: lambda v: isinstance(v, list),
            FieldType.DICT: lambda v: isinstance(v, dict),
            FieldType.TIMESTAMP: lambda v: self._is_valid_timestamp(v),
        }
        
        check_func = type_checks.get(expected_type)
        if check_func and not check_func(value):
            return ValidationError(
                field_name=field_name,
                error_type='type',
                message=f'字段 {field_name} 类型错误，期望 {expected_type.value}，实际 {type(value).__name__}',
                level=ValidationLevel.ERROR,
                original_value=value
            )
        
        # 特殊检查：timestamp不能是未来时间
        if expected_type == FieldType.TIMESTAMP:
            ts = self._parse_timestamp(value)
            if ts and ts > datetime.now() + timedelta(hours=1):  # 允许1小时误差
                return ValidationError(
                    field_name=field_name,
                    error_type='future_timestamp',
                    message=f'字段 {field_name} 时间戳不能是未来时间',
                    level=ValidationLevel.WARNING,
                    original_value=value
                )
        
        return None
    
    def _is_valid_timestamp(self, value: Any) -> bool:
        """检查是否是有效的时间戳"""
        if isinstance(value, (int, float)):
            # Unix时间戳
            try:
                if value > 1e12:  # 毫秒时间戳
                    value = value / 1000
                datetime.fromtimestamp(value)
                return True
            except:
                return False
        elif isinstance(value, str):
            return self._parse_timestamp(value) is not None
        elif isinstance(value, datetime):
            return True
        return False
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """解析时间戳"""
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, (int, float)):
            try:
                if value > 1e12:
                    value = value / 1000
                return datetime.fromtimestamp(value)
            except:
                return None
        
        if isinstance(value, str):
            # 尝试多种格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y/%m/%d %H:%M:%S',
                '%a %b %d %H:%M:%S %z %Y',  # 微博格式
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except:
                    continue
            
            # 尝试解析微博的中文格式
            try:
                # "刚刚", "X分钟前", "X小时前", "昨天", "今天"
                if '刚刚' in value:
                    return datetime.now()
                elif '分钟前' in value:
                    minutes = int(re.search(r'(\d+)', value).group(1))
                    return datetime.now() - timedelta(minutes=minutes)
                elif '小时前' in value:
                    hours = int(re.search(r'(\d+)', value).group(1))
                    return datetime.now() - timedelta(hours=hours)
                elif '昨天' in value:
                    return datetime.now() - timedelta(days=1)
            except:
                pass
        
        return None
    
    def _auto_fix_type(self, value: Any, expected_type: FieldType) -> Tuple[Any, bool]:
        """自动修复类型"""
        try:
            if expected_type == FieldType.INTEGER:
                if isinstance(value, str):
                    # 移除逗号等分隔符
                    clean_value = re.sub(r'[,\s]', '', value)
                    return int(float(clean_value)), True
                elif isinstance(value, float):
                    return int(value), True
            
            elif expected_type == FieldType.FLOAT:
                if isinstance(value, str):
                    clean_value = re.sub(r'[,\s]', '', value)
                    return float(clean_value), True
                elif isinstance(value, int):
                    return float(value), True
            
            elif expected_type == FieldType.STRING:
                return str(value), True
            
            elif expected_type == FieldType.TIMESTAMP:
                ts = self._parse_timestamp(value)
                if ts:
                    return ts.isoformat(), True
        except:
            pass
        
        return value, False
    
    def validate(self, data: Dict) -> ValidationResult:
        """验证单条数据"""
        errors = []
        warnings = []
        fixed_data = data.copy()
        
        for rule in self.rules:
            field_name = rule.field_name
            value = data.get(field_name)
            
            field_errors = self.validate_field(field_name, value, rule)
            
            for error in field_errors:
                if error.level == ValidationLevel.ERROR and not error.fixed:
                    errors.append(error)
                else:
                    warnings.append(error)
                
                # 应用修复
                if error.fixed and error.fixed_value is not None:
                    fixed_data[field_name] = error.fixed_value
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            data=data,
            fixed_data=fixed_data
        )
    
    def validate_batch(self, data_list: List[Dict], 
                      check_duplicates: bool = True,
                      auto_fix: bool = True) -> Tuple[List[Dict], DataQualityMetrics]:
        """
        批量验证数据
        
        Args:
            data_list: 数据列表
            check_duplicates: 是否检查重复
            auto_fix: 是否自动修复
        
        Returns:
            (有效数据列表, 质量指标)
        """
        start_time = datetime.now()
        
        metrics = DataQualityMetrics(
            total_records=len(data_list),
            start_time=start_time.isoformat()
        )
        
        valid_data = []
        field_counts = defaultdict(int)
        error_counts = defaultdict(int)
        
        with self._lock:
            for data in data_list:
                # 检查重复
                data_id = data.get('id') or data.get('mid') or self._generate_hash(data)
                
                if check_duplicates and data_id in self._seen_ids:
                    metrics.duplicate_records += 1
                    continue
                
                self._seen_ids.add(data_id)
                
                # 验证数据
                result = self.validate(data)
                
                # 统计字段完整率
                for rule in self.rules:
                    if data.get(rule.field_name) is not None and data.get(rule.field_name) != '':
                        field_counts[rule.field_name] += 1
                
                # 统计错误
                for error in result.errors + result.warnings:
                    error_counts[error.error_type] += 1
                
                if result.is_valid:
                    metrics.valid_records += 1
                    valid_data.append(result.fixed_data if auto_fix else data)
                elif auto_fix and len(result.errors) == 0:
                    # 所有错误都已修复
                    metrics.fixed_records += 1
                    metrics.valid_records += 1
                    valid_data.append(result.fixed_data)
                else:
                    metrics.invalid_records += 1
                    # 记录错误日志
                    self._log_error(data, result)
        
        # 计算字段完整率
        total_non_duplicate = metrics.total_records - metrics.duplicate_records
        if total_non_duplicate > 0:
            for rule in self.rules:
                metrics.field_completeness[rule.field_name] = field_counts[rule.field_name] / total_non_duplicate
        
        metrics.error_counts = dict(error_counts)
        
        end_time = datetime.now()
        metrics.end_time = end_time.isoformat()
        metrics.duration_seconds = (end_time - start_time).total_seconds()
        
        # 保存错误日志
        self._save_error_log()
        
        return valid_data, metrics
    
    def _generate_hash(self, data: Dict) -> str:
        """生成数据哈希"""
        text = data.get('text', '')
        user_id = data.get('user', {}).get('id', '') if isinstance(data.get('user'), dict) else ''
        content = f"{text}_{user_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _log_error(self, data: Dict, result: ValidationResult):
        """记录错误日志"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'data_id': data.get('id') or data.get('mid'),
            'data_preview': str(data.get('text', ''))[:100],
            'errors': [e.to_dict() for e in result.errors],
            'warnings': [w.to_dict() for w in result.warnings]
        }
        self._error_log.append(error_entry)
    
    def generate_quality_report(self, metrics: DataQualityMetrics, 
                               task_id: str = None) -> Dict:
        """
        生成数据质量报告
        
        Args:
            metrics: 质量指标
            task_id: 任务ID
        
        Returns:
            质量报告
        """
        alerts = self.check_quality_alerts(metrics)
        
        report = {
            'report_id': f"quality_{int(datetime.now().timestamp() * 1000)}",
            'task_id': task_id,
            'generated_at': datetime.now().isoformat(),
            'metrics': metrics.to_dict(),
            'alerts': [a.to_dict() for a in alerts],
            'summary': {
                'status': 'healthy' if len(alerts) == 0 else 'warning' if all(a.severity in ['low', 'medium'] for a in alerts) else 'critical',
                'total_alerts': len(alerts),
                'critical_alerts': sum(1 for a in alerts if a.severity == 'critical'),
                'high_alerts': sum(1 for a in alerts if a.severity == 'high'),
            },
            'recommendations': self._generate_recommendations(metrics, alerts)
        }
        
        # 保存报告
        self._quality_reports.append(report)
        self._save_quality_reports()
        
        return report
    
    def check_quality_alerts(self, metrics: DataQualityMetrics) -> List[QualityAlert]:
        """检查质量报警"""
        alerts = []
        
        # 检查成功率
        if metrics.success_rate < self.QUALITY_THRESHOLDS['success_rate']:
            severity = 'critical' if metrics.success_rate < 0.5 else 'high' if metrics.success_rate < 0.7 else 'medium'
            alerts.append(QualityAlert(
                alert_type='low_success_rate',
                message=f'数据采集成功率过低: {metrics.success_rate*100:.1f}%',
                severity=severity,
                metric_name='success_rate',
                current_value=metrics.success_rate,
                threshold=self.QUALITY_THRESHOLDS['success_rate']
            ))
        
        # 检查重复率
        if metrics.duplicate_rate > self.QUALITY_THRESHOLDS['duplicate_rate']:
            severity = 'high' if metrics.duplicate_rate > 0.5 else 'medium'
            alerts.append(QualityAlert(
                alert_type='high_duplicate_rate',
                message=f'数据重复率过高: {metrics.duplicate_rate*100:.1f}%',
                severity=severity,
                metric_name='duplicate_rate',
                current_value=metrics.duplicate_rate,
                threshold=self.QUALITY_THRESHOLDS['duplicate_rate']
            ))
        
        # 检查字段完整率
        for field_name, completeness in metrics.field_completeness.items():
            if completeness < self.QUALITY_THRESHOLDS['field_completeness']:
                # 必填字段完整率低是严重问题
                rule = self._rules_dict.get(field_name)
                is_required = rule.required if rule else False
                severity = 'high' if is_required else 'low'
                
                alerts.append(QualityAlert(
                    alert_type='low_field_completeness',
                    message=f'字段 {field_name} 完整率过低: {completeness*100:.1f}%',
                    severity=severity,
                    metric_name=f'field_completeness.{field_name}',
                    current_value=completeness,
                    threshold=self.QUALITY_THRESHOLDS['field_completeness']
                ))
        
        return alerts
    
    def _generate_recommendations(self, metrics: DataQualityMetrics, 
                                  alerts: List[QualityAlert]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if metrics.success_rate < 0.8:
            recommendations.append('建议检查爬虫配置和网络连接，提高数据采集成功率')
        
        if metrics.duplicate_rate > 0.2:
            recommendations.append('建议优化去重策略，减少重复数据采集')
        
        # 根据错误类型给出建议
        if metrics.error_counts.get('required', 0) > 0:
            recommendations.append('存在必填字段缺失，建议检查数据源完整性')
        
        if metrics.error_counts.get('type', 0) > 0:
            recommendations.append('存在字段类型错误，建议检查数据解析逻辑')
        
        if metrics.error_counts.get('future_timestamp', 0) > 0:
            recommendations.append('存在未来时间戳，建议检查时间解析和时区设置')
        
        if not recommendations:
            recommendations.append('数据质量良好，继续保持')
        
        return recommendations
    
    def get_error_log(self, limit: int = 100, 
                     error_type: str = None) -> List[Dict]:
        """获取错误日志"""
        logs = self._error_log
        
        if error_type:
            logs = [
                log for log in logs 
                if any(e['error_type'] == error_type for e in log.get('errors', []))
            ]
        
        return logs[-limit:]
    
    def get_quality_reports(self, limit: int = 10) -> List[Dict]:
        """获取质量报告"""
        return self._quality_reports[-limit:]
    
    def get_latest_quality_summary(self) -> Dict:
        """获取最新质量摘要"""
        if not self._quality_reports:
            return {
                'status': 'no_data',
                'message': '暂无质量报告数据'
            }
        
        latest = self._quality_reports[-1]
        return {
            'status': latest['summary']['status'],
            'success_rate': latest['metrics']['success_rate'],
            'duplicate_rate': latest['metrics']['duplicate_rate'],
            'total_records': latest['metrics']['total_records'],
            'alerts_count': latest['summary']['total_alerts'],
            'generated_at': latest['generated_at']
        }
    
    def clear_seen_ids(self):
        """清除已见ID缓存（用于新任务）"""
        with self._lock:
            self._seen_ids.clear()


# 全局单例
_validator: Optional[WeiboDataValidator] = None


def get_validator() -> WeiboDataValidator:
    """获取验证器单例"""
    global _validator
    if _validator is None:
        _validator = WeiboDataValidator()
    return _validator


# ==================== 便捷函数 ====================

def validate_weibo_data(data: Dict) -> ValidationResult:
    """验证单条微博数据"""
    return get_validator().validate(data)


def validate_weibo_batch(data_list: List[Dict], 
                        check_duplicates: bool = True,
                        auto_fix: bool = True) -> Tuple[List[Dict], DataQualityMetrics]:
    """批量验证微博数据"""
    return get_validator().validate_batch(data_list, check_duplicates, auto_fix)


def generate_quality_report(metrics: DataQualityMetrics, 
                           task_id: str = None) -> Dict:
    """生成质量报告"""
    return get_validator().generate_quality_report(metrics, task_id)


def get_data_quality_summary() -> Dict:
    """获取数据质量摘要"""
    return get_validator().get_latest_quality_summary()
