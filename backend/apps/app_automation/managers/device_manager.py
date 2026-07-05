# -*- coding: utf-8 -*-
import subprocess
import logging
import platform
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _discover_tools() -> dict:
    """
    自动发现 tools/ 目录下的 ADB 和 scrcpy 工具路径。
    优先级：tools/adb/adb.exe > tools/scrcpy/*/adb.exe > 系统 PATH
    """
    base_dir = Path(__file__).resolve().parent.parent.parent.parent  # ZXtextAI/
    tools_dir = base_dir / 'tools'

    result = {'adb': 'adb', 'scrcpy': None}

    # 查找 ADB
    adb_candidates = [
        tools_dir / 'adb' / 'adb.exe',
        base_dir / 'adb.exe',
    ]
    # 同时搜索 scrcpy 目录下的 adb
    scrcpy_dir = tools_dir / 'scrcpy'
    if scrcpy_dir.exists():
        for item in scrcpy_dir.iterdir():
            if item.is_dir():
                adb_candidates.append(item / 'adb.exe')
                adb_candidates.append(item / 'adb')

    for candidate in adb_candidates:
        if candidate.exists():
            result['adb'] = str(candidate)
            logger.info(f"[DeviceManager] 自动发现 ADB: {result['adb']}")
            break

    # 查找 scrcpy
    if scrcpy_dir.exists():
        for item in scrcpy_dir.iterdir():
            if item.is_dir():
                scrcpy_exe = item / 'scrcpy.exe'
                if scrcpy_exe.exists():
                    result['scrcpy'] = str(scrcpy_exe)
                    logger.info(f"[DeviceManager] 自动发现 scrcpy: {result['scrcpy']}")
                    break

    return result


class DeviceManager:
    """设备管理器 - Android ADB 设备管理 + 投屏"""

    _tools_cache = None

    def __init__(self, adb_path='adb', scrcpy_path=None):
        # 自动发现工具路径
        if DeviceManager._tools_cache is None:
            DeviceManager._tools_cache = _discover_tools()

        self.adb_path = adb_path if adb_path and adb_path != 'adb' else DeviceManager._tools_cache['adb']
        self.scrcpy_path = scrcpy_path or DeviceManager._tools_cache.get('scrcpy')

        # 设置跨平台的subprocess参数
        self.subprocess_kwargs = {}
        if platform.system() == 'Windows':
            self.subprocess_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    
    def _verify_adb(self):
        """验证ADB是否可用"""
        try:
            result = subprocess.run(
                [self.adb_path, 'version'],
                capture_output=True,
                text=True,
                timeout=5,
                **self.subprocess_kwargs
            )
            if result.returncode != 0:
                logger.warning(f"ADB验证失败: {result.stderr}")
                return False
            logger.info(f"ADB验证成功: {result.stdout.strip()}")
            return True
        except FileNotFoundError:
            logger.error(f"找不到ADB命令: {self.adb_path}")
            raise Exception(f"找不到ADB命令: {self.adb_path}，请检查ADB路径配置")
        except subprocess.TimeoutExpired:
            logger.error("ADB验证超时")
            raise Exception("ADB验证超时，请检查ADB是否正常工作")
        except Exception as e:
            logger.error(f"ADB验证异常: {str(e)}")
            raise
    
    def list_devices(self):
        """
        获取设备列表
        返回: [{'device_id': 'xxx', 'status': 'online', ...}, ...]
        """
        try:
            # Verify ADB is available before running commands
            self._verify_adb()
            
            logger.info(f"执行ADB命令: {self.adb_path} devices -l")
            result = subprocess.run(
                [self.adb_path, 'devices', '-l'],
                capture_output=True,
                text=True,
                timeout=10,
                **self.subprocess_kwargs
            )
            
            if result.returncode != 0:
                logger.error(f"ADB命令执行失败: {result.stderr}")
                raise Exception(f"ADB命令执行失败: {result.stderr}")
            
            logger.info(f"ADB输出: {result.stdout}")
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('*'):
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = 'online' if parts[1] == 'device' else 'offline'
                    
                    # 解析设备信息
                    device_info = {
                        'device_id': device_id,
                        'status': status,
                        'name': None,
                        'android_version': None,
                        'ip_address': None,
                        'port': 5555
                    }
                    
                    # 如果是远程设备，解析IP和端口
                    if ':' in device_id:
                        ip_port = device_id.split(':')
                        device_info['ip_address'] = ip_port[0]
                        device_info['port'] = int(ip_port[1]) if len(ip_port) > 1 else 5555
                    
                    # 获取设备详细信息
                    if status == 'online':
                        try:
                            device_info.update(self.get_device_info(device_id))
                        except Exception:
                            pass
                    
                    devices.append(device_info)
            
            logger.info(f"找到 {len(devices)} 个设备")
            return devices
            
        except subprocess.TimeoutExpired:
            logger.error("ADB命令执行超时")
            raise Exception("ADB命令执行超时")
        except Exception as e:
            logger.error(f"获取设备列表失败: {str(e)}")
            raise Exception(f"获取设备列表失败: {str(e)}")
    
    def get_device_info(self, device_id):
        """
        获取设备详细信息
        """
        info = {}
        
        try:
            # 获取设备名称
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
                capture_output=True,
                text=True,
                timeout=5,
                **self.subprocess_kwargs
            )
            if result.returncode == 0:
                info['name'] = result.stdout.strip()
            
            # 获取Android版本
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'],
                capture_output=True,
                text=True,
                timeout=5,
                **self.subprocess_kwargs
            )
            if result.returncode == 0:
                info['android_version'] = result.stdout.strip()
                
        except Exception as e:
            logger.warning(f"获取设备 {device_id} 详细信息失败: {str(e)}")
        
        return info
    
    def connect_device(self, ip_address, port=5555):
        """
        连接远程设备
        返回: {'device_id': 'xxx', 'status': 'online', ...} 或 None
        """
        try:
            device_address = f"{ip_address}:{port}"
            logger.info(f"连接设备: {device_address}")
            
            # 执行连接命令
            result = subprocess.run(
                [self.adb_path, 'connect', device_address],
                capture_output=True,
                text=True,
                timeout=30,
                **self.subprocess_kwargs
            )
            
            if result.returncode != 0:
                logger.error(f"连接失败: {result.stderr}")
                raise Exception(f"连接失败: {result.stderr}")
            
            # 检查连接结果
            output = result.stdout.strip()
            logger.info(f"连接结果: {output}")
            if 'connected' in output.lower() or 'already connected' in output.lower():
                # 获取设备信息
                device_info = {
                    'device_id': device_address,
                    'status': 'online',
                    'ip_address': ip_address,
                    'port': port,
                    'name': None,
                    'android_version': None
                }
                
                # 获取详细信息
                try:
                    device_info.update(self.get_device_info(device_address))
                except Exception as e:
                    logger.warning(f"获取设备详细信息失败: {str(e)}")
                
                logger.info(f"设备连接成功: {device_info}")
                return device_info
            else:
                logger.error(f"连接失败: {output}")
                raise Exception(f"连接失败: {output}")
                
        except subprocess.TimeoutExpired:
            logger.error("连接超时")
            raise Exception("连接超时，请检查设备网络")
        except Exception as e:
            logger.error(f"连接设备失败: {str(e)}")
            raise Exception(f"连接设备失败: {str(e)}")
    
    def disconnect_device(self, device_id: str) -> bool:
        """
        断开设备连接
        """
        try:
            logger.info(f"断开设备: {device_id}")
            result = subprocess.run(
                [self.adb_path, 'disconnect', device_id],
                capture_output=True,
                text=True,
                timeout=10,
                **self.subprocess_kwargs
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"设备断开成功: {device_id}")
            else:
                logger.error(f"设备断开失败: {result.stderr}")
            return success
            
        except Exception as e:
            logger.error(f"断开设备失败: {str(e)}")
            return False

    def capture_screenshot(self, device_id: str) -> bytes:
        """
        通过 ADB 截取设备屏幕，返回 PNG 字节数据。
        优先使用 screencap 命令，失败则尝试 exec-out。
        """
        try:
            # 方法1: exec-out (更高效，支持高版本 Android)
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'exec-out', 'screencap', '-p'],
                capture_output=True,
                timeout=10,
                **self.subprocess_kwargs
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout

            # 方法2: 传统 shell 方式
            logger.info(f"exec-out 失败，尝试 shell screencap: {result.stderr}")
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'screencap', '-p', '/sdcard/screen_tmp.png'],
                capture_output=True,
                timeout=10,
                **self.subprocess_kwargs
            )
            if result.returncode != 0:
                raise Exception(f"screencap 失败: {result.stderr}")

            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'pull', '/sdcard/screen_tmp.png', '-'],
                capture_output=True,
                timeout=10,
                **self.subprocess_kwargs
            )
            if result.returncode != 0:
                raise Exception(f"pull 失败: {result.stderr}")
            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"设备 {device_id} 截图超时")
            raise Exception("截图超时")
        except Exception as e:
            logger.error(f"设备 {device_id} 截图失败: {str(e)}")
            raise

    def start_screen_mirror(self, device_id: str, max_fps: int = 15, 
                           max_size: int = 1024, bit_rate: int = 8000000) -> subprocess.Popen:
        """
        使用 scrcpy 启动屏幕镜像（返回子进程）。
        如果 scrcpy 不可用则回退到 ADB 截图轮询方式。
        
        返回:
            Popen 进程对象，可用于后续停止。
        """
        if not self.scrcpy_path or not os.path.isfile(self.scrcpy_path):
            logger.warning(f"scrcpy 未找到 ({self.scrcpy_path})，无法启动镜像流")
            raise FileNotFoundError(f"scrcpy 未找到: {self.scrcpy_path}")

        cmd = [
            self.scrcpy_path,
            '-s', device_id,
            '--max-fps', str(max_fps),
            '--max-size', str(max_size),
            '--bit-rate', str(bit_rate),
            '--no-audio',
            '--no-window',           # 无 GUI 窗口
            '--no-playback',         # 不播放，仅录制
            '--record', '-',         # 输出到 stdout
        ]

        logger.info(f"启动 scrcpy 镜像: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **{k: v for k, v in self.subprocess_kwargs.items() if k != 'creationflags'}
        )
        return proc

    def scrcpy_record(self, device_id: str, output_path: str, duration: int = 0,
                     max_size: int = 1024, bit_rate: int = 8000000) -> subprocess.Popen:
        """
        使用 scrcpy 录制设备屏幕到本地文件。
        
        参数:
            device_id: 设备 ID
            output_path: 输出文件路径 (e.g. media/screen_records/xxx.mp4)
            duration: 录制时长(秒)，0=手动停止
            max_size: 最大分辨率
            bit_rate: 比特率
        返回:
            Popen 进程对象
        """
        if not self.scrcpy_path or not os.path.isfile(self.scrcpy_path):
            raise FileNotFoundError(f"scrcpy 未找到: {self.scrcpy_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        cmd = [
            self.scrcpy_path,
            '-s', device_id,
            '--max-size', str(max_size),
            '--bit-rate', str(bit_rate),
            '--no-audio',
            '--no-window',
            '--record', output_path,
        ]
        if duration > 0:
            cmd.extend(['--time-limit', str(duration)])

        logger.info(f"scrcpy 录制: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **{k: v for k, v in self.subprocess_kwargs.items() if k != 'creationflags'}
        )
        return proc

    def send_touch(self, device_id: str, x: int, y: int, action: str = 'tap',
                  duration: int = 0) -> bool:
        """
        通过 ADB 发送触摸事件到设备。
        
        参数:
            device_id: 设备 ID
            x, y: 坐标
            action: 'tap' | 'swipe' | 'long_press'
            duration: swipe 持续时间(ms)
        """
        try:
            if action == 'tap':
                cmd = [self.adb_path, '-s', device_id, 'shell', 'input', 'tap', str(x), str(y)]
            elif action == 'swipe':
                # 简单滑动：起点到同一点（模拟）
                cmd = [self.adb_path, '-s', device_id, 'shell', 'input', 'swipe',
                       str(x), str(y), str(x), str(y), str(duration or 200)]
            elif action == 'long_press':
                cmd = [self.adb_path, '-s', device_id, 'shell', 'input', 'swipe',
                       str(x), str(y), str(x), str(y), str(duration or 800)]
            else:
                raise ValueError(f"不支持的操作: {action}")

            result = subprocess.run(cmd, capture_output=True, timeout=5,
                                   **self.subprocess_kwargs)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"发送触摸事件失败: {str(e)}")
            return False

    def send_keyevent(self, device_id: str, keycode: int) -> bool:
        """
        发送按键事件到设备（Home/Back/Volume 等）。
        常用 keycode: 3=Home, 4=Back, 24=VolumeUp, 25=VolumeDown, 26=Power
        """
        try:
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'input', 'keyevent', str(keycode)],
                capture_output=True, timeout=5,
                **self.subprocess_kwargs
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"发送按键事件失败: {str(e)}")
            return False

    def get_screen_size(self, device_id: str) -> tuple:
        """获取设备屏幕尺寸 (width, height)"""
        try:
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'wm', 'size'],
                capture_output=True, text=True, timeout=5,
                **self.subprocess_kwargs
            )
            if result.returncode == 0:
                # 输出格式: Physical size: 1080x2340
                line = result.stdout.strip()
                if ':' in line:
                    size_str = line.split(':')[-1].strip()
                    w, h = size_str.split('x')
                    return int(w), int(h)
                # Override 格式: 1080x2340
                parts = line.split()
                for p in parts:
                    if 'x' in p:
                        w, h = p.split('x')
                        return int(w), int(h)
        except Exception:
            pass
        return 1080, 2340  # 默认值

    def check_adb_connection(self, device_id: str) -> bool:
        """检查设备 ADB 连接是否正常"""
        try:
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'echo', '1'],
                capture_output=True, text=True, timeout=5,
                **self.subprocess_kwargs
            )
            return result.returncode == 0 and '1' in result.stdout
        except Exception:
            return False
