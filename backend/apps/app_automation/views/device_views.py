# -*- coding: utf-8 -*-
"""APP设备管理视图"""
import os
import re
import platform
import subprocess
import base64
from io import BytesIO
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import logging

from .test_case_views import AppPagination
from ..models import AppDevice
from ..serializers import AppDeviceSerializer
from ..managers.device_manager import DeviceManager

logger = logging.getLogger(__name__)


def get_adb_path() -> str:
    """
    获取 ADB 路径：优先使用数据库配置，否则使用默认值 'adb'
    """
    try:
        from ..models import AppTestConfig
        config = AppTestConfig.objects.first()
        return config.adb_path if config else 'adb'
    except Exception as e:
        logger.warning(f"获取 ADB 配置失败，使用默认路径: {e}")
        return 'adb'


class AppDeviceViewSet(viewsets.ModelViewSet):
    """APP设备管理 ViewSet"""
    queryset = AppDevice.objects.all()
    serializer_class = AppDeviceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'connection_type']
    search_fields = ['device_id', 'name']
    
    @action(detail=False, methods=['get'])
    def discover(self, request):
        """发现ADB设备（真机 USB/远程连接）"""
        try:
            adb_path = get_adb_path()
            logger.info(f"使用 ADB 路径: {adb_path}")
            
            manager = DeviceManager(adb_path=adb_path)
            devices_info = manager.list_devices()
            
            # 更新或创建设备记录
            db_devices = []
            for device_info in devices_info:
                device_id = device_info.get('device_id', '')
                if not device_id:
                    continue
                if ':' in device_id:
                    # 远程设备（IP:端口格式）
                    connection_type = 'remote_emulator'
                    ip_address = device_info.get('ip_address') or ''
                elif device_id.startswith('emulator-'):
                    # 本地模拟器
                    connection_type = 'emulator'
                    ip_address = '127.0.0.1'
                else:
                    # USB 连接的真机
                    connection_type = 'real_device'
                    ip_address = device_info.get('ip_address') or ''
                
                device, created = AppDevice.objects.update_or_create(
                    device_id=device_info['device_id'],
                    defaults={
                        'name': device_info.get('name') or '',
                        'status': device_info.get('status') or 'offline',
                        'android_version': device_info.get('android_version') or '',
                        'ip_address': ip_address,
                        'port': device_info.get('port') or 5555,
                        'connection_type': connection_type,
                    }
                )
                db_devices.append(device)
            
            if not db_devices:
                return Response({
                    'success': True,
                    'message': '未发现任何设备。请确保手机已通过 USB 连接并开启 USB 调试，或通过 IP 地址远程连接。',
                    'devices': [],
                    'hint': '请检查：1) 手机已连接USB 2) 已开启开发者选项和USB调试 3) 已授权此电脑的调试请求'
                })
            
            return Response({
                'success': True,
                'message': f'发现 {len(db_devices)} 个设备',
                'devices': AppDeviceSerializer(db_devices, many=True).data
            })
        except Exception as e:
            logger.error(f"发现设备失败: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'发现设备失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """锁定设备"""
        device = self.get_object()
        
        if device.status == 'locked':
            return Response({
                'success': False,
                'message': '设备已被锁定'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        device.lock(request.user)
        
        return Response({
            'success': True,
            'message': '设备锁定成功',
            'device': AppDeviceSerializer(device).data
        })
    
    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """释放设备"""
        device = self.get_object()
        
        if device.locked_by and device.locked_by != request.user:
            return Response({
                'success': False,
                'message': '无权释放他人锁定的设备'
            }, status=status.HTTP_403_FORBIDDEN)
        
        device.unlock()
        
        return Response({
            'success': True,
            'message': '设备释放成功',
            'device': AppDeviceSerializer(device).data
        })
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """断开远程设备连接"""
        device = self.get_object()
        
        # 只有远程设备可以断开
        if device.connection_type not in ['remote', 'remote_emulator']:
            return Response({
                'success': False,
                'message': '只能断开远程设备的连接'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            adb_path = get_adb_path()
            manager = DeviceManager(adb_path=adb_path)
            success = manager.disconnect_device(f'{device.ip_address}:{device.port}')
            
            if not success:
                return Response({
                    'success': False,
                    'message': '断开设备失败'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 更新设备状态为离线
            device.status = 'offline'
            device.save()
            
            return Response({
                'success': True,
                'message': f'设备 {device.name or device.device_id} 已断开连接',
                'device': AppDeviceSerializer(device).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'断开设备失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def connect(self, request):
        """连接远程设备"""
        try:
            ip_address = request.data.get('ip_address')
            port = request.data.get('port', 5555)
            
            if not ip_address:
                return Response({
                    'success': False,
                    'message': '请提供设备IP地址'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            adb_path = get_adb_path()
            manager = DeviceManager(adb_path=adb_path)
            device_info = manager.connect_device(ip_address, port)
            
            # 创建或更新设备记录
            device, created = AppDevice.objects.update_or_create(
                device_id=device_info['device_id'],
                defaults={
                    'name': device_info.get('name') or '',
                    'status': 'online',
                    'android_version': device_info.get('android_version', ''),
                    'ip_address': ip_address,
                    'port': port,
                    'connection_type': 'remote_emulator',
                }
            )
            
            return Response({
                'success': True,
                'message': '设备连接成功',
                'device': AppDeviceSerializer(device).data
            })
        except Exception as e:
            logger.error(f"连接设备失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'连接设备失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='screenshot')
    def screenshot(self, request, pk=None):
        """
        获取设备实时截图
        
        功能：
        1. 使用 adb screencap 获取设备截图
        2. 转换为 Base64
        3. 返回 data URL 格式
        """
        device = self.get_object()
        
        if device.status == 'offline':
            return Response({
                'code': 400,
                'msg': '设备离线，无法截图',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            adb_path = get_adb_path()
            
            # 使用 adb screencap 命令截图
            result = subprocess.run(
                [adb_path, '-s', device.device_id, 'exec-out', 'screencap', '-p'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10
            )
            
            if not result.stdout:
                return Response({
                    'code': 500,
                    'msg': '截图失败：无返回数据',
                    'success': False
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 转换为 Base64
            image_base64 = base64.b64encode(result.stdout).decode('utf-8')
            
            logger.info(f"设备 {device.device_id} 截图成功")
            
            return Response({
                'code': 0,
                'msg': '截图成功',
                'success': True,
                'data': {
                    'filename': f"device_{device.id}_{int(timezone.now().timestamp())}.png",
                    'content': f"data:image/png;base64,{image_base64}",
                    'device_id': device.device_id,
                    'timestamp': int(timezone.now().timestamp())
                }
            })
            
        except subprocess.TimeoutExpired:
            logger.error(f"设备 {device.device_id} 截图超时")
            return Response({
                'code': 500,
                'msg': '截图超时，请检查设备连接',
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"设备 {device.device_id} 截图失败: {str(e)}")
            return Response({
                'code': 500,
                'msg': f'截图失败: {str(e)}',
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ──────── 录屏（真机使用 scrcpy 录制 MP4）────────

    @action(detail=True, methods=['post'], url_path='screen_record/start')
    def start_screen_record(self, request, pk=None):
        """
        启动设备录屏（通过 scrcpy 录制到本地 MP4 文件）
        """
        device = self.get_object()

        if device.device_id.startswith('virtual-'):
            return Response({
                'success': False,
                'message': '虚拟设备不支持录屏，请使用真实设备'
            }, status=status.HTTP_400_BAD_REQUEST)

        if device.status == 'offline':
            return Response({
                'success': False,
                'message': '设备离线，无法录屏'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            import time, os
            manager = DeviceManager()
            timestamp = int(time.time())
            filename = f"screen_record_{device.id}_{timestamp}.mp4"
            output_dir = os.path.join('media', 'screen_records')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)

            if manager.scrcpy_path and os.path.isfile(manager.scrcpy_path):
                # 使用 scrcpy 录制（高质量 MP4）
                proc = manager.scrcpy_record(
                    device.device_id, output_path,
                    max_size=1024, bit_rate=8000000
                )
                device._screen_record_proc = proc
                return Response({
                    'success': True,
                    'message': '录屏已启动（scrcpy）',
                    'data': {'mode': 'scrcpy', 'filename': filename, 'output': output_path}
                })
            else:
                # 回退到 ADB screenrecord
                import threading
                def do_record():
                    try:
                        proc = subprocess.Popen(
                            [manager.adb_path, '-s', device.device_id,
                             'shell', 'screenrecord', '/sdcard/screenrecord.mp4'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            **(manager.subprocess_kwargs if hasattr(manager, 'subprocess_kwargs') else {})
                        )
                        device._screen_record_proc = proc
                        proc.wait()
                    except Exception as ex:
                        logger.error(f"ADB 录屏失败: {ex}")

                thread = threading.Thread(target=do_record, daemon=True)
                thread.start()
                return Response({
                    'success': True,
                    'message': '录屏已启动（ADB screenrecord）',
                    'data': {'mode': 'adb', 'filename': filename}
                })
        except Exception as e:
            logger.error(f"启动录屏失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'启动录屏失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='screen_record/stop')
    def stop_screen_record(self, request, pk=None):
        """
        停止设备录屏并返回 MP4 文件路径
        """
        device = self.get_object()

        if device.device_id.startswith('virtual-'):
            return Response({
                'success': False,
                'message': '虚拟设备不支持录屏'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 首先终止录制进程
            if hasattr(device, '_screen_record_proc') and device._screen_record_proc:
                try:
                    device._screen_record_proc.terminate()
                except Exception:
                    pass
                device._screen_record_proc = None

            import os, glob, time
            # 等待文件写入完成
            time.sleep(1)

            adb_path = get_adb_path()
            # 如果是 ADB screenrecord 模式，需要 pull 文件
            record_dir = os.path.join('media', 'screen_records')
            pattern = os.path.join(record_dir, f"screen_record_{device.id}_*.mp4")
            files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

            if not files:
                # 尝试从设备 pull
                output_path = f"media/screen_records/stopped_{device.id}_{int(time.time())}.mp4"
                subprocess.run(
                    [adb_path, '-s', device.device_id, 'pull',
                     '/sdcard/screenrecord.mp4', output_path],
                    check=False, timeout=30
                )
                if os.path.exists(output_path):
                    files = [output_path]

            if files:
                return Response({
                    'success': True,
                    'message': '录屏已停止',
                    'data': {
                        'mode': 'mp4',
                        'path': f'/media/screen_records/{os.path.basename(files[0])}',
                        'filename': os.path.basename(files[0]),
                        'size': os.path.getsize(files[0]),
                    }
                })
            else:
                return Response({
                    'success': False,
                    'message': '未找到录制文件'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"停止录屏失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'停止录屏失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='screen_records')
    def screen_records(self, request, pk=None):
        """获取设备录屏列表（MP4 文件）"""
        device = self.get_object()
        import os, glob
        record_dir = os.path.join('media', 'screen_records')
        os.makedirs(record_dir, exist_ok=True)
        pattern = os.path.join(record_dir, f"*_{device.id}_*.mp4")
        stopped_pattern = os.path.join(record_dir, f"stopped_{device.id}_*.mp4")
        files = sorted(
            set(glob.glob(pattern) + glob.glob(stopped_pattern)),
            key=lambda f: os.path.getmtime(f), reverse=True
        )
        records = []
        for f in files[:20]:
            records.append({
                'filename': os.path.basename(f),
                'path': f'/media/screen_records/{os.path.basename(f)}',
                'size': os.path.getsize(f),
                'created_at': os.path.getmtime(f),
                'type': 'mp4',
            })
        return Response({
            'success': True,
            'data': records
        })

    @action(detail=True, methods=['post', 'delete'], url_path='screen_record/delete')
    def delete_screen_record(self, request, pk=None):
        """
        删除指定录屏文件。
        POST/DELETE 参数: filename (录屏文件名)
        """
        device = self.get_object()
        import os

        filename = request.data.get('filename', '') or request.query_params.get('filename', '')
        if not filename:
            return Response({
                'success': False,
                'message': '请提供要删除的录屏文件名(filename)'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 安全检查：路径穿越防护
        if '..' in filename or '/' in filename or '\\' in filename:
            return Response({
                'success': False,
                'message': '无效的文件名'
            }, status=status.HTTP_400_BAD_REQUEST)

        record_dir = os.path.join('media', 'screen_records')
        filepath = os.path.join(record_dir, filename)

        if not os.path.isfile(filepath):
            return Response({
                'success': False,
                'message': f'文件不存在: {filename}'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            os.remove(filepath)
            logger.info(f"录屏文件已删除: {filepath}")
            return Response({
                'success': True,
                'message': f'已删除录屏文件: {filename}'
            })
        except Exception as e:
            logger.error(f"删除录屏文件失败: {e}")
            return Response({
                'success': False,
                'message': f'删除失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='live-screenshot')
    def live_screenshot(self, request, pk=None):
        """
        获取设备实时截图（用于真机投屏/实时预览）- 性能优化版

        优化：
        - 屏幕尺寸首次获取后缓存在设备对象上，减少 ADB 调用（3→1）
        - 支持 JPEG 压缩（quality 参数，默认 70），大幅减少数据传输量
        - 支持 max_size 缩放（默认 720px），减少解码开销

        查询参数:
            quality: JPEG 质量 (0-100)，默认 70，为 0 时返回原始 PNG
            max_size: 最大边长 px，默认 720
            format: 'png' | 'jpeg'，默认 'jpeg'
        """
        device = self.get_object()

        if device.device_id.startswith('virtual-'):
            return Response({
                'success': False,
                'message': '虚拟设备不支持实时截图，请连接真实手机。'
            }, status=status.HTTP_400_BAD_REQUEST)

        if device.status == 'offline':
            return Response({
                'success': False,
                'message': '设备离线，无法截图。请检查 USB 连接或 ADB 状态。'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            adb_path = get_adb_path()
            quality = int(request.query_params.get('quality', 70))
            max_size = int(request.query_params.get('max_size', 720))
            fmt = request.query_params.get('format', 'jpeg')

            # ADB 获取真实手机截图（仅 1 次 ADB 调用）
            result = subprocess.run(
                [adb_path, '-s', device.device_id, 'exec-out', 'screencap', '-p'],
                capture_output=True, timeout=10,
                **({} if platform.system() != 'Windows' else {'creationflags': subprocess.CREATE_NO_WINDOW})
            )
            if result.returncode != 0 or not result.stdout:
                return Response({
                    'success': False,
                    'message': 'ADB 截图失败，请检查设备连接'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            image_bytes = result.stdout

            # 屏幕尺寸：缓存到 device 对象上避免每次 wm size
            width, height = 1080, 2340  # 默认值
            if not hasattr(device, '_cached_screen_size'):
                try:
                    size_result = subprocess.run(
                        [adb_path, '-s', device.device_id, 'shell', 'wm', 'size'],
                        capture_output=True, timeout=5,
                        **({} if platform.system() != 'Windows' else {'creationflags': subprocess.CREATE_NO_WINDOW})
                    )
                    size_line = size_result.stdout.decode('utf-8', errors='ignore').strip()
                    # Parse "Physical size: 1080x2340" or "Override size: 1080x2400"
                    import re
                    match = re.search(r'(\d+)\s*x\s*(\d+)', size_line)
                    if match:
                        width, height = int(match.group(1)), int(match.group(2))
                    device._cached_screen_size = (width, height)
                except Exception:
                    pass
            else:
                width, height = device._cached_screen_size

            # 图片压缩/缩放（可选）
            content_type = 'image/png'
            if quality > 0 and fmt != 'png':
                try:
                    from PIL import Image

                    img = Image.open(BytesIO(image_bytes))

                    # 缩放到目标大小
                    scale = min(max_size / max(width, height), 1.0)
                    if scale < 1.0:
                        new_w, new_h = int(width * scale), int(height * scale)
                        img = img.resize((new_w, new_h), Image.LANCZOS)
                        width, height = new_w, new_h

                    # RGBA → RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background

                    # JPEG 压缩
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=min(quality, 95), optimize=True)
                    image_bytes = output.getvalue()
                    content_type = 'image/jpeg'
                except ImportError:
                    pass
                except Exception as comp_err:
                    logger.debug(f"图片压缩跳过: {comp_err}")

            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            return Response({
                'success': True,
                'data': {
                    'image': f"data:{content_type};base64,{image_b64}",
                    'mode': 'live',
                    'device_id': device.device_id,
                    'width': width,
                    'height': height,
                    'size_kb': round(len(image_bytes) / 1024, 1),
                }
            })

        except subprocess.TimeoutExpired:
            return Response({
                'success': False,
                'message': '截图超时，请检查设备性能或重新连接'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"实时截图失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'截图失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='touch')
    def touch(self, request, pk=None):
        """
        向真实设备发送触摸事件（ADB input tap/swipe）
        POST 参数:
            x, y: 坐标
            action: 'tap' | 'swipe' | 'long_press' (默认 'tap')
            duration: 持续时间(ms)
        """
        device = self.get_object()

        if device.device_id.startswith('virtual-'):
            return Response({
                'success': False,
                'message': '虚拟设备不支持触摸操作，请连接真实手机'
            }, status=status.HTTP_400_BAD_REQUEST)

        if device.status == 'offline':
            return Response({
                'success': False,
                'message': '设备离线，无法操作'
            }, status=status.HTTP_400_BAD_REQUEST)

        x = request.data.get('x')
        y = request.data.get('y')
        action = request.data.get('action', 'tap')
        duration = request.data.get('duration', 0)

        if x is None or y is None:
            return Response({
                'success': False,
                'message': '请提供 x, y 坐标'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            adb_path = get_adb_path()
            manager = DeviceManager(adb_path=adb_path)
            ok = manager.send_touch(device.device_id, int(x), int(y), action, int(duration))
            return Response({
                'success': ok,
                'message': '操作成功' if ok else '操作失败'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='keyevent')
    def keyevent(self, request, pk=None):
        """
        向真实设备发送按键事件
        POST 参数:
            keycode: 按键码 (3=Home, 4=Back, 26=Power, 24=VolUp, 25=VolDown, 187=Recent)
        """
        device = self.get_object()

        if device.device_id.startswith('virtual-'):
            return Response({
                'success': False,
                'message': '虚拟设备不支持按键操作，请连接真实手机'
            }, status=status.HTTP_400_BAD_REQUEST)

        if device.status == 'offline':
            return Response({
                'success': False,
                'message': '设备离线'
            }, status=status.HTTP_400_BAD_REQUEST)

        keycode = request.data.get('keycode')
        if keycode is None:
            return Response({
                'success': False,
                'message': '请提供 keycode'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            adb_path = get_adb_path()
            manager = DeviceManager(adb_path=adb_path)
            ok = manager.send_keyevent(device.device_id, int(keycode))
            return Response({
                'success': ok,
                'message': f'按键 {keycode} {"成功" if ok else "失败"}'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='device-info')
    def device_info_detail(self, request, pk=None):
        """
        获取设备详细信息（含屏幕尺寸、ADB 状态、工具可用性）
        """
        device = self.get_object()
        data = AppDeviceSerializer(device).data

        if device.status != 'offline' and not device.device_id.startswith('virtual-'):
            try:
                adb_path = get_adb_path()
                manager = DeviceManager(adb_path=adb_path)
                width, height = manager.get_screen_size(device.device_id)
                data['screen_size'] = f'{width}x{height}'
                data['adb_connected'] = manager.check_adb_connection(device.device_id)
            except Exception:
                data['screen_size'] = '未知'
                data['adb_connected'] = False
        else:
            data['screen_size'] = '未知'
            data['adb_connected'] = False

        # 工具可用性（自动发现工具路径）
        dm = DeviceManager()
        data['tools'] = {
            'adb_path': dm.adb_path,
            'scrcpy_available': bool(dm.scrcpy_path and os.path.isfile(dm.scrcpy_path)),
        }

        return Response({
            'success': True,
            'data': data
        })
