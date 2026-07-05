"""
验证码/风控检测器
负责检测页面上的验证码、风控验证、安全挑战等阻塞场景
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CaptchaDetectionResult:
    """验证码检测结果"""
    
    def __init__(self):
        self.detected: bool = False
        self.captcha_type: str = ""  # slider, text, click, iframe, unknown
        self.block_reason: str = ""
        self.url: str = ""
        self.page_title: str = ""
        self.detection_time: str = ""
        self.evidence: Dict[str, str] = {}  # screenshot_path, dom_path, console_log_path
        self.blocking_elements: List[Dict] = []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'detected': self.detected,
            'captcha_type': self.captcha_type,
            'block_reason': self.block_reason,
            'url': self.url,
            'page_title': self.page_title,
            'detection_time': self.detection_time,
            'evidence': self.evidence,
            'blocking_elements': self.blocking_elements,
        }


class CaptchaDetector:
    """
    验证码/风控检测器
    检测页面上常见的验证码组件和风控提示
    """
    
    # 常见验证码相关文本关键词
    CAPTCHA_KEYWORDS = [
        '验证码', '验证', '安全验证', '请完成验证', '验证你是人类',
        '行为验证', '滑块验证', '图片验证', '文字验证', '图形验证',
        '人机验证', '智能验证', 'reCAPTCHA', 'Google验证',
        '滑动验证', '点选验证', '拼图验证', '拼图',
        '请点击', '请滑动', '请选择', '安全挑战',
        '验证失败', '验证超时', '请重新验证',
        # 英文关键词
        'captcha', 'CAPTCHA', 'verify', 'verification',
        'security check', 'human verification', 'robot check',
        'challenge', 'prove you are human', 'I am not a robot',
    ]
    
    # 常见验证码元素选择器
    CAPTCHA_SELECTORS = [
        # 滑块验证码
        '.captcha-slider', '.slider-captcha', '.geetest-slider', '.tc-slider',
        '.yidun-slider', '.secsdk-captcha', '.nc_captcha', '.captcha-box',
        '[class*="slider"]', '[class*="captcha"]',
        
        # reCAPTCHA
        'iframe[src*="recaptcha"]', '.g-recaptcha', '[data-sitekey]',
        
        # 点选验证码
        '.click-captcha', '.image-captcha', '.pic-captcha',
        
        # 文字输入验证码
        '[name*="captcha"]', '[id*="captcha"]', '[class*="captcha-input"]',
        
        # 通用验证码容器
        '.captcha-container', '.captcha-wrapper', '.verification-container',
    ]
    
    # 风控页面特征URL模式
    RISK_URL_PATTERNS = [
        re.compile(r'.*risk.*', re.IGNORECASE),
        re.compile(r'.*security.*', re.IGNORECASE),
        re.compile(r'.*verify.*', re.IGNORECASE),
        re.compile(r'.*captcha.*', re.IGNORECASE),
        re.compile(r'.*challenge.*', re.IGNORECASE),
    ]
    
    def __init__(self):
        self.detection_history: List[CaptchaDetectionResult] = []
    
    async def detect(self, page) -> CaptchaDetectionResult:
        """
        检测页面上是否存在验证码或风控阻塞
        
        Args:
            page: Playwright Page 对象
            
        Returns:
            CaptchaDetectionResult: 检测结果
        """
        result = CaptchaDetectionResult()
        result.url = page.url
        result.detection_time = datetime.now().isoformat()
        
        try:
            result.page_title = await page.title()
        except Exception:
            result.page_title = ""
        
        # 1. 检查URL是否包含风控特征
        if self._check_risk_url(page.url):
            result.detected = True
            result.captcha_type = "risk_page"
            result.block_reason = f"URL包含风控特征: {page.url}"
            logger.warning(f"检测到风控URL: {page.url}")
            self.detection_history.append(result)
            return result
        
        # 2. 检查页面标题是否包含验证码关键词
        if self._check_title_keywords(result.page_title):
            result.detected = True
            result.captcha_type = "title_detected"
            result.block_reason = f"页面标题包含验证码关键词: {result.page_title}"
            logger.warning(f"检测到标题包含验证码关键词: {result.page_title}")
            self.detection_history.append(result)
            return result
        
        # 3. 检查页面文本是否包含验证码关键词
        text_result = await self._check_page_text(page)
        if text_result['detected']:
            result.detected = True
            result.captcha_type = text_result['captcha_type']
            result.block_reason = text_result['reason']
            logger.warning(f"检测到页面文本包含验证码关键词: {text_result['reason']}")
            self.detection_history.append(result)
            return result
        
        # 4. 检查页面元素是否包含验证码相关元素
        element_result = await self._check_captcha_elements(page)
        if element_result['detected']:
            result.detected = True
            result.captcha_type = element_result['captcha_type']
            result.block_reason = element_result['reason']
            result.blocking_elements = element_result['elements']
            logger.warning(f"检测到验证码元素: {element_result['reason']}")
            self.detection_history.append(result)
            return result
        
        # 5. 检查是否存在验证码iframe
        iframe_result = await self._check_captcha_iframe(page)
        if iframe_result['detected']:
            result.detected = True
            result.captcha_type = "iframe_captcha"
            result.block_reason = iframe_result['reason']
            logger.warning(f"检测到验证码iframe: {iframe_result['reason']}")
            self.detection_history.append(result)
            return result
        
        logger.debug(f"未检测到验证码/风控阻塞: {page.url}")
        return result
    
    def _check_risk_url(self, url: str) -> bool:
        """检查URL是否包含风控特征"""
        for pattern in self.RISK_URL_PATTERNS:
            if pattern.match(url):
                return True
        return False
    
    def _check_title_keywords(self, title: str) -> bool:
        """检查页面标题是否包含验证码关键词"""
        if not title:
            return False
        
        title_lower = title.lower()
        for keyword in self.CAPTCHA_KEYWORDS:
            if keyword.lower() in title_lower:
                return True
        return False
    
    async def _check_page_text(self, page) -> Dict[str, Any]:
        """检查页面文本是否包含验证码关键词"""
        try:
            # 获取页面body文本
            body_text = await page.evaluate('document.body.innerText')
            
            if not body_text:
                return {'detected': False}
            
            body_text_lower = body_text.lower()
            
            # 检查关键词
            matched_keywords = []
            for keyword in self.CAPTCHA_KEYWORDS:
                if keyword.lower() in body_text_lower:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                return {
                    'detected': True,
                    'captcha_type': "text_detected",
                    'reason': f"页面文本包含验证码关键词: {', '.join(matched_keywords)}",
                }
            
        except Exception as e:
            logger.warning(f"检查页面文本失败: {e}")
        
        return {'detected': False}
    
    async def _check_captcha_elements(self, page) -> Dict[str, Any]:
        """检查页面元素是否包含验证码相关元素"""
        found_elements = []
        
        for selector in self.CAPTCHA_SELECTORS:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    # 获取元素信息
                    elements = await page.locator(selector).all()
                    for element in elements[:3]:  # 最多记录3个
                        try:
                            element_info = await self._get_element_info(element)
                            found_elements.append(element_info)
                        except Exception:
                            pass
            except Exception:
                continue
        
        if found_elements:
            return {
                'detected': True,
                'captcha_type': "element_detected",
                'reason': f"找到 {len(found_elements)} 个验证码相关元素",
                'elements': found_elements,
            }
        
        return {'detected': False}
    
    async def _get_element_info(self, element) -> Dict[str, str]:
        """获取元素信息"""
        info = {}
        
        try:
            info['tag_name'] = await element.evaluate('el => el.tagName')
        except Exception:
            info['tag_name'] = ""
        
        try:
            info['class'] = await element.evaluate('el => el.className')
        except Exception:
            info['class'] = ""
        
        try:
            info['id'] = await element.evaluate('el => el.id')
        except Exception:
            info['id'] = ""
        
        try:
            info['text'] = await element.inner_text()
            if len(info['text']) > 100:
                info['text'] = info['text'][:100] + "..."
        except Exception:
            info['text'] = ""
        
        try:
            info['visible'] = await element.is_visible()
        except Exception:
            info['visible'] = False
        
        return info
    
    async def _check_captcha_iframe(self, page) -> Dict[str, Any]:
        """检查页面是否包含验证码iframe"""
        try:
            # 获取所有iframe
            iframes = await page.locator('iframe').all()
            
            for iframe in iframes:
                try:
                    src = await iframe.get_attribute('src')
                    if src:
                        # 检查src是否包含验证码相关域名
                        captcha_domains = ['captcha', 'geetest', 'yidun', 'recaptcha', 'secsdk', 'ncaptcha']
                        for domain in captcha_domains:
                            if domain.lower() in src.lower():
                                return {
                                    'detected': True,
                                    'reason': f"找到验证码iframe: {src}",
                                }
                except Exception:
                    continue
        
        except Exception as e:
            logger.warning(f"检查iframe失败: {e}")
        
        return {'detected': False}
    
    async def capture_evidence(self, page, result: CaptchaDetectionResult, output_dir: str) -> None:
        """
        捕获检测证据
        
        Args:
            page: Playwright Page 对象
            result: 检测结果
            output_dir: 输出目录
        """
        import os
        import time
        
        timestamp = int(time.time() * 1000)
        
        # 截图
        try:
            screenshot_path = os.path.join(output_dir, 'screenshots', f"captcha_detected_{timestamp}.png")
            screenshot_bytes = await page.screenshot(full_page=True)
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_bytes)
            result.evidence['screenshot_path'] = screenshot_path
        except Exception as e:
            logger.warning(f"保存截图失败: {e}")
        
        # DOM
        try:
            dom_path = os.path.join(output_dir, 'dom', f"captcha_detected_{timestamp}.html")
            html_content = await page.content()
            with open(dom_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            result.evidence['dom_path'] = dom_path
        except Exception as e:
            logger.warning(f"保存DOM失败: {e}")
        
        # 控制台日志（如果已收集）
        # 控制台日志通常由StepExecutor收集
    
    def get_history(self) -> List[CaptchaDetectionResult]:
        """获取检测历史"""
        return self.detection_history
    
    def reset_history(self) -> None:
        """重置检测历史"""
        self.detection_history = []


# 全局实例
_captcha_detector = None


def get_captcha_detector() -> CaptchaDetector:
    """获取全局验证码检测器实例"""
    global _captcha_detector
    if _captcha_detector is None:
        _captcha_detector = CaptchaDetector()
    return _captcha_detector
