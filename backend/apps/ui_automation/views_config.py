from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import shutil
import subprocess
import platform
import os
import json
import logging

logger = logging.getLogger(__name__)

class EnvironmentConfigViewSet(viewsets.ViewSet):
    """
    UI自动化环境配置视图集
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def check_environment(self, request):
        """
        检测环境状态 (系统浏览器和Playwright浏览器)
        """
        import sys
        
        # 1. 检测系统浏览器 (Selenium常用)
        system_browsers_list = ['chrome', 'firefox', 'edge'] # Safari not on Windows usually
        if platform.system() == 'Darwin':
             system_browsers_list.append('safari')
             
        system_results = []

        is_windows = platform.system() == 'Windows'

        for browser in system_browsers_list:
            installed = False
            version = None
            install_cmd = ""
            
            if browser == 'chrome':
                if is_windows:
                    paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            installed = True
                            break
                    install_cmd = "请下载 Chrome 安装包安装"
                elif platform.system() == 'Darwin':  # macOS
                    if os.path.exists('/Applications/Google Chrome.app'):
                        installed = True
                    install_cmd = "brew install --cask google-chrome"
                else:  # Linux
                    chrome_paths = [
                        '/usr/bin/google-chrome',
                        '/usr/bin/google-chrome-stable',
                        '/usr/bin/chromium-browser',
                        '/usr/bin/chromium',
                        '/opt/google/chrome/google-chrome',
                        '/snap/bin/chromium'
                    ]
                    for path in chrome_paths:
                        if os.path.exists(path):
                            installed = True
                            break
                    install_cmd = "sudo dnf install chromium 或 sudo dnf install google-chrome-stable"
                    
            elif browser == 'firefox':
                if is_windows:
                    paths = [
                        r"C:\Program Files\Mozilla Firefox\firefox.exe",
                        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            installed = True
                            break
                    install_cmd = "请下载 Firefox 安装包安装"
                elif platform.system() == 'Darwin':  # macOS
                    if os.path.exists('/Applications/Firefox.app'):
                        installed = True
                    install_cmd = "brew install --cask firefox"
                else:  # Linux
                    firefox_paths = [
                        '/usr/bin/firefox',
                        '/usr/bin/firefox-esr'
                    ]
                    for path in firefox_paths:
                        if os.path.exists(path):
                            installed = True
                            break
                    install_cmd = "sudo dnf install firefox"
                    
            elif browser == 'safari':
                if not is_windows and os.path.exists('/Applications/Safari.app'):
                    installed = True
                install_cmd = "系统自带"
                
            elif browser == 'edge':
                if is_windows:
                    paths = [
                         r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            installed = True
                            break
                    install_cmd = "请下载 Edge 安装包安装"
                elif platform.system() == 'Darwin':  # macOS
                    if os.path.exists('/Applications/Microsoft Edge.app'):
                        installed = True
                    install_cmd = "brew install --cask microsoft-edge"
                else:  # Linux
                    edge_paths = [
                        '/usr/bin/microsoft-edge',
                        '/usr/bin/microsoft-edge-stable',
                        '/opt/microsoft/msedge/msedge'
                    ]
                    for path in edge_paths:
                        if os.path.exists(path):
                            installed = True
                            break
                    install_cmd = "从微软官网下载 Edge Linux 版本安装包"

            system_results.append({
                'name': browser,
                'installed': installed,
                'version': version, # Version check omitted for simplicity/performance
                'install_cmd': install_cmd
            })

        # 2. 检测Playwright浏览器
        playwright_browsers_list = ['chromium', 'firefox', 'webkit']
        playwright_results = []
        
        # Playwright 缓存路径
        if is_windows:
            playwright_cache_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'ms-playwright')
        elif platform.system() == 'Darwin':  # macOS
            playwright_cache_dir = os.path.expanduser('~/Library/Caches/ms-playwright')
        else:  # Linux
            playwright_cache_dir = os.path.expanduser('~/.cache/ms-playwright')
        
        # 调试信息：打印缓存路径
        print(f"Playwright cache dir: {playwright_cache_dir}")

        for browser in playwright_browsers_list:
            installed = False
            version = None
            install_cmd = f"playwright install {browser}"
            
            # 检查缓存目录中是否有对应的浏览器文件夹
            if os.path.exists(playwright_cache_dir):
                for dirname in os.listdir(playwright_cache_dir):
                    # 匹配规则: chromium-123456, firefox-1234, webkit-1234
                    # 注意: 有时候是 chromium-vxxxx
                    if dirname.startswith(browser + '-'):
                        installed = True
                        version = dirname.split('-')[-1]
                        break
            
            playwright_results.append({
                'name': browser,
                'installed': installed,
                'version': version,
                'install_cmd': install_cmd
            })

        has_system_browser = any(b['installed'] for b in system_results)
        has_playwright_browser = any(b['installed'] for b in playwright_results)
        
        if not has_system_browser and not has_playwright_browser:
            auto_setup_results = self._auto_setup_if_needed()
            return Response({
                'os': platform.system(),
                'system_browsers': system_results,
                'playwright_browsers': playwright_results,
                'auto_setup': auto_setup_results
            })
        
        return Response({
            'os': platform.system(),
            'system_browsers': system_results,
            'playwright_browsers': playwright_results
        })

    def _auto_setup_if_needed(self):
        """
        自动配置环境（当检测到没有可用浏览器时调用）
        自动下载Chromium到huanjing目录并安装Playwright驱动
        """
        results = {
            'success': True,
            'steps': [],
            'chromium_path': None,
            'message': ''
        }
        
        results['steps'].append("⚠️ 未找到系统浏览器和Playwright浏览器，开始自动下载Chromium...")
        
        chromium_path, msg = _download_chromium()
        if chromium_path:
            results['steps'].append(f"✅ {msg}: {chromium_path}")
            results['chromium_path'] = chromium_path
        else:
            results['steps'].append(f"❌ 自动下载失败: {msg}")
            results['success'] = False
            results['message'] = "环境配置失败，请手动安装Chrome浏览器"
            return results
        
        results['steps'].append("📦 安装Playwright浏览器驱动...")
        try:
            import sys
            result = subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], 
                                   capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                results['steps'].append("✅ Playwright驱动安装成功")
            else:
                results['steps'].append(f"⚠️ Playwright安装警告: {result.stderr[:200]}")
        except Exception as e:
            results['steps'].append(f"⚠️ Playwright安装失败: {str(e)}")
        
        results['message'] = "环境配置完成"
        return results

    @action(detail=False, methods=['post'])
    def install_driver(self, request):
        """
        安装浏览器驱动
        """
        browser = request.data.get('browser')
        if not browser:
            return Response({'error': 'Browser name is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 使用当前 Python 环境执行模块安装命令
            import sys
            subprocess.run([sys.executable, '-m', 'playwright', 'install', browser], check=True)
            return Response({'message': f'Successfully installed driver for {browser}'})
        except subprocess.CalledProcessError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import requests
from apps.requirement_analysis.models import AIModelConfig, AIModelService
import zipfile

def _download_chromium():
    """自动下载Chromium到backend/huanjing/目录"""
    huanjing_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'huanjing')
    os.makedirs(huanjing_dir, exist_ok=True)
    
    system = platform.system()
    download_url = None
    extract_name = None
    executable_name = None
    
    if system == 'Windows':
        download_url = 'https://storage.googleapis.com/chromium-browser-snapshots/Win/1429927/chrome-win.zip'
        extract_name = 'chrome-win'
        executable_name = 'chrome.exe'
    elif system == 'Linux':
        download_url = 'https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1429927/chrome-linux.zip'
        extract_name = 'chrome-linux'
        executable_name = 'chrome'
    else:
        return None, "不支持的操作系统"
    
    extract_path = os.path.join(huanjing_dir, extract_name)
    executable_path = os.path.join(extract_path, executable_name)
    
    if os.path.exists(executable_path):
        return executable_path, "Chromium已存在"
    
    zip_path = os.path.join(huanjing_dir, f'{extract_name}.zip')
    
    try:
        logger.info(f"开始下载Chromium: {download_url}")
        
        response = requests.get(download_url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
        
        logger.info("下载完成，开始解压...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(huanjing_dir)
        
        os.remove(zip_path)
        
        if os.path.exists(executable_path):
            os.chmod(executable_path, 0o755)
            return executable_path, "Chromium安装完成"
        else:
            return None, "解压后未找到可执行文件"
            
    except Exception as e:
        logger.error(f"自动下载Chromium失败: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return None, str(e)


class EnvironmentAutoSetupViewSet(viewsets.ViewSet):
    """
    环境自动配置视图集
    检测到环境缺失时自动触发下载流程
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def auto_setup(self, request):
        """
        自动检测并配置环境
        当检测到浏览器缺失时，自动下载Chromium到huanjing目录
        """
        results = {
            'success': True,
            'steps': [],
            'chromium_path': None,
            'message': ''
        }
        
        # 1. 检查系统浏览器
        is_windows = platform.system() == 'Windows'
        chrome_found = False
        
        if is_windows:
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            for p in paths:
                if os.path.exists(p):
                    chrome_found = True
                    results['steps'].append(f"✅ 找到系统Chrome: {p}")
                    results['chromium_path'] = p
                    break
        else:
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/opt/google/chrome/google-chrome',
                '/snap/bin/chromium'
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_found = True
                    results['steps'].append(f"✅ 找到系统浏览器: {path}")
                    results['chromium_path'] = path
                    break
        
        # 2. 检查Edge
        if not chrome_found:
            if is_windows:
                paths = [
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                ]
                for p in paths:
                    if os.path.exists(p):
                        chrome_found = True
                        results['steps'].append(f"✅ 找到系统Edge: {p}")
                        results['chromium_path'] = p
                        break
        
        # 3. 如果没有找到系统浏览器，自动下载Chromium
        if not chrome_found:
            results['steps'].append("⚠️ 未找到系统浏览器，开始自动下载Chromium...")
            chromium_path, msg = _download_chromium()
            if chromium_path:
                results['steps'].append(f"✅ {msg}: {chromium_path}")
                results['chromium_path'] = chromium_path
            else:
                results['steps'].append(f"❌ 自动下载失败: {msg}")
                results['success'] = False
                results['message'] = "环境配置失败，请手动安装Chrome浏览器"
                return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 4. 安装Playwright驱动
        results['steps'].append("📦 安装Playwright浏览器驱动...")
        try:
            import sys
            result = subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], 
                                   capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                results['steps'].append("✅ Playwright驱动安装成功")
            else:
                results['steps'].append(f"⚠️ Playwright安装警告: {result.stderr[:200]}")
        except Exception as e:
            results['steps'].append(f"⚠️ Playwright安装失败: {str(e)}")
        
        results['message'] = "环境配置完成"
        return Response(results)

class AIIntelligentModeConfigViewSet(viewsets.ViewSet):
    """
    AI智能模式配置视图集 (Browser-use) - 使用ModelViewSet支持标准CRUD
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIModelConfig.objects.all()

    @property
    def queryset(self):
        return self.get_queryset()

    def list(self, request):
        """
        获取所有AI智能模式配置列表
        """
        configs = self.get_queryset().order_by('-created_at')
        serializer_data = [{
            'id': config.id,
            'name': config.name,
            'model_type': config.model_type,
            'model_name': config.model_name,
            'base_url': config.base_url,
            'is_active': config.is_active,
            'api_key_length': len(config.api_key) if config.api_key else 0,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        } for config in configs]
        return Response(serializer_data)

    def create(self, request):
        """
        创建新的AI智能模式配置
        """
        data = request.data
        user = request.user

        required_fields = ['name', 'model_type', 'model_name', 'api_key']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {'error': f'{field} is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        config = AIModelConfig.objects.create(
            name=data['name'],
            model_type=data['model_type'],
            model_name=data['model_name'],
            api_key=data['api_key'],
            base_url=data.get('base_url', ''),
            is_active=data.get('is_active', True),
            created_by=user
        )

        return Response({
            'id': config.id,
            'name': config.name,
            'model_type': config.model_type,
            'model_name': config.model_name,
            'base_url': config.base_url,
            'is_active': config.is_active,
            'created_at': config.created_at
        }, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """
        获取单个配置详情
        """
        try:
            config = self.get_queryset().get(pk=pk)
            return Response({
                'id': config.id,
                'name': config.name,
                'model_type': config.model_type,
                'model_name': config.model_name,
                'base_url': config.base_url,
                'is_active': config.is_active,
                'created_at': config.created_at,
                'updated_at': config.updated_at
            })
        except AIModelConfig.DoesNotExist:
            return Response(
                {'error': 'Config not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def update(self, request, pk=None):
        """
        更新配置 (PUT)
        """
        try:
            config = self.get_queryset().get(pk=pk)
            data = request.data

            if 'name' in data:
                config.name = data['name']
            if 'model_type' in data:
                config.model_type = data['model_type']
            if 'model_name' in data:
                config.model_name = data['model_name']
            if 'api_key' in data and data['api_key']:
                config.api_key = data['api_key']
            if 'base_url' in data:
                config.base_url = data['base_url']
            if 'is_active' in data:
                config.is_active = data['is_active']

            config.save()

            response_data = {
                'id': config.id,
                'name': config.name,
                'model_type': config.model_type,
                'model_name': config.model_name,
                'base_url': config.base_url,
                'is_active': config.is_active,
                'created_at': config.created_at,
                'updated_at': config.updated_at
            }

            # 如果禁用了其他配置,返回被禁用的配置名称
            if disabled_config_names:
                response_data['disabled_configs'] = disabled_config_names

            return Response(response_data)
        except AIModelConfig.DoesNotExist:
            return Response(
                {'error': 'Config not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, pk=None):
        """
        部分更新配置 (PATCH)
        """
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        """
        删除配置
        """
        try:
            config = self.get_queryset().get(pk=pk)
            config.delete()
            return Response(
                {'message': 'Config deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except AIModelConfig.DoesNotExist:
            return Response(
                {'error': 'Config not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='test_connection')
    def test_connection_preview(self, request):
        """
        测试模型连接 (在保存前测试，不保存配置)
        """
        provider = request.data.get('provider')
        base_url = request.data.get('base_url')
        api_key = request.data.get('api_key')
        model_name = request.data.get('model_name')

        if not api_key:
            return Response(
                {'error': 'API Key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not base_url:
            base_url = AIModelService.default_base_url(provider)

        if not base_url:
             return Response(
                 {'error': 'Base URL is required for this provider'},
                 status=status.HTTP_400_BAD_REQUEST
             )

        temp_config = type('TempConfig', (), {
            'api_key': api_key,
            'model_name': model_name,
            'model_type': provider,
            'base_url': base_url,
        })()
        ok, errors = AIModelService.validate_model_config(temp_config)
        if not ok:
            return Response({'error': '配置不可用: ' + '；'.join(errors)}, status=status.HTTP_400_BAD_REQUEST)

        url = AIModelService.build_chat_completions_url(base_url, provider)

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }

            logger.info(f"AI智能模式预览 - 发送POST请求到: {url}")
            response = requests.post(url, headers=headers, json=data, timeout=(15, 45))

            logger.info(f"AI智能模式预览 - 收到响应: status_code={response.status_code}")

            if response.status_code == 200:
                return Response({'message': '连接成功'})
            else:
                logger.error(f"AI智能模式 - API调用返回错误: Status={response.status_code}, Body={response.text}")
                return Response(
                    {'error': f'连接失败: {response.status_code} - {response.text}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except requests.exceptions.Timeout as e:
            logger.error(f"AI智能模式 - API连接测试超时: {repr(e)}")
            return Response(
                {'error': '连接测试超时: 请检查网络连接或API地址是否正确'},
                status=status.HTTP_408_REQUEST_TIMEOUT
            )
        except Exception as e:
            logger.error(f"AI智能模式 - API连接测试异常: {repr(e)}")
            return Response(
                {'error': f'连接异常: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        测试已保存配置的连接
        """
        try:
            config = self.get_queryset().get(pk=pk)
        except AIModelConfig.DoesNotExist:
            return Response(
                {'error': 'Config not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        logger.info(f"=== AI智能模式 - 开始测试模型连接 ===")
        logger.info(f"模型类型: {config.model_type}")
        logger.info(f"模型名称: {config.model_name}")
        logger.info(f"API URL: {config.base_url}")
        if not config.api_key:
            return Response(
                {'error': 'API Key is required before testing the model connection'},
                status=status.HTTP_400_BAD_REQUEST
            )
        logger.info(f"API Key前缀: {config.api_key[:10]}..." if len(config.api_key) > 10 else f"API Key: {config.api_key}")

        ok, errors = AIModelService.validate_model_config(config)
        if not ok:
            return Response({'error': '配置不可用: ' + '；'.join(errors)}, status=status.HTTP_400_BAD_REQUEST)

        base_url = config.base_url or AIModelService.default_base_url(config.model_type)

        if not base_url:
            return Response(
                {'error': 'Base URL is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        url = AIModelService.build_chat_completions_url(base_url, config.model_type)

        try:
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }

            logger.info(f"AI智能模式 - 发送POST请求到: {url}")
            response = requests.post(url, headers=headers, json=data, timeout=(15, 45))

            logger.info(f"AI智能模式 - 收到响应: status_code={response.status_code}")

            if response.status_code == 200:
                logger.info("AI智能模式 - API连接测试成功")
                return Response({'message': '连接成功'})
            else:
                logger.error(f"AI智能模式 - API调用返回错误: Status={response.status_code}, Body={response.text}")
                return Response(
                    {'error': f'连接失败: {response.status_code} - {response.text}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except requests.exceptions.Timeout as e:
            logger.error(f"AI智能模式 - API连接测试超时: {repr(e)}")
            return Response(
                {'error': '连接测试超时: 请检查网络连接或API地址是否正确'},
                status=status.HTTP_408_REQUEST_TIMEOUT
            )
        except Exception as e:
            logger.error(f"AI智能模式 - API连接测试异常: {repr(e)}")
            return Response(
                {'error': f'连接异常: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
