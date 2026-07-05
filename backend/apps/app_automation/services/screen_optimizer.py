# -*- coding: utf-8 -*-
"""
APP屏幕推流优化模块
- 图片压缩
- 增量传输
- 流控限制
- 多线程处理
"""
import io
import time
import logging
import asyncio
from typing import Optional, Tuple
from PIL import Image
import hashlib

logger = logging.getLogger(__name__)


class ScreenFrameCompressor:
    """屏幕帧压缩器 - 优化WebSocket传输"""

    # 图片质量等级（1-95）
    QUALITY_HIGH = 85
    QUALITY_MEDIUM = 75
    QUALITY_LOW = 65

    # 最大屏幕宽度/高度
    MAX_WIDTH = 1920
    MAX_HEIGHT = 1080

    def __init__(self, quality: int = QUALITY_MEDIUM, enable_delta: bool = True):
        """
        初始化压缩器

        Args:
            quality: 图片压缩质量（1-95）
            enable_delta: 是否启用增量传输
        """
        self.quality = max(1, min(95, quality))
        self.enable_delta = enable_delta
        self.prev_frame_hash = None
        self.prev_frame_data = None

    def compress_image(self, image_data: bytes, max_size_kb: int = 100) -> Tuple[bytes, dict]:
        """
        压缩图片 - 自动降低质量直到达到目标大小

        Args:
            image_data: 原始图片数据
            max_size_kb: 目标最大文件大小（KB）

        Returns:
            (压缩后的图片数据, 压缩统计信息)
        """
        try:
            img = Image.open(io.BytesIO(image_data))
            original_size = len(image_data)

            # 如果图片过大，进行缩小
            if img.width > self.MAX_WIDTH or img.height > self.MAX_HEIGHT:
                ratio = min(self.MAX_WIDTH / img.width, self.MAX_HEIGHT / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 逐步降低质量直到达到目标大小
            quality = self.quality
            while quality > 10:
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                compressed_data = output.getvalue()
                compressed_size_kb = len(compressed_data) / 1024

                if compressed_size_kb <= max_size_kb:
                    break
                quality -= 5

            compressed_size = len(compressed_data)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1

            stats = {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': round(compression_ratio, 2),
                'original_dimension': f"{img.width}x{img.height}",
                'quality_level': quality,
            }

            logger.debug(f"图片压缩: {original_size}B -> {compressed_size}B (压缩率: {compression_ratio:.2f}x)")
            return compressed_data, stats

        except Exception as e:
            logger.error(f"图片压缩失败: {str(e)}")
            return image_data, {'error': str(e), 'original_size': len(image_data)}

    def calculate_frame_hash(self, image_data: bytes) -> str:
        """计算帧哈希用于增量检测"""
        return hashlib.md5(image_data).hexdigest()

    def is_frame_changed(self, image_data: bytes, threshold: float = 0.1) -> bool:
        """
        检测帧是否改变（用于增量传输）

        Args:
            image_data: 新帧数据
            threshold: 变化阈值

        Returns:
            是否改变
        """
        if not self.enable_delta:
            return True

        current_hash = self.calculate_frame_hash(image_data)

        if self.prev_frame_hash is None:
            self.prev_frame_hash = current_hash
            self.prev_frame_data = image_data
            return True

        changed = current_hash != self.prev_frame_hash
        self.prev_frame_hash = current_hash
        self.prev_frame_data = image_data

        return changed


class WebSocketRateLimiter:
    """WebSocket消息流控器 - 防止过载"""

    def __init__(self, max_messages_per_second: int = 30):
        """
        初始化限流器

        Args:
            max_messages_per_second: 每秒最多消息数
        """
        self.max_messages_per_second = max_messages_per_second
        self.min_interval = 1.0 / max_messages_per_second
        self.last_send_time = 0

    async def wait_if_needed(self) -> float:
        """
        如果需要，等待以遵守流控限制

        Returns:
            实际等待时间（秒）
        """
        current_time = time.time()
        time_since_last_send = current_time - self.last_send_time

        if time_since_last_send < self.min_interval:
            wait_time = self.min_interval - time_since_last_send
            await asyncio.sleep(wait_time)
            self.last_send_time = time.time()
            return wait_time

        self.last_send_time = current_time
        return 0


class ScreenPushManager:
    """屏幕推流管理器 - 综合管理压缩、限流、增量传输"""

    def __init__(
        self,
        compress_quality: int = ScreenFrameCompressor.QUALITY_MEDIUM,
        max_frame_size_kb: int = 100,
        max_fps: int = 30,
        enable_delta: bool = True
    ):
        """
        初始化推流管理器

        Args:
            compress_quality: 图片压缩质量
            max_frame_size_kb: 最大帧大小（KB）
            max_fps: 最大帧率
            enable_delta: 是否启用增量传输
        """
        self.compressor = ScreenFrameCompressor(compress_quality, enable_delta)
        self.rate_limiter = WebSocketRateLimiter(max_fps)
        self.max_frame_size_kb = max_frame_size_kb
        self.stats = {
            'total_frames': 0,
            'skipped_frames': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'total_wait_time': 0,
        }

    async def process_frame(self, frame_data: bytes) -> Optional[dict]:
        """
        处理一帧屏幕数据

        Args:
            frame_data: 原始帧数据

        Returns:
            {
                'compressed': 压缩后的图片数据（base64）,
                'changed': 是否改变,
                'stats': 统计信息,
                'wait_time': 等待时间
            }
            如果跳过则返回None
        """
        try:
            # 检测帧是否改变
            if not self.compressor.is_frame_changed(frame_data):
                self.stats['skipped_frames'] += 1
                return None

            # 压缩图片
            compressed_data, compress_stats = self.compressor.compress_image(
                frame_data,
                self.max_frame_size_kb
            )

            # 应用流控
            wait_time = await self.rate_limiter.wait_if_needed()

            # 更新统计
            self.stats['total_frames'] += 1
            self.stats['total_original_size'] += len(frame_data)
            self.stats['total_compressed_size'] += len(compressed_data)
            self.stats['total_wait_time'] += wait_time

            # 返回处理结果
            import base64
            return {
                'compressed': base64.b64encode(compressed_data).decode('utf-8'),
                'changed': True,
                'stats': compress_stats,
                'wait_time': wait_time,
            }

        except Exception as e:
            logger.error(f"处理帧失败: {str(e)}")
            return None

    def get_statistics(self) -> dict:
        """获取推流统计信息"""
        total_size = self.stats['total_original_size']
        compressed_size = self.stats['total_compressed_size']

        return {
            **self.stats,
            'total_frames_sent': self.stats['total_frames'],
            'skip_rate': f"{self.stats['skipped_frames'] / max(1, self.stats['total_frames'] + self.stats['skipped_frames']) * 100:.1f}%",
            'compression_ratio': f"{total_size / max(1, compressed_size):.2f}x" if compressed_size > 0 else "N/A",
            'average_wait_time_ms': f"{self.stats['total_wait_time'] / max(1, self.stats['total_frames']) * 1000:.1f}",
        }
