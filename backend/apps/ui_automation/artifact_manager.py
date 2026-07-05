"""
测试产物管理器
负责统一管理测试执行过程中的所有产物：
- video: 录屏文件
- screenshots: 截图文件
- trace: 追踪文件
- har: 网络请求文件
- dom: 页面DOM文件
- logs: 日志文件
- console: 控制台日志文件
- report: 测试报告文件
"""
import os
import uuid
import time
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class ArtifactManager:
    """
    测试产物管理器
    按"run_时间戳_任务ID"组织产物目录结构
    """
    
    # 默认子目录名称
    SUBDIRS = [
        'screenshots',
        'video',
        'trace',
        'har',
        'dom',
        'logs',
        'console',
        'report',
    ]
    
    def __init__(self, base_dir: str = "artifacts"):
        """
        初始化产物管理器
        
        Args:
            base_dir: 产物根目录，默认为 artifacts
        """
        self.base_dir = base_dir
        self.run_id = ""
        self.run_dir = ""
        self.subdirs: Dict[str, str] = {}
        
    def create_run_directory(self, execution_id: Optional[str] = None) -> str:
        """
        创建本次运行的产物目录
        
        Args:
            execution_id: 执行ID，如果不提供则自动生成
            
        Returns:
            运行目录路径
        """
        # 生成执行ID
        if execution_id:
            self.run_id = execution_id
        else:
            timestamp = int(time.time())
            uuid_short = str(uuid.uuid4())[:8]
            self.run_id = f"{timestamp}_{uuid_short}"
        
        # 创建运行目录
        self.run_dir = os.path.join(self.base_dir, f"run_{self.run_id}")
        
        # 创建所有子目录
        for subdir in self.SUBDIRS:
            subdir_path = os.path.join(self.run_dir, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            self.subdirs[subdir] = subdir_path
            logger.debug(f"创建产物目录: {subdir_path}")
        
        logger.info(f"测试产物目录已创建: {self.run_dir}")
        return self.run_dir
    
    def get_run_dir(self) -> str:
        """获取当前运行目录"""
        if not self.run_dir:
            raise RuntimeError("请先调用 create_run_directory() 创建运行目录")
        return self.run_dir
    
    def get_run_id(self) -> str:
        """获取当前运行ID"""
        return self.run_id
    
    def get_subdir_path(self, subdir_name: str) -> str:
        """
        获取指定子目录路径
        
        Args:
            subdir_name: 子目录名称
            
        Returns:
            子目录路径
        """
        if subdir_name not in self.subdirs:
            raise ValueError(f"未知的子目录: {subdir_name}")
        return self.subdirs[subdir_name]
    
    def generate_filename(self, prefix: str, extension: str = "png") -> str:
        """
        生成唯一文件名
        
        Args:
            prefix: 文件名前缀
            extension: 文件扩展名
            
        Returns:
            完整的文件路径
        """
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}.{extension}"
        return filename
    
    def get_screenshot_path(self, prefix: str = "screenshot") -> str:
        """
        获取截图文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的截图文件路径
        """
        filename = self.generate_filename(prefix, "png")
        return os.path.join(self.subdirs['screenshots'], filename)
    
    def get_video_path(self, prefix: str = "video") -> str:
        """
        获取视频文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的视频文件路径
        """
        filename = self.generate_filename(prefix, "webm")
        return os.path.join(self.subdirs['video'], filename)
    
    def get_har_path(self, prefix: str = "network") -> str:
        """
        获取HAR文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的HAR文件路径
        """
        filename = self.generate_filename(prefix, "har")
        return os.path.join(self.subdirs['har'], filename)
    
    def get_trace_path(self, prefix: str = "trace") -> str:
        """
        获取trace文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的trace文件路径
        """
        filename = self.generate_filename(prefix, "zip")
        return os.path.join(self.subdirs['trace'], filename)
    
    def get_dom_path(self, prefix: str = "dom") -> str:
        """
        获取DOM文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的DOM文件路径
        """
        filename = self.generate_filename(prefix, "html")
        return os.path.join(self.subdirs['dom'], filename)
    
    def get_log_path(self, prefix: str = "test") -> str:
        """
        获取日志文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的日志文件路径
        """
        filename = self.generate_filename(prefix, "log")
        return os.path.join(self.subdirs['logs'], filename)
    
    def get_console_path(self, prefix: str = "console") -> str:
        """
        获取控制台日志文件路径
        
        Args:
            prefix: 文件前缀
            
        Returns:
            完整的控制台日志文件路径
        """
        filename = self.generate_filename(prefix, "log")
        return os.path.join(self.subdirs['console'], filename)
    
    def get_report_path(self, prefix: str = "report", extension: str = "html") -> str:
        """
        获取报告文件路径
        
        Args:
            prefix: 文件前缀
            extension: 文件扩展名
            
        Returns:
            完整的报告文件路径
        """
        filename = self.generate_filename(prefix, extension)
        return os.path.join(self.subdirs['report'], filename)
    
    def save_file(self, content: bytes, subdir: str, filename: str) -> str:
        """
        保存二进制文件到指定子目录
        
        Args:
            content: 文件内容（二进制）
            subdir: 子目录名称
            filename: 文件名
            
        Returns:
            完整的文件路径
        """
        if subdir not in self.subdirs:
            raise ValueError(f"未知的子目录: {subdir}")
        
        file_path = os.path.join(self.subdirs[subdir], filename)
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.debug(f"文件已保存: {file_path}")
        return file_path
    
    def save_text_file(self, content: str, subdir: str, filename: str, encoding: str = "utf-8") -> str:
        """
        保存文本文件到指定子目录
        
        Args:
            content: 文件内容（文本）
            subdir: 子目录名称
            filename: 文件名
            encoding: 编码格式
            
        Returns:
            完整的文件路径
        """
        if subdir not in self.subdirs:
            raise ValueError(f"未知的子目录: {subdir}")
        
        file_path = os.path.join(self.subdirs[subdir], filename)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        logger.debug(f"文本文件已保存: {file_path}")
        return file_path
    
    def save_json_file(self, data: Dict, subdir: str, filename: str) -> str:
        """
        保存JSON文件到指定子目录
        
        Args:
            data: JSON数据
            subdir: 子目录名称
            filename: 文件名
            
        Returns:
            完整的文件路径
        """
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return self.save_text_file(content, subdir, filename)
    
    def get_artifact_info(self) -> Dict[str, Any]:
        """
        获取产物目录信息
        
        Returns:
            产物目录信息字典
        """
        return {
            'run_id': self.run_id,
            'run_dir': self.run_dir,
            'subdirs': self.subdirs,
            'created_at': datetime.now().isoformat(),
        }
    
    def list_artifacts(self) -> Dict[str, List[str]]:
        """
        列出所有产物文件
        
        Returns:
            各子目录下的文件列表
        """
        artifacts = {}
        
        for subdir_name, subdir_path in self.subdirs.items():
            if os.path.exists(subdir_path):
                files = [f for f in os.listdir(subdir_path) if os.path.isfile(os.path.join(subdir_path, f))]
                artifacts[subdir_name] = files
        
        return artifacts
    
    def cleanup_old_runs(self, days_to_keep: int = 7) -> int:
        """
        清理旧的运行目录
        
        Args:
            days_to_keep: 保留天数，超过此天数的目录将被删除
            
        Returns:
            删除的目录数量
        """
        import shutil
        
        deleted_count = 0
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        if not os.path.exists(self.base_dir):
            return 0
        
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            
            if not os.path.isdir(item_path):
                continue
            
            # 检查是否是运行目录（以 run_ 开头）
            if not item.startswith("run_"):
                continue
            
            try:
                # 获取目录创建时间
                mtime = os.path.getmtime(item_path)
                
                if mtime < cutoff_time:
                    shutil.rmtree(item_path)
                    deleted_count += 1
                    logger.info(f"清理旧运行目录: {item_path}")
            except Exception as e:
                logger.warning(f"清理目录失败 {item_path}: {e}")
        
        return deleted_count
    
    def create_case_directory(self, case_name: str) -> str:
        """
        为单个测试用例创建子目录
        
        Args:
            case_name: 测试用例名称
            
        Returns:
            用例目录路径
        """
        # 清理用例名称中的非法字符
        safe_case_name = self._sanitize_filename(case_name)
        case_dir = os.path.join(self.run_dir, safe_case_name)
        os.makedirs(case_dir, exist_ok=True)
        
        # 在case目录下创建子目录
        for subdir in self.SUBDIRS:
            subdir_path = os.path.join(case_dir, subdir)
            os.makedirs(subdir_path, exist_ok=True)
        
        logger.debug(f"创建用例目录: {case_dir}")
        return case_dir
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全的文件名
        """
        import re
        # 移除或替换非法字符
        return re.sub(r'[\\/*?:"<>|]', '_', filename)
    
    def __repr__(self):
        return f"ArtifactManager(run_id={self.run_id}, run_dir={self.run_dir})"


# 全局实例
_artifact_manager = None


def get_artifact_manager(base_dir: str = "artifacts") -> ArtifactManager:
    """
    获取全局产物管理器实例
    
    Args:
        base_dir: 产物根目录
        
    Returns:
        ArtifactManager实例
    """
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactManager(base_dir)
    return _artifact_manager


def create_new_run(execution_id: Optional[str] = None) -> ArtifactManager:
    """
    创建新的运行实例
    
    Args:
        execution_id: 执行ID
        
    Returns:
        配置好的ArtifactManager实例
    """
    global _artifact_manager
    _artifact_manager = ArtifactManager()
    _artifact_manager.create_run_directory(execution_id)
    return _artifact_manager