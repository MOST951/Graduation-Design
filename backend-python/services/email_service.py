"""
邮件服务 - 验证码发送
支持 QQ邮箱 / 163邮箱 / Gmail 等 SMTP 服务
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from datetime import datetime

logger = logging.getLogger(__name__)

def _get_smtp_config() -> dict:
    """每次调用时动态读取环境变量，确保 .env 更新后立即生效"""
    return {
        'server': os.getenv('SMTP_SERVER', 'smtp.qq.com'),
        'port': int(os.getenv('SMTP_PORT', '465')),
        'use_ssl': os.getenv('SMTP_USE_SSL', 'true').lower() == 'true',
        'user': os.getenv('SMTP_USER', ''),           # 发件邮箱
        'password': os.getenv('SMTP_PASSWORD', ''),    # 授权码（非登录密码）
        'from_name': os.getenv('SMTP_FROM_NAME', '微博舆情分析系统'),
    }


def _build_code_html(code: str, expire_minutes: int = 5) -> str:
    """构建验证码邮件 HTML 模板"""
    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:'Microsoft YaHei',Arial,sans-serif;">
      <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:32px 24px;border-radius:12px 12px 0 0;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:22px;">微博舆情分析系统</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:13px;">Weibo Sentiment Analysis Platform</p>
      </div>
      <div style="background:#fff;padding:32px 24px;border:1px solid #e8e8e8;border-top:none;">
        <p style="color:#333;font-size:15px;line-height:1.8;">您好，</p>
        <p style="color:#333;font-size:15px;line-height:1.8;">您正在进行账号注册操作，验证码为：</p>
        <div style="text-align:center;margin:24px 0;">
          <span style="display:inline-block;padding:14px 40px;background:#f6f8fc;border:2px dashed #667eea;border-radius:8px;font-size:32px;font-weight:700;letter-spacing:8px;color:#667eea;">
            {code}
          </span>
        </div>
        <p style="color:#999;font-size:13px;line-height:1.8;">
          ⏱ 验证码 <strong>{expire_minutes} 分钟</strong>内有效，请勿泄露给他人。<br>
          如非本人操作，请忽略此邮件。
        </p>
      </div>
      <div style="background:#fafafa;padding:16px 24px;border-radius:0 0 12px 12px;border:1px solid #e8e8e8;border-top:none;text-align:center;">
        <p style="color:#bbb;font-size:11px;margin:0;">
          本科毕业设计 · 罗森 · 2022407443 · {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </p>
      </div>
    </div>
    """


def send_verification_email(to_email: str, code: str, expire_minutes: int = 5) -> bool:
    """
    发送验证码邮件

    Args:
        to_email: 收件人邮箱
        code: 6 位验证码
        expire_minutes: 有效时间（分钟）

    Returns:
        True 发送成功，False 发送失败
    """
    cfg = _get_smtp_config()
    smtp_user = cfg['user']
    smtp_password = cfg['password']

    if not smtp_user or not smtp_password:
        logger.warning('SMTP 未配置（SMTP_USER / SMTP_PASSWORD 为空），跳过邮件发送')
        return False

    try:
        # 构建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(f'【舆情分析系统】验证码：{code}', 'utf-8')
        msg['From'] = formataddr((str(Header(cfg['from_name'], 'utf-8')), smtp_user))
        msg['To'] = to_email

        html_body = _build_code_html(code, expire_minutes)
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # 发送
        if cfg['use_ssl']:
            # SSL 直连（QQ邮箱 465 端口）
            with smtplib.SMTP_SSL(cfg['server'], cfg['port']) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            # STARTTLS（Gmail 587 端口）
            with smtplib.SMTP(cfg['server'], cfg['port']) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

        logger.info(f'验证码邮件已发送: {to_email}')
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(f'SMTP 认证失败，请检查 SMTP_USER 和 SMTP_PASSWORD（授权码）')
        return False
    except smtplib.SMTPException as e:
        logger.error(f'邮件发送失败: {e}')
        return False
    except Exception as e:
        logger.error(f'邮件发送异常: {e}', exc_info=True)
        return False
