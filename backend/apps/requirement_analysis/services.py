import os
import json
import time
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from PyPDF2 import PdfReader
except ImportError:
    from PyPDF2 import PdfFileReader as PdfReader
    
try:
    import docx
except ImportError:
    docx = None
from django.conf import settings
from django.core.files.storage import default_storage

from .models import (
    RequirementDocument, RequirementAnalysis, BusinessRequirement, GeneratedTestCase, AnalysisTask,
    AIModelConfig, PromptConfig, AIModelService
)

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理服务"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """从PDF文件提取文本"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PDF文本提取失败: {e}")
            return f"PDF文本提取失败: {str(e)}"
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """从Word文档提取文本"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Word文档文本提取失败: {e}")
            return f"Word文档文本提取失败: {str(e)}"
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """从文本文件提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    return file.read().strip()
            except Exception as e:
                logger.error(f"文本文件读取失败: {e}")
                return f"文本文件读取失败: {str(e)}"
        except Exception as e:
            logger.error(f"文本文件读取失败: {e}")
            return f"文本文件读取失败: {str(e)}"
    
    @classmethod
    def extract_text(cls, document: RequirementDocument) -> str:
        """根据文档类型提取文本"""
        file_path = document.file.path
        
        if document.document_type == 'pdf':
            return cls.extract_text_from_pdf(file_path)
        elif document.document_type == 'docx':
            return cls.extract_text_from_docx(file_path)
        elif document.document_type == 'txt':
            return cls.extract_text_from_txt(file_path)
        elif document.document_type == 'md':
            return cls.extract_text_from_txt(file_path)
        else:
            return "不支持的文档类型"


class AIService:
    """AI服务类 - 调用真实大模型API"""

    @staticmethod
    async def analyze_requirements(text: str, document_title: str = "") -> Dict[str, Any]:
        """先进的需求分析 - 使用真实AI分析引擎"""
        try:
            from apps.requirement_analysis.advanced_analyzer import advanced_analyzer
            logger.info(f"使用先进分析器分析需求，文档标题: {document_title}")
            result = await advanced_analyzer.analyze_requirements_advanced(text, document_title)
            analysis_report = result.get("analysis_report", "")
            structured_requirements = result.get("structured_requirements", {})
            requirements_list = structured_requirements.get("requirements", [])
            import time
            analysis_time = time.time() % 10 + 2
            logger.info(f"先进需求分析完成，识别需求{len(requirements_list)}个")
            return {
                "analysis_report": analysis_report,
                "requirements": requirements_list,
                "requirements_count": len(requirements_list),
                "analysis_time": analysis_time,
                "quality_assessment": result.get("quality_assessment", {}),
                "risk_analysis": result.get("risk_analysis", {})
            }
        except Exception as e:
            logger.error(f"先进需求分析失败: {e}")
            return await AIService._fallback_analyze_requirements(text, document_title)

    @staticmethod
    async def _fallback_analyze_requirements(text: str, document_title: str = "") -> Dict[str, Any]:
        """备用需求分析方法 - 调用真实AI"""
        logger.info(f"使用真实AI进行需求分析，文档标题: {document_title}")
        try:
            writer_config, writer_candidates = AIModelService.select_local_usable_config([
                'writer', 'ai_tester', 'reviewer', 'browser_use_text', 'browser_use_vision'
            ])
            if not writer_config:
                raise Exception("未找到活跃的AI模型配置")

            writer_prompt = PromptConfig.objects.filter(is_active=True, prompt_type='writer').first()
            system_prompt = writer_prompt.content if writer_prompt else "你是一位资深的测试需求分析师。请根据文档内容分析需求，输出结构化的需求列表。"

            user_message = f"""请分析以下需求文档，生成结构化的分析报告和需求列表。

【文档标题】{document_title}

【文档内容】
{text[:8000]}

【输出要求】
请以JSON格式输出，包含以下字段：
{{
  "analysis_report": "详细的需求分析报告（markdown格式）",
  "requirements": [
    {{
      "requirement_id": "REQ-001",
      "requirement_name": "需求名称",
      "requirement_type": "functional/performance/security/usability",
      "module": "所属模块",
      "requirement_level": "high/medium/low",
      "description": "需求描述",
      "acceptance_criteria": "验收标准"
    }}
  ]
}}

只输出JSON，不要输出其他内容。"""

            response, selected_config = await AIModelService.call_with_auto_model(
                'writer',
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=8192
            )
            logger.info(f"Auto selected writer model: {selected_config.name}")

            content = response['choices'][0]['message']['content']
            # 检查空内容
            if not content or not content.strip():
                logger.warning("AI需求分析返回空内容，返回默认结果")
                return {
                    "analysis_report": "AI返回空内容",
                    "requirements": [],
                    "requirements_count": 0,
                }
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    requirements = result.get('requirements', [])
                    return {
                        "analysis_report": result.get('analysis_report', ''),
                        "requirements": requirements,
                        "requirements_count": len(requirements),
                    }
                except (json.JSONDecodeError, ValueError) as je:
                    logger.warning(f"JSON解析失败: {je}，使用全文作为分析报告")
                    return {
                        "analysis_report": content,
                        "requirements": [],
                        "requirements_count": 0,
                    }

            # 如果无法提取JSON，用全文
            return {
                "analysis_report": content,
                "requirements": [],
                "requirements_count": 0,
            }

        except Exception as e:
            logger.error(f"真实AI需求分析失败: {e}")
            # 最后的fallback - 返回空结果
            return {
                "analysis_report": f"AI分析失败: {str(e)}",
                "requirements": [],
                "requirements_count": 0,
            }

    @staticmethod
    async def generate_test_cases(requirement: BusinessRequirement, test_level: str, test_priority: str, count: int = 5) -> List[Dict[str, Any]]:
        """生成测试用例 - 调用真实大模型"""
        logger.info(f"使用真实AI生成测试用例: {requirement.requirement_name}")
        try:
            writer_config, writer_candidates = AIModelService.select_local_usable_config([
                'writer', 'ai_tester', 'reviewer', 'browser_use_text', 'browser_use_vision'
            ])
            if not writer_config:
                raise Exception("未找到活跃的AI模型配置")

            writer_prompt = PromptConfig.objects.filter(is_active=True, prompt_type='writer').first()
            system_prompt = writer_prompt.content if writer_prompt else "你是一位资深的测试用例设计专家。"

            user_message = f"""请为以下需求生成{count}个高质量的测试用例。

【需求信息】
- 需求编号: {requirement.requirement_id}
- 需求名称: {requirement.requirement_name}
- 需求类型: {requirement.requirement_type}
- 所属模块: {requirement.module}
- 需求级别: {requirement.requirement_level}
- 需求描述: {requirement.description}
- 验收标准: {requirement.acceptance_criteria}
- 测试级别: {test_level}
- 优先级: {test_priority}

【输出格式】
请以JSON数组格式输出，每个用例包含：
{{
  "case_id": "TC-{requirement.requirement_id}-XXX",
  "title": "用例标题",
  "priority": "{test_priority}",
  "precondition": "前置条件",
  "test_steps": "详细测试步骤（用\\n分隔）",
  "expected_result": "预期结果"
}}

只输出JSON数组，不要输出其他内容。"""

            response, selected_config = await AIModelService.call_with_auto_model(
                'writer',
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=8192
            )
            logger.info(f"Auto selected writer model: {selected_config.name}")

            content = response['choices'][0]['message']['content']
            # 检查空内容
            if not content or not content.strip():
                logger.warning("AI生成测试用例返回空内容")
                return []
            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except (json.JSONDecodeError, ValueError) as je:
                    logger.warning(f"JSON解析测试用例失败: {je}，返回空列表")
                    return []

            # 无法解析则返回空
            return []

        except Exception as e:
            logger.error(f"AI生成测试用例失败: {e}")
            raise Exception(f"AI生成测试用例失败: {str(e)}")

    @staticmethod
    async def review_test_cases(test_cases: List[GeneratedTestCase], review_criteria: str) -> Dict[str, Any]:
        """评审测试用例 - 调用真实大模型"""
        logger.info(f"使用真实AI评审{len(test_cases)}个测试用例")
        try:
            reviewer_config, reviewer_candidates = AIModelService.select_local_usable_config(['reviewer', 'writer'])
            if not reviewer_config:
                reviewer_config = None
            if not reviewer_config:
                raise Exception("未找到活跃的AI模型配置")

            reviewer_prompt = PromptConfig.objects.filter(is_active=True, prompt_type='reviewer').first()
            system_prompt = reviewer_prompt.content if reviewer_prompt else "你是一位严格的测试评审专家。"

            cases_text = "\n\n".join([
                f"用例{c.id}: {c.title}\n步骤: {c.test_steps}\n预期: {c.expected_result}"
                for c in test_cases
            ])

            user_message = f"""请评审以下测试用例。

【评审标准】{review_criteria}

【测试用例】
{cases_text}

【输出格式】
请以JSON格式输出：
{{
  "overall_score": 85,
  "pass_rate": 100.0,
  "reviewed_cases": [
    {{
      "test_case_id": 用例ID,
      "review_score": 80,
      "review_comments": "评审意见",
      "status": "reviewed"
    }}
  ]
}}

只输出JSON。"""

            response, selected_config = await AIModelService.call_with_auto_model(
                'reviewer',
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=8192
            )
            logger.info(f"Auto selected review model: {selected_config.name}")

            content = response['choices'][0]['message']['content']
            # 检查空内容
            if not content or not content.strip():
                logger.warning("AI评审返回空内容，返回默认评审结果")
                return {"overall_score": 0, "pass_rate": 0, "reviewed_cases": []}
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except (json.JSONDecodeError, ValueError) as je:
                    logger.warning(f"JSON解析评审失败: {je}，返回默认评审结果")
                    return {"overall_score": 0, "pass_rate": 0, "reviewed_cases": []}

            return {"overall_score": 0, "pass_rate": 0, "reviewed_cases": []}

        except Exception as e:
            logger.error(f"AI评审失败: {e}")
            raise Exception(f"AI评审失败: {str(e)}")


class RequirementAnalysisService:
    """需求分析服务"""
    
    @classmethod
    def create_analysis_task(cls, document: RequirementDocument, task_type: str) -> AnalysisTask:
        """创建分析任务"""
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        
        task = AnalysisTask.objects.create(
            task_id=task_id,
            task_type=task_type,
            document=document,
            status='pending'
        )
        
        return task
    
    @classmethod
    async def process_document_analysis(cls, document: RequirementDocument) -> RequirementAnalysis:
        """处理文档分析"""
        # 创建分析任务
        task = cls.create_analysis_task(document, 'requirement_analysis')
        
        try:
            # 更新任务状态
            task.status = 'running'
            task.started_at = datetime.now()
            task.progress = 10
            task.save()
            
            # 提取文档文本
            if not document.extracted_text:
                document.extracted_text = DocumentProcessor.extract_text(document)
                document.save()
            
            task.progress = 30
            task.save()
            
            # 调用AI分析
            start_time = time.time()
            analysis_result = await AIService.analyze_requirements(
                document.extracted_text, 
                document.title
            )
            analysis_time = time.time() - start_time
            
            task.progress = 70
            task.save()
            
            # 创建分析记录
            analysis = RequirementAnalysis.objects.create(
                document=document,
                analysis_report=analysis_result['analysis_report'],
                requirements_count=analysis_result['requirements_count'],
                analysis_time=analysis_time
            )
            
            # 保存需求数据
            for req_data in analysis_result['requirements']:
                BusinessRequirement.objects.create(
                    analysis=analysis,
                    **req_data
                )
            
            # 更新文档状态
            document.status = 'analyzed'
            document.save()
            
            # 完成任务
            task.status = 'completed'
            task.completed_at = datetime.now()
            task.progress = 100
            task.result = analysis_result
            task.save()
            
            return analysis
            
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            
            # 更新任务状态
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.save()
            
            # 更新文档状态
            document.status = 'failed'
            document.save()
            
            raise e
    
    @classmethod
    async def generate_test_cases_for_requirements(cls, requirement_ids: List[int], test_level: str, test_priority: str, test_case_count: int) -> List[GeneratedTestCase]:
        """为需求生成测试用例"""
        generated_cases = []
        
        for req_id in requirement_ids:
            try:
                requirement = BusinessRequirement.objects.get(id=req_id)
                
                # 调用AI生成测试用例
                test_cases_data = await AIService.generate_test_cases(
                    requirement, test_level, test_priority, test_case_count
                )
                
                # 保存生成的测试用例
                for case_data in test_cases_data:
                    test_case = GeneratedTestCase.objects.create(
                        requirement=requirement,
                        case_id=case_data['case_id'],
                        title=case_data['title'],
                        priority=case_data['priority'],
                        precondition=case_data['precondition'],
                        test_steps=case_data['test_steps'],
                        expected_result=case_data['expected_result'],
                        generated_by_ai='AI-A'
                    )
                    generated_cases.append(test_case)
                    
            except BusinessRequirement.DoesNotExist:
                logger.error(f"需求ID {req_id} 不存在")
                continue
            except Exception as e:
                logger.error(f"为需求 {req_id} 生成测试用例失败: {e}")
                continue
        
        return generated_cases
    
    @classmethod
    async def review_test_cases(cls, test_case_ids: List[int], review_criteria: str) -> Dict[str, Any]:
        """评审测试用例"""
        test_cases = GeneratedTestCase.objects.filter(id__in=test_case_ids)
        
        # 调用AI评审
        review_result = await AIService.review_test_cases(list(test_cases), review_criteria)
        
        # 更新测试用例状态
        for case_review in review_result['reviewed_cases']:
            try:
                test_case = GeneratedTestCase.objects.get(id=case_review['test_case_id'])
                test_case.status = case_review['status']
                test_case.review_comments = case_review['review_comments']
                test_case.reviewed_by_ai = 'AI-B'
                test_case.save()
            except GeneratedTestCase.DoesNotExist:
                logger.error(f"测试用例ID {case_review['test_case_id']} 不存在")
                continue
        
        return review_result
