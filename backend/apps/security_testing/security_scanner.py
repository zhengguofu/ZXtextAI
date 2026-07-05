"""
真实安全扫描引擎
支持 SQL 注入、XSS、CSRF、安全头检查、端口扫描等常见漏洞检测
"""

import re
import socket
import ssl
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.exceptions import RequestException
import logging

logger = logging.getLogger(__name__)

TIMEOUT = 10
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ZX-SecurityScanner/2.0'

# 常见端口扫描列表
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 1433, 1521, 3306, 3389, 5432, 6379, 8080, 8443, 9090]

# SQL 注入测试 Payload
SQLI_PAYLOADS = [
    ("' OR '1'='1", "字符串闭合注入"),
    ("' OR 1=1 --", "数字型注释注入"),
    ("' UNION SELECT 1,2,3 --", "UNION 查询注入"),
    ("1' AND 1=1 --", "AND 布尔盲注"),
    ("1' AND SLEEP(5) --", "时间盲注"),
    ('" OR "1"="1', "双引号闭合"),
    ("1; DROP TABLE users --", "堆叠查询"),
]

# XSS 测试 Payload
XSS_PAYLOADS = [
    ("<script>alert(1)</script>", "基础 script 标签"),
    ('<img src=x onerror=alert(1)>', "img onerror"),
    ('<svg onload=alert(1)>', "SVG onload"),
    ('javascript:alert(1)', "javascript: 协议"),
    ('"><script>alert(1)</script>', "属性闭合注入"),
    ("<body onload=alert(1)>", "body onload"),
]

# 安全检查列表
SECURITY_HEADERS = {
    'Content-Security-Policy': '内容安全策略',
    'X-Content-Type-Options': 'MIME 类型嗅探防护',
    'X-Frame-Options': '点击劫持防护',
    'X-XSS-Protection': 'XSS 过滤器',
    'Strict-Transport-Security': 'HSTS 强制 HTTPS',
    'Referrer-Policy': '引用策略',
    'Permissions-Policy': '权限策略',
    'X-Permitted-Cross-Domain-Policies': '跨域策略',
}

# 敏感路径探测
SENSITIVE_PATHS = [
    '/.git/HEAD',
    '/.env',
    '/.env.backup',
    '/backup/',
    '/phpinfo.php',
    '/info.php',
    '/wp-admin/',
    '/administrator/',
    '/api/admin/',
    '/admin/',
    '/config/',
    '/.DS_Store',
    '/robots.txt',
    '/sitemap.xml',
    '/swagger-ui.html',
    '/swagger/',
    '/api-docs/',
    '/actuator/health',
    '/debug/',
    '/debug/default/view',
    '/console/',
    '/test.php',
    '/phpmyadmin/',
    '/db/',
]

# 信息泄露正则
INFO_LEAK_PATTERNS = [
    (r'(?:password|passwd|pwd)\s*[:=]\s*["\']?[\w!@#$%^&*()-+=]+["\']?', '密码硬编码'),
    (r'(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*["\']?[\w-]+["\']?', 'API Key 泄露'),
    (r'(?:secret|token)\s*[:=]\s*["\']?[\w.-]+["\']?', '敏感令牌泄露'),
    (r'(?:jdbc|mysql|postgresql):\/\/[^\s"\']+', '数据库连接串泄露'),
    (r'-----BEGIN\s(?:RSA\s)?PRIVATE\sKEY-----', '私钥泄露'),
    (r'(?:access_key|secret_key|SECRET)\s*[:=]\s*["\']?[\w/-]+["\']?', '云服务密钥泄露'),
]


class SecurityScanner:
    """真实安全扫描器"""

    def __init__(self, target_url, task_id=None):
        self.target_url = target_url.rstrip('/') if target_url else ''
        self.task_id = task_id
        self.session = self._create_session()
        self.findings = []

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        session.verify = False
        session.timeout = TIMEOUT
        # 禁用 SSL 警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return session

    def _add_finding(self, title, detail, severity, remediation=''):
        self.findings.append({
            'title': title,
            'detail': detail,
            'severity': severity,
            'target': self.target_url,
            'remediation': remediation or '请参考相关安全修复指南进行处理。'
        })

    def _parse_host(self):
        """从 URL 提取主机名"""
        parsed = urllib.parse.urlparse(self.target_url)
        return parsed.hostname or self.target_url

    def run_full_scan(self):
        """执行完整安全扫描"""
        if not self.target_url:
            self._add_finding('目标地址为空', '无法执行扫描，目标地址未设置', 'info')
            return self.findings

        logger.info(f"开始安全扫描: {self.target_url}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self.scan_sql_injection),
                executor.submit(self.scan_xss),
                executor.submit(self.scan_security_headers),
                executor.submit(self.scan_sensitive_paths),
                executor.submit(self.scan_info_leak),
                executor.submit(self.scan_open_ports),
                executor.submit(self.scan_csrf),
                executor.submit(self.scan_ssl_tls),
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"扫描模块异常: {e}")

        logger.info(f"安全扫描完成，发现 {len(self.findings)} 个问题")
        return self.findings

    def scan_sql_injection(self):
        """SQL 注入检测"""
        # 尝试在 URL 参数中注入
        parsed = urllib.parse.urlparse(self.target_url)
        if not parsed.query:
            return

        params = urllib.parse.parse_qs(parsed.query)
        base_url = self.target_url.split('?')[0]

        for payload, desc in SQLI_PAYLOADS:
            test_params = {}
            for key in params:
                test_params[key] = payload

            try:
                # 先发正常请求获取基准
                resp_base = self.session.get(self.target_url)
                base_len = len(resp_base.text)

                resp = self.session.get(base_url, params=test_params)
                resp_len = len(resp_base.text)

                # 检测响应差异
                if abs(resp_len - base_len) > 500:
                    error_indicators = [
                        'sql', 'syntax', 'mysql', 'oracle', 'postgresql',
                        'sqlite', 'microsoft', 'odbc', 'database', 'error',
                        'warning', 'unclosed', 'quotation'
                    ]
                    text_lower = resp.text.lower()
                    for indicator in error_indicators:
                        if indicator in text_lower:
                            self._add_finding(
                                f'疑似 SQL 注入漏洞 ({desc})',
                                f'使用 Payload "{payload}" 测试发现响应中包含数据库错误信息: {indicator}。响应长度变化: {base_len} -> {resp_len}',
                                'critical',
                                '使用参数化查询或预编译语句，对所有用户输入进行严格过滤和转义。'
                            )
                            return
            except RequestException:
                continue

    def scan_xss(self):
        """XSS 跨站脚本检测"""
        parsed = urllib.parse.urlparse(self.target_url)
        base_url = self.target_url.split('?')[0]

        for payload, desc in XSS_PAYLOADS:
            try:
                test_url = f"{base_url}?q={urllib.parse.quote(payload)}"
                resp = self.session.get(test_url)

                if payload in resp.text:
                    self._add_finding(
                        f'XSS 跨站脚本漏洞 ({desc})',
                        f'Payload "{payload}" 被原样反射到响应页面中，存在反射型 XSS 风险。',
                        'high',
                        '对所有用户输入进行 HTML 实体编码输出，使用 Content-Security-Policy 头。'
                    )
                    return
            except RequestException:
                continue

    def scan_security_headers(self):
        """安全响应头检查"""
        try:
            resp = self.session.get(self.target_url)
            headers = resp.headers

            missing_headers = []
            existing_headers = []

            for header, desc in SECURITY_HEADERS.items():
                if header not in headers:
                    missing_headers.append(f'{desc}({header})')
                else:
                    existing_headers.append(f'{desc}({header})')

            if missing_headers:
                self._add_finding(
                    f'缺少 {len(missing_headers)} 个安全响应头',
                    f'缺失的安全头: {", ".join(missing_headers)}\n\n已配置的安全头: {", ".join(existing_headers) if existing_headers else "无"}',
                    'medium',
                    '在 Web 服务器或应用框架中配置缺失的安全响应头。'
                )
        except RequestException as e:
            self._add_finding('无法获取安全响应头', f'请求失败: {str(e)}', 'info')

    def scan_sensitive_paths(self):
        """敏感路径探测"""
        found_paths = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_map = {}
            for path in SENSITIVE_PATHS:
                test_url = f"{self.target_url}{path}"
                future_map[executor.submit(self._check_path, test_url)] = path

            for future in as_completed(future_map):
                path = future_map[future]
                try:
                    status_code, content = future.result()
                    if status_code is not None and status_code < 404:
                        found_paths.append({
                            'path': path,
                            'status': status_code
                        })
                except Exception:
                    pass

        if found_paths:
            paths_detail = '\n'.join([f"- {p['path']} (HTTP {p['status']})" for p in found_paths])
            self._add_finding(
                f'发现 {len(found_paths)} 个敏感路径',
                f'以下路径可被访问:\n{paths_detail}\n\n这些路径可能泄露系统信息或提供管理入口。',
                'high',
                '对敏感路径进行访问控制，将其从生产环境移除或限制访问 IP。'
            )

    def _check_path(self, url):
        """检测单个路径是否可访问"""
        try:
            resp = self.session.head(url, allow_redirects=False, timeout=5)
            if resp.status_code == 405:
                resp = self.session.get(url, allow_redirects=False, timeout=5)
            return resp.status_code, resp.text[:200] if resp.status_code == 200 else ''
        except RequestException:
            return None, ''

    def scan_info_leak(self):
        """信息泄露检测"""
        try:
            resp = self.session.get(self.target_url)
            html = resp.text

            leaks = []
            for pattern, desc in INFO_LEAK_PATTERNS:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # 脱敏处理
                    masked = str(matches[0])[:30] + '...' if len(str(matches[0])) > 30 else str(matches[0])
                    leaks.append(f'- {desc}: {masked}')

            if leaks:
                self._add_finding(
                    f'发现 {len(leaks)} 处疑似信息泄露',
                    f'在页面响应中检测到以下敏感信息:\n{chr(10).join(leaks)}',
                    'critical',
                    '立即移除前端代码和 API 响应中的所有硬编码密钥和敏感信息，使用环境变量管理。'
                )
        except RequestException as e:
            self._add_finding('信息泄露检测失败', f'请求失败: {str(e)}', 'info')

    def scan_open_ports(self):
        """常见端口扫描"""
        host = self._parse_host()
        if not host:
            return

        open_ports = []
        for port in COMMON_PORTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    service = self._get_service_name(port)
                    open_ports.append(f'{port} ({service})')
                sock.close()
            except Exception:
                continue

        if open_ports:
            self._add_finding(
                f'发现 {len(open_ports)} 个开放端口',
                f'目标主机 {host} 开放端口: {", ".join(open_ports)}。开放的端口增加了攻击面。',
                'medium',
                '关闭不必要的端口，使用防火墙限制外部访问非必要端口。'
            )

    def _get_service_name(self, port):
        """端口 -> 服务名映射"""
        services = {
            21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP',
            53: 'DNS', 80: 'HTTP', 110: 'POP3', 143: 'IMAP',
            443: 'HTTPS', 993: 'IMAPS', 995: 'POP3S',
            1433: 'MSSQL', 1521: 'Oracle', 3306: 'MySQL',
            3389: 'RDP', 5432: 'PostgreSQL', 6379: 'Redis',
            8080: 'HTTP-Alt', 8443: 'HTTPS-Alt', 9090: 'Web-Admin'
        }
        return services.get(port, 'Unknown')

    def scan_csrf(self):
        """CSRF 跨站请求伪造检测"""
        try:
            resp = self.session.get(self.target_url)
            html = resp.text

            # 检查页面中是否存在表单
            forms = re.findall(r'<form[^>]*>', html, re.IGNORECASE)

            if forms:
                csrf_tokens = re.findall(
                    r'(?:csrf|xsrf|_token|authenticity_token|nonce)',
                    html, re.IGNORECASE
                )

                if not csrf_tokens:
                    # 尝试发送一个简单的 POST 请求
                    try:
                        post_resp = self.session.post(
                            self.target_url,
                            data={'test': 'csrf_check'},
                            headers={'Content-Type': 'application/x-www-form-urlencoded'}
                        )
                        if post_resp.status_code < 400:
                            self._add_finding(
                                '缺少 CSRF 防护',
                                f'页面包含 {len(forms)} 个表单但未检测到 CSRF Token。POST 请求可被接受，存在 CSRF 攻击风险。',
                                'high',
                                '在表单中添加 CSRF Token，验证 Referer/Origin 头，使用 SameSite Cookie。'
                            )
                    except RequestException:
                        pass
        except RequestException:
            pass

    def scan_ssl_tls(self):
        """SSL/TLS 配置检测"""
        host = self._parse_host()
        if not host or not self.target_url.startswith('https://'):
            return

        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()

                    if not cert:
                        self._add_finding(
                            'SSL 证书无效',
                            '无法获取有效的 SSL 证书信息。',
                            'high',
                            '安装有效的 SSL/TLS 证书。'
                        )
                        return

                    # 检查证书过期
                    import datetime
                    not_after = ssl.cert_time_to_seconds(cert.get('notAfter', ''))
                    expire_date = datetime.datetime.fromtimestamp(not_after)
                    days_left = (expire_date - datetime.datetime.now()).days

                    if days_left < 30:
                        self._add_finding(
                            f'SSL 证书即将过期 ({days_left}天后)',
                            f'证书过期日期: {expire_date.strftime("%Y-%m-%d")}',
                            'medium',
                            '及时更新 SSL 证书。'
                        )

                    # 检查 TLS 版本
                    if cipher and cipher[1].startswith('TLSv1.0') or cipher[1].startswith('TLSv1.1'):
                        self._add_finding(
                            '使用不安全的 TLS 版本',
                            f'当前 TLS 版本: {cipher[1]}，应升级到 TLS 1.2 或 1.3。',
                            'high',
                            '禁用 TLS 1.0/1.1，启用 TLS 1.2 及以上版本。'
                        )

        except ssl.SSLError as e:
            self._add_finding(
                'SSL/TLS 握手失败',
                f'SSL 连接错误: {str(e)[:200]}',
                'medium',
                '检查 SSL 证书配置是否完整和正确。'
            )
        except Exception:
            pass


def create_default_dashboard_stats(user):
    """为 Dashboard 提供真实统计（当没有扫描记录时）"""
    from .models import SecurityScanTask
    tasks = SecurityScanTask.objects.filter(created_by=user)
    total = tasks.count()
    completed = tasks.filter(status='completed')
    return {
        'total': total,
        'safe': completed.filter(high_risks=0).count(),
        'risk': completed.filter(high_risks__gt=0).count(),
        'high': tasks.filter(high_risks__gt=0).count(),
    }
