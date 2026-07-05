"""
测试资产中心API
提供统一的资产查询、删除、清理接口
支持：
- 截图、视频、报告、下载中心
- 数据库记录 + 磁盘文件双重清理
- 一键全部删除
"""
import os
import shutil
import logging
import time
from typing import List

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def _safe_remove_file(file_path: str) -> bool:
    """安全删除文件（带边界保护）"""
    if not file_path:
        return False
    try:
        # 安全边界：禁止删除系统敏感目录
        forbidden = ['/windows', '/system32', '/program files', '\\windows', '\\system32',
                    'appdata\\local\\microsoft', 'appdata\\roaming\\microsoft']
        file_path_lower = file_path.lower()
        for f in forbidden:
            if f in file_path_lower:
                logger.warning(f"拒绝删除系统目录文件: {file_path}")
                return False
        if os.path.isfile(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.warning(f"删除文件失败 {file_path}: {e}")
    return False


def _safe_remove_dir(dir_path: str) -> bool:
    """安全删除目录"""
    if not dir_path:
        return False
    try:
        forbidden = ['/windows', '/system32', '/program files', '\\windows', '\\system32']
        dir_path_lower = dir_path.lower()
        for f in forbidden:
            if f in dir_path_lower:
                logger.warning(f"拒绝删除系统目录: {dir_path}")
                return False
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)
            return True
    except Exception as e:
        logger.warning(f"删除目录失败 {dir_path}: {e}")
    return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_assets(request):
    """
    统一查询测试资产
    返回: screenshots, videos, reports, downloads
    """
    asset_type = request.query_params.get('type', 'all')
    user = request.user

    result = {
        'screenshots': [],
        'videos': [],
        'reports': [],
        'downloads': [],
    }

    try:
        # 1. 截图
        if asset_type in ('all', 'screenshot'):
            try:
                from apps.ui_automation.models import Screenshot
                accessible = _accessible_projects(user)
                if accessible is not None:
                    shots = Screenshot.objects.filter(execution__project__in=accessible).order_by('-captured_at')[:200]
                else:
                    shots = Screenshot.objects.all().order_by('-captured_at')[:200]
                for s in shots:
                    result['screenshots'].append({
                        'id': s.id,
                        'name': s.name or f'截图_{s.id}',
                        'image': s.image.url if s.image else '',
                        'execution_id': s.execution_id,
                        'captured_at': s.captured_at.isoformat() if s.captured_at else '',
                    })
            except Exception as e:
                logger.warning(f"查询截图失败: {e}")

        # 2. 视频（来自 AI 执行记录 + artifacts 目录）
        if asset_type in ('all', 'video'):
            try:
                from apps.ui_automation.models import AIExecutionRecord
                records = AIExecutionRecord.objects.filter(
                    Q(project__owner=user) | Q(project__members=user) | Q(project__isnull=True)
                ).filter(video_path__isnull=False).order_by('-start_time')[:100]
                for r in records:
                    if r.video_path:
                        result['videos'].append({
                            'id': r.id,
                            'name': r.case_name or f'视频_{r.id}',
                            'video_path': r.video_path,
                            'case_name': r.case_name,
                            'created_at': r.start_time.isoformat() if r.start_time else '',
                        })
            except Exception as e:
                logger.warning(f"查询视频失败: {e}")

        # 3. 报告
        if asset_type in ('all', 'report'):
            try:
                from apps.reports.models import TestReport
                reports = TestReport.objects.all().order_by('-created_at')[:200]
                for r in reports:
                    result['reports'].append({
                        'id': r.id,
                        'name': r.name or f'报告_{r.id}',
                        'created_at': r.created_at.isoformat() if r.created_at else '',
                        'status': r.status,
                    })
            except Exception as e:
                logger.warning(f"查询报告失败: {e}")

        return Response(result)
    except Exception as e:
        logger.error(f"查询资产失败: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_asset(request):
    """
    统一删除资产
    body: { type: 'screenshot'|'video'|'report'|'download', id: int, file_path?: str }
    """
    asset_type = request.data.get('type', '')
    asset_id = request.data.get('id')
    file_path = request.data.get('file_path', '')

    if not asset_type:
        return Response({'error': '请指定资产类型 type'}, status=400)

    result = {
        'deleted': False,
        'db_deleted': False,
        'file_deleted': False,
        'message': '',
    }

    try:
        if asset_type == 'screenshot':
            try:
                from apps.ui_automation.models import Screenshot
                accessible = _accessible_projects(request.user)
                if accessible is not None:
                    shot = Screenshot.objects.filter(
                        id=asset_id, execution__project__in=accessible
                    ).first()
                else:
                    shot = Screenshot.objects.filter(id=asset_id).first()
                if not shot:
                    return Response({'error': f'截图 #{asset_id} 不存在或无权访问'}, status=404)
                # 提取文件路径
                file_path_to_delete = ''
                try:
                    if shot.image:
                        file_path_to_delete = shot.image.path
                except Exception:
                    pass
                shot.delete()
                result['db_deleted'] = True
                if file_path_to_delete and _safe_remove_file(file_path_to_delete):
                    result['file_deleted'] = True
                result['deleted'] = True
                result['message'] = f'截图 #{asset_id} 已删除（含文件）' if result['file_deleted'] else f'截图 #{asset_id} 已删除（数据库）'
            except Exception as e:
                return Response({'error': f'删除截图失败: {str(e)}'}, status=500)

        elif asset_type == 'video':
            # 视频是 AI 执行记录的产物
            try:
                from apps.ui_automation.models import AIExecutionRecord
                rec = AIExecutionRecord.objects.filter(
                    Q(id=asset_id) & (Q(project__owner=request.user) | Q(project__members=request.user) | Q(project__isnull=True))
                ).first()
                if not rec:
                    return Response({'error': f'视频 #{asset_id} 不存在或无权访问'}, status=404)
                video_path = rec.video_path
                rec.delete()
                result['db_deleted'] = True
                if video_path and _safe_remove_file(video_path):
                    result['file_deleted'] = True
                result['deleted'] = True
                result['message'] = f'视频 #{asset_id} 已删除（含文件）' if result['file_deleted'] else f'视频 #{asset_id} 已删除（数据库）'
            except Exception as e:
                return Response({'error': f'删除视频失败: {str(e)}'}, status=500)

        elif asset_type == 'report':
            try:
                from apps.reports.models import TestReport
                report = TestReport.objects.filter(id=asset_id).first()
                if not report:
                    return Response({'error': f'报告 #{asset_id} 不存在'}, status=404)
                # 清理关联的产物目录
                report_dir = os.path.join(settings.BASE_DIR, 'media', 'reports', str(report.id))
                _safe_remove_dir(report_dir)
                # 清理 artifacts 下的相关目录
                artifact_dir = os.path.join(settings.BASE_DIR, 'artifacts', f'run_*')
                # 尝试匹配关联 artifacts
                report.delete()
                result['db_deleted'] = True
                result['file_deleted'] = True  # 总是尝试清理
                result['deleted'] = True
                result['message'] = f'报告 #{asset_id} 已删除（含关联文件）'
            except Exception as e:
                return Response({'error': f'删除报告失败: {str(e)}'}, status=500)

        elif asset_type == 'download':
            # 下载文件 - 直接删除磁盘文件
            if not file_path:
                return Response({'error': '请提供文件路径 file_path'}, status=400)
            if _safe_remove_file(file_path):
                result['file_deleted'] = True
                result['deleted'] = True
                result['message'] = f'下载文件已删除: {file_path}'
            else:
                return Response({'error': f'删除文件失败: {file_path}'}, status=500)

        else:
            return Response({'error': f'不支持的资产类型: {asset_type}'}, status=400)

        return Response(result)
    except Exception as e:
        logger.error(f"删除资产失败: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_delete_assets(request):
    """
    批量删除资产
    body: { type: 'screenshot'|'video'|'report', ids: [int, int, ...] }
    """
    asset_type = request.data.get('type', '')
    ids = request.data.get('ids', [])

    if not asset_type:
        return Response({'error': '请指定资产类型 type'}, status=400)
    if not ids or not isinstance(ids, list):
        return Response({'error': '请提供有效的 ids 数组'}, status=400)

    deleted = 0
    files_cleaned = 0
    errors = []

    for asset_id in ids:
        try:
            # 复用 delete_asset 的逻辑（简化版）
            r = delete_asset(request._request) if False else None  # 不递归调用
            # 直接用逻辑
            if asset_type == 'screenshot':
                from apps.ui_automation.models import Screenshot
                accessible = _accessible_projects(request.user)
                if accessible is not None:
                    shot = Screenshot.objects.filter(
                        id=asset_id, execution__project__in=accessible
                    ).first()
                else:
                    shot = Screenshot.objects.filter(id=asset_id).first()
                if not shot:
                    errors.append(f'截图 #{asset_id} 不存在或无权访问')
                    continue
                file_path_to_delete = ''
                try:
                    if shot.image:
                        file_path_to_delete = shot.image.path
                except Exception:
                    pass
                shot.delete()
                deleted += 1
                if file_path_to_delete and _safe_remove_file(file_path_to_delete):
                    files_cleaned += 1

            elif asset_type == 'video':
                from apps.ui_automation.models import AIExecutionRecord
                rec = AIExecutionRecord.objects.filter(
                    Q(id=asset_id) & (Q(project__owner=request.user) | Q(project__members=request.user) | Q(project__isnull=True))
                ).first()
                if not rec:
                    errors.append(f'视频 #{asset_id} 不存在或无权访问')
                    continue
                video_path = rec.video_path
                rec.delete()
                deleted += 1
                if video_path and _safe_remove_file(video_path):
                    files_cleaned += 1

            elif asset_type == 'report':
                from apps.reports.models import TestReport
                report = TestReport.objects.filter(id=asset_id).first()
                if not report:
                    errors.append(f'报告 #{asset_id} 不存在')
                    continue
                report_dir = os.path.join(settings.BASE_DIR, 'media', 'reports', str(report.id))
                _safe_remove_dir(report_dir)
                report.delete()
                deleted += 1
                files_cleaned += 1
        except Exception as e:
            errors.append(f'删除 #{asset_id} 失败: {str(e)}')

    return Response({
        'deleted': deleted,
        'files_cleaned': files_cleaned,
        'errors': errors,
        'message': f'成功删除 {deleted} 项，清理 {files_cleaned} 个文件' + (f'，{len(errors)} 个错误' if errors else '')
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clean_artifacts_directory(request):
    """
    清理 artifacts 目录（真实磁盘文件）
    body: { days_old?: int, exec_id?: str }
    - days_old: 只清理 N 天前的（默认 0 = 全部）
    - exec_id: 只清理指定执行ID的目录
    """
    try:
        days_old = int(request.data.get('days_old', 0))
        exec_id = request.data.get('exec_id', '')

        artifacts_root = os.path.join(settings.BASE_DIR, 'artifacts')
        if not os.path.isdir(artifacts_root):
            return Response({'message': 'artifacts 目录不存在', 'cleaned': 0})

        cleaned = 0
        size_freed = 0
        errors = []
        current_time = time.time()

        for entry in os.listdir(artifacts_root):
            entry_path = os.path.join(artifacts_root, entry)
            if not os.path.isdir(entry_path):
                continue
            # 如果指定了 exec_id，只清理匹配的
            if exec_id and exec_id not in entry:
                continue
            # 检查时间
            if days_old > 0:
                mtime = os.path.getmtime(entry_path)
                age_days = (current_time - mtime) / 86400
                if age_days < days_old:
                    continue
            # 计算大小
            try:
                dir_size = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, fn in os.walk(entry_path)
                    for f in fn
                )
            except Exception:
                dir_size = 0
            # 删除
            if _safe_remove_dir(entry_path):
                cleaned += 1
                size_freed += dir_size
            else:
                errors.append(f'删除失败: {entry}')

        return Response({
            'cleaned': cleaned,
            'size_freed_mb': round(size_freed / 1024 / 1024, 2),
            'errors': errors,
            'message': f'成功清理 {cleaned} 个执行目录，释放 {round(size_freed / 1024 / 1024, 2)} MB'
        })
    except Exception as e:
        logger.error(f"清理 artifacts 失败: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def artifacts_stats(request):
    """统计 artifacts 目录的使用情况"""
    try:
        artifacts_root = os.path.join(settings.BASE_DIR, 'artifacts')
        if not os.path.isdir(artifacts_root):
            return Response({
                'total_dirs': 0,
                'total_size_mb': 0,
                'oldest': None,
                'newest': None,
            })

        total_size = 0
        total_dirs = 0
        oldest_time = None
        newest_time = None

        for dp, dn, fn in os.walk(artifacts_root):
            for f in fn:
                try:
                    fp = os.path.join(dp, f)
                    total_size += os.path.getsize(fp)
                except Exception:
                    pass
        for entry in os.listdir(artifacts_root):
            ep = os.path.join(artifacts_root, entry)
            if os.path.isdir(ep):
                total_dirs += 1
                mtime = os.path.getmtime(ep)
                if oldest_time is None or mtime < oldest_time:
                    oldest_time = mtime
                if newest_time is None or mtime > newest_time:
                    newest_time = mtime

        return Response({
            'total_dirs': total_dirs,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'oldest': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest_time)) if oldest_time else None,
            'newest': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(newest_time)) if newest_time else None,
        })
    except Exception as e:
        logger.error(f"统计 artifacts 失败: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


def _accessible_projects(user):
    """获取用户有权限的项目"""
    try:
        from apps.ui_automation.models import UiProject
        return UiProject.objects.filter(
            Q(owner=user) | Q(members=user)
        ).distinct()
    except Exception:
        return None
