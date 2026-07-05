import logging
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .services.screen_optimizer import ScreenPushManager

logger = logging.getLogger(__name__)


class AppExecutionConsumer(AsyncJsonWebsocketConsumer):
    """APP执行WebSocket消费者 - 支持优化的屏幕推流"""

    async def connect(self):
        try:
            self.execution_id = self.scope["url_route"]["kwargs"]["execution_id"]
            self.group_name = f"app_execution_{self.execution_id}"

            # 初始化屏幕推流管理器
            self.push_manager = ScreenPushManager(
                compress_quality=75,
                max_frame_size_kb=100,
                max_fps=30,
                enable_delta=True
            )

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket 连接成功: execution_id={self.execution_id}")
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'group_name'):
                # 记录推流统计信息
                if hasattr(self, 'push_manager'):
                    stats = self.push_manager.get_statistics()
                    logger.info(f"推流统计: {stats}")

                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(f"WebSocket 断开: execution_id={self.execution_id}, code={close_code}")
        except Exception as e:
            logger.error(f"WebSocket 断开处理失败: {e}")

    async def execution_update(self, event):
        """处理执行更新消息"""
        try:
            # 如果是屏幕帧数据，进行优化处理
            if event.get('type') == 'screen_frame' and 'frame_data' in event:
                frame_data = event['frame_data']
                if isinstance(frame_data, str):
                    # 如果是base64字符串，转换为字节
                    import base64
                    frame_data = base64.b64decode(frame_data)

                # 使用优化管理器处理帧
                result = await self.push_manager.process_frame(frame_data)

                if result:
                    # 发送优化后的帧
                    optimized_event = {
                        'type': 'screen_frame',
                        'frame_data': result['compressed'],
                        'changed': result['changed'],
                        'compression_ratio': result['stats'].get('compression_ratio', 1),
                    }
                    await self.send_json(optimized_event)
                # 如果帧被跳过（增量传输），不发送
            else:
                # 其他消息类型直接转发
                await self.send_json(event)
        except Exception as e:
            logger.error(f"WebSocket 推送消息失败: {e}")
