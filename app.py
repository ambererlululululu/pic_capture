from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
from PIL import Image
import io
import base64
import time
import hashlib
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# 简单的内存收集器（仅当前进程内有效）
collected_links = []

class ContentExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
    
    def extract_text_content(self, soup, url):
        """提取网页的文字内容"""
        text_content = {
            'title': '',
            'main_content': '',
            'headings': [],
            'paragraphs': [],
            'lists': [],
            'links': [],
            'full_text': ''
        }
        
        try:
            # 提取标题
            title_tag = soup.find('title')
            if title_tag:
                text_content['title'] = title_tag.get_text().strip()
            
            # 提取主内容区域（优先选择article, main, content等语义化标签）
            main_content_selectors = [
                'article', 'main', '[role="main"]', '.content', '.main-content', 
                '.post-content', '.article-content', '.entry-content',
                '#content', '#main', '.container', 'body'
            ]
            
            main_element = None
            for selector in main_content_selectors:
                main_element = soup.select_one(selector)
                if main_element:
                    break
            
            if not main_element:
                main_element = soup.find('body')
            
            if main_element:
                # 提取标题
                headings = main_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for heading in headings:
                    heading_text = heading.get_text().strip()
                    if heading_text:
                        text_content['headings'].append({
                            'level': heading.name,
                            'text': heading_text
                        })
                
                # 提取段落
                paragraphs = main_element.find_all('p')
                for p in paragraphs:
                    p_text = p.get_text().strip()
                    if p_text and len(p_text) > 10:  # 过滤太短的段落
                        text_content['paragraphs'].append(p_text)
                
                # 提取列表
                lists = main_element.find_all(['ul', 'ol'])
                for list_elem in lists:
                    list_items = []
                    for li in list_elem.find_all('li'):
                        li_text = li.get_text().strip()
                        if li_text:
                            list_items.append(li_text)
                    if list_items:
                        text_content['lists'].append({
                            'type': list_elem.name,
                            'items': list_items
                        })
                
                # 提取链接
                links = main_element.find_all('a', href=True)
                for link in links:
                    link_text = link.get_text().strip()
                    href = link.get('href')
                    if link_text and href:
                        # 转换为绝对URL
                        absolute_url = urljoin(url, href)
                        text_content['links'].append({
                            'text': link_text,
                            'url': absolute_url
                        })
                
                # 提取完整文本内容
                # 移除脚本和样式标签
                for script in main_element(["script", "style", "nav", "header", "footer", "aside"]):
                    script.decompose()
                
                # 获取纯文本
                full_text = main_element.get_text()
                # 清理文本
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                text_content['full_text'] = '\n'.join(lines)
                
                # 生成主要内容的摘要
                if text_content['paragraphs']:
                    text_content['main_content'] = '\n\n'.join(text_content['paragraphs'][:5])  # 取前5个段落
                elif text_content['full_text']:
                    # 如果没有段落，从完整文本中提取前500字符
                    text_content['main_content'] = text_content['full_text'][:500] + '...' if len(text_content['full_text']) > 500 else text_content['full_text']
        
        except Exception as e:
            print(f"文字提取错误: {e}")
        
        return text_content

    def extract_images_from_url(self, url, cookie: str = None):
        """从URL提取所有图片链接"""
        try:
            # 尝试多种请求方式
            response = None
            for attempt in range(3):
                try:
                    if attempt == 0:
                        # 第一次尝试：标准请求
                        headers = self.session.headers.copy()
                        if cookie:
                            headers['Cookie'] = cookie
                        response = self.session.get(url, headers=headers, timeout=10)
                    elif attempt == 1:
                        # 第二次尝试：添加更多浏览器头
                        headers = self.session.headers.copy()
                        headers.update({
                            'Referer': 'https://www.google.com/',
                            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                            'Sec-Ch-Ua-Mobile': '?0',
                            'Sec-Ch-Ua-Platform': '"macOS"'
                        })
                        if cookie:
                            headers['Cookie'] = cookie
                        response = self.session.get(url, headers=headers, timeout=10)
                    else:
                        # 第三次尝试：使用不同的User-Agent
                        headers = self.session.headers.copy()
                        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        if cookie:
                            headers['Cookie'] = cookie
                        response = self.session.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        break
                    elif response.status_code == 403:
                        if attempt < 2:  # 还有重试机会
                            continue
                        else:
                            return {'error': f'访问被拒绝 (403 Forbidden)。这可能是由于网站的反爬虫保护。请尝试：\n1. 使用直接的图片链接\n2. 尝试其他网站\n3. 稍后再试'}
                    else:
                        response.raise_for_status()
                        
                except requests.exceptions.RequestException as e:
                    if attempt == 2:  # 最后一次尝试
                        raise e
                    continue
            
            if not response:
                return {'error': '无法连接到服务器'}
            
            # 检查是否是直接的图片链接
            content_type = response.headers.get('content-type', '').lower()
            if 'image' in content_type:
                # 这是一个直接的图片链接
                return [{
                    'url': url,
                    'alt': '直接图片链接',
                    'width': '',
                    'height': '',
                    'original_src': url,
                    'is_direct_image': True
                }]
            
            # 确保内容被正确解码
            content = response.content
            if response.encoding:
                try:
                    content = content.decode(response.encoding)
                except:
                    content = content.decode('utf-8', errors='ignore')
            else:
                content = content.decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # 提取文字内容
            text_content = self.extract_text_content(soup, url)
            
            images = []
            
            # 查找所有img标签
            img_tags = soup.find_all('img')
            for img in img_tags:
                # 检查多种可能的src属性
                src = (img.get('src') or 
                       img.get('data-src') or 
                       img.get('data-lazy-src') or 
                       img.get('data-original') or 
                       img.get('data-srcset') or 
                       img.get('data-lazy') or
                       img.get('data-url') or
                       img.get('data-image') or
                       img.get('data-img'))
                
                if src:
                    # 处理srcset属性（包含多个图片URL）
                    if 'data-srcset' in img.attrs:
                        srcset = img.get('data-srcset', '')
                        # 解析srcset中的URL
                        srcset_urls = re.findall(r'([^\s,]+)', srcset)
                        for srcset_url in srcset_urls:
                            absolute_url = urljoin(url, srcset_url)
                            images.append({
                                'url': absolute_url,
                                'alt': img.get('alt', ''),
                                'width': img.get('width', ''),
                                'height': img.get('height', ''),
                                'original_src': srcset_url,
                                'source': 'srcset'
                            })
                    
                    # 转换为绝对URL
                    absolute_url = urljoin(url, src)
                    alt_text = img.get('alt', '')
                    width = img.get('width', '')
                    height = img.get('height', '')
                    
                    images.append({
                        'url': absolute_url,
                        'alt': alt_text,
                        'width': width,
                        'height': height,
                        'original_src': src
                    })
            
            # 查找CSS背景图片
            style_tags = soup.find_all('style')
            for style in style_tags:
                if style.string:
                    # 改进的背景图片正则表达式
                    bg_patterns = [
                        r'background-image:\s*url\(["\']?([^"\']+)["\']?\)',
                        r'background:\s*url\(["\']?([^"\']+)["\']?\)',
                        r'background:\s*[^;]*url\(["\']?([^"\']+)["\']?\)',
                    ]
                    for pattern in bg_patterns:
                        bg_images = re.findall(pattern, style.string, re.IGNORECASE)
                    for bg_img in bg_images:
                        absolute_url = urljoin(url, bg_img)
                        images.append({
                            'url': absolute_url,
                            'alt': 'CSS背景图片',
                            'width': '',
                            'height': '',
                                'original_src': bg_img,
                                'source': 'css'
                            })
            
            # 抓取并解析外链 CSS 文件中的背景图片
            try:
                stylesheet_links = soup.find_all('link', rel=lambda x: x and 'stylesheet' in x)
                for link in stylesheet_links:
                    href = link.get('href')
                    if not href:
                        continue
                    css_url = urljoin(url, href)
                    try:
                        css_headers = {'Referer': url}
                        if cookie:
                            css_headers['Cookie'] = cookie
                        css_resp = self.session.get(css_url, headers=css_headers, timeout=8)
                        if css_resp.status_code == 200 and css_resp.text:
                            css_text = css_resp.text
                            css_bg_urls = re.findall(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', css_text, re.IGNORECASE)
                            for bg_url in css_bg_urls:
                                if bg_url.startswith('data:'):
                                    # 忽略内联 data url，这里交由后续逻辑处理
                                    continue
                                absolute_url = urljoin(css_url, bg_url)
                                if not any(absolute_url == existing['url'] for existing in images):
                                    images.append({
                                        'url': absolute_url,
                                        'alt': '外链CSS背景图片',
                                        'width': '',
                                        'height': '',
                                        'original_src': bg_url,
                                        'source': 'external-css'
                                    })
                    except Exception:
                        # 忽略单个 CSS 拉取失败
                        pass
            except Exception:
                pass

            # 查找内联样式中的背景图片
            elements_with_style = soup.find_all(attrs={'style': True})
            for element in elements_with_style:
                style_attr = element.get('style', '')
                bg_images = re.findall(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style_attr, re.IGNORECASE)
                for bg_img in bg_images:
                    absolute_url = urljoin(url, bg_img)
                    images.append({
                        'url': absolute_url,
                        'alt': '内联样式背景图片',
                        'width': '',
                        'height': '',
                        'original_src': bg_img,
                        'source': 'inline-css'
                    })
            
            # 查找其他可能包含图片的元素
            # 检查picture标签
            picture_tags = soup.find_all('picture')
            for picture in picture_tags:
                sources = picture.find_all('source')
                for source in sources:
                    srcset = source.get('srcset', '')
                    if srcset:
                        srcset_urls = re.findall(r'([^\s,]+)', srcset)
                        for srcset_url in srcset_urls:
                            absolute_url = urljoin(url, srcset_url)
                            images.append({
                                'url': absolute_url,
                                'alt': 'Picture元素图片',
                                'width': '',
                                'height': '',
                                'original_src': srcset_url,
                                'source': 'picture'
                            })
            
            # 提取 meta 图片（OG / Twitter 等）
            try:
                meta_candidates = []
                meta_candidates.extend(soup.find_all('meta', attrs={'property': 'og:image'}))
                meta_candidates.extend(soup.find_all('meta', attrs={'property': 'og:image:url'}))
                meta_candidates.extend(soup.find_all('meta', attrs={'name': 'twitter:image'}))
                meta_candidates.extend(soup.find_all('meta', attrs={'itemprop': 'image'}))
                for meta in meta_candidates:
                    content = meta.get('content')
                    if not content:
                        continue
                    absolute_url = urljoin(url, content)
                    if not any(absolute_url == existing['url'] for existing in images):
                        images.append({
                            'url': absolute_url,
                            'alt': 'Meta图片',
                            'width': '',
                            'height': '',
                            'original_src': content,
                            'source': 'meta'
                        })
            except Exception:
                pass

            # 解析 noscript 中的图片
            try:
                noscripts = soup.find_all('noscript')
                for ns in noscripts:
                    ns_html = ns.string or ns.decode_contents()
                    if not ns_html:
                        continue
                    ns_soup = BeautifulSoup(ns_html, 'html.parser')
                    for img in ns_soup.find_all('img'):
                        ns_src = img.get('src') or img.get('data-src')
                        if not ns_src:
                            continue
                        absolute_url = urljoin(url, ns_src)
                        if not any(absolute_url == existing['url'] for existing in images):
                            images.append({
                                'url': absolute_url,
                                'alt': img.get('alt', 'noscript图片'),
                                'width': img.get('width', ''),
                                'height': img.get('height', ''),
                                'original_src': ns_src,
                                'source': 'noscript'
                            })
            except Exception:
                pass

            # 检查video标签的poster属性
            video_tags = soup.find_all('video')
            for video in video_tags:
                poster = video.get('poster')
                if poster:
                    absolute_url = urljoin(url, poster)
                    images.append({
                        'url': absolute_url,
                        'alt': '视频封面',
                        'width': '',
                        'height': '',
                        'original_src': poster,
                        'source': 'video-poster'
                        })
            
            # 查找JavaScript中的图片URL（常见模式）
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # 扩展的图片URL模式
                    img_patterns = [
                        # 标准图片格式
                        r'https?://[^"\s,]+\.(?:jpg|jpeg|png|gif|webp|svg|bmp|ico|tiff)',
                        # 包含images路径的URL
                        r'https?://[^"\s,]*images[^"\s,]*\.(?:jpg|jpeg|png|gif|webp|svg|bmp)',
                        # 特定域名模式
                        r'https?://[^"\s,]*\.itc\.cn[^"\s,]*\.(?:jpg|jpeg|png|gif|webp|svg|bmp)',
                        r'https?://[^"\s,]*openai\.com[^"\s,]*\.(?:jpg|jpeg|png|gif|webp|svg|bmp)',
                        r'https?://[^"\s,]*doubao\.com[^"\s,]*\.(?:jpg|jpeg|png|gif|webp|svg|bmp)',
                        # 缩略图
                        r'https?://[^"\s,]*thumbnails[^"\s,]*',
                        r'https?://[^"\s,]*thumb[^"\s,]*\.(?:jpg|jpeg|png|gif|webp)',
                        # CDN图片
                        r'https?://[^"\s,]*cdn[^"\s,]*\.(?:jpg|jpeg|png|gif|webp|svg|bmp)',
                        # 数据URL (base64图片)
                        r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+',
                        # 相对路径图片
                        r'["\'][^"\']*\.(?:jpg|jpeg|png|gif|webp|svg|bmp)["\']',
                    ]
                    
                    for pattern in img_patterns:
                        found_urls = re.findall(pattern, script.string, re.IGNORECASE)
                        for img_url in found_urls:
                            # 清理URL（移除可能的引号或逗号）
                            img_url = img_url.strip('"\'",')
                            
                            # 处理相对路径
                            if not img_url.startswith(('http://', 'https://', 'data:')):
                                if img_url.startswith('/'):
                                    img_url = urljoin(url, img_url)
                                else:
                                    img_url = urljoin(url, '/' + img_url)
                            
                            # 检查是否已存在
                            if img_url and not any(img_url in existing['url'] for existing in images):
                                images.append({
                                    'url': img_url,
                                    'alt': 'JavaScript动态图片',
                                    'width': '',
                                    'height': '',
                                    'original_src': img_url,
                                    'source': 'javascript'
                                })
            
            # 查找JSON数据中的图片URL
            json_scripts = soup.find_all('script', type='application/json')
            for script in json_scripts:
                if script.string:
                    try:
                        import json
                        data = json.loads(script.string)
                        # 递归查找JSON中的图片URL
                        def find_images_in_json(obj, path=""):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if isinstance(value, str) and any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']):
                                        if value.startswith(('http://', 'https://')):
                                            absolute_url = value
                                        else:
                                            absolute_url = urljoin(url, value)
                                        
                                        if not any(absolute_url in existing['url'] for existing in images):
                                            images.append({
                                                'url': absolute_url,
                                                'alt': f'JSON数据图片 ({path}.{key})',
                                                'width': '',
                                                'height': '',
                                                'original_src': value,
                                                'source': 'json'
                                            })
                                    elif isinstance(value, (dict, list)):
                                        find_images_in_json(value, f"{path}.{key}" if path else key)
                            elif isinstance(obj, list):
                                for i, item in enumerate(obj):
                                    find_images_in_json(item, f"{path}[{i}]")
                        
                        find_images_in_json(data)
                    except:
                        pass
            
            # 去重处理
            unique_images = []
            seen_urls = set()
            for img in images:
                if img['url'] not in seen_urls:
                    seen_urls.add(img['url'])
                    unique_images.append(img)
            
            return {
                'images': unique_images,
                'text_content': text_content
            }
            
        except requests.RequestException as e:
            return {'error': f'请求失败: {str(e)}'}
        except Exception as e:
            return {'error': f'解析失败: {str(e)}'}
    
    def validate_image_url(self, url, referer: str = None, cookie: str = None):
        """验证图片URL是否有效。
        优先使用 HEAD；若被拦截或无有效 Content-Type，则回退到 GET 的前几 KB。
        可传入 referer 以增加通过率（例如字节系 CDN 需要）。
        """
        headers = {}
        if referer:
            headers['Referer'] = referer
        if cookie:
            headers['Cookie'] = cookie
        try:
            # 优先 HEAD
            response = self.session.head(url, headers=headers, timeout=8, allow_redirects=True)
            content_type = (response.headers.get('content-type') or '').lower()
            if 'image' in content_type:
                return True
            # 某些站点不返回类型或拦截 HEAD，回退到 GET 少量数据
            response = self.session.get(url, headers=headers, timeout=8, stream=True)
            content_type = (response.headers.get('content-type') or '').lower()
            if 'image' in content_type:
                return True
            # 简单魔数判断（只读取前 512 字节）
            try:
                chunk = next(response.iter_content(chunk_size=512))
                is_image_signature = (
                    chunk.startswith(b'\xff\xd8\xff') or  # JPEG
                    chunk.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                    chunk.startswith(b'GIF87a') or chunk.startswith(b'GIF89a') or  # GIF
                    chunk.startswith(b'BM') or  # BMP
                    chunk.startswith(b'RIFF') or  # WEBP/AVI 容器（后续由 PIL 进一步判定）
                    chunk.startswith(b'\x00\x00\x01\x00')  # ICO
                )
                return bool(is_image_signature)
            except Exception:
                return False
        except Exception:
            return False
    
    def get_image_info(self, url, referer: str = None, cookie: str = None):
        """获取图片信息，支持传入 referer"""
        try:
            headers = {}
            if referer:
                headers['Referer'] = referer
            if cookie:
                headers['Cookie'] = cookie
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = response.headers.get('content-length', '0')
                
                # 尝试获取图片尺寸
                try:
                    img = Image.open(io.BytesIO(response.content))
                    width, height = img.size
                    return {
                        'valid': True,
                        'content_type': content_type,
                        'size': int(content_length),
                        'width': width,
                        'height': height,
                        'format': img.format
                    }
                except:
                    return {
                        'valid': True,
                        'content_type': content_type,
                        'size': int(content_length),
                        'width': 'unknown',
                        'height': 'unknown',
                        'format': 'unknown'
                    }
        except:
            return {'valid': False}

extractor = ContentExtractor()

@app.route('/')
def index():
    return render_template('preview.html')

@app.route('/test_images.html')
def test_images():
    with open('test_images.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/manual')
def manual():
    return render_template('manual.html')

@app.route('/collect_host')
def collect_host():
    # 一个本地小页面，用于跨站点 postMessage 回传链接
    return render_template('collect_host.html')

@app.route('/extract', methods=['POST'])
def extract_images():
    data = request.get_json()
    url = data.get('url', '').strip()
    cookie = data.get('cookie')
    debug = data.get('debug', False)
    
    if not url:
        return jsonify({'error': '请输入URL'})
    
    # 添加协议前缀
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # 提取内容和图片
    result = extractor.extract_images_from_url(url, cookie=cookie)
    
    if 'error' in result:
        return jsonify(result)
    
    # 验证图片并获取信息
    validated_images = []
    for img in result['images']:
        if extractor.validate_image_url(img['url'], referer=url, cookie=cookie):
            info = extractor.get_image_info(img['url'], referer=url, cookie=cookie)
            img.update(info)
            validated_images.append(img)
    
    response_data = {
        'success': True,
        'url': url,
        'total_found': len(result['images']),
        'valid_images': len(validated_images),
        'images': validated_images,
        'text_content': result['text_content']
    }
    
    # 如果启用调试模式，添加调试信息
    if debug:
        try:
            response = extractor.session.get(url, timeout=10)
            # 使用相同的内容处理逻辑
            content = response.content
            if response.encoding:
                try:
                    content = content.decode(response.encoding)
                except:
                    content = content.decode('utf-8', errors='ignore')
            else:
                content = content.decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(content, 'html.parser')
            response_data['debug'] = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'encoding': response.encoding,
                'title': soup.title.string if soup.title else 'No title',
                'img_tags_count': len(soup.find_all('img')),
                'has_scripts': len(soup.find_all('script')) > 0,
                'sample_html': str(soup)[:1000] + '...' if len(str(soup)) > 1000 else str(soup)
            }
        except Exception as e:
            response_data['debug'] = {'error': str(e)}
    
    return jsonify(response_data)

@app.route('/download/<path:image_url>')
def download_image(image_url):
    """下载图片"""
    try:
        response = extractor.session.get(image_url, timeout=10)
        response.raise_for_status()
        
        # 获取文件名
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = 'image.jpg'
        
        return send_file(
            io.BytesIO(response.content),
            as_attachment=True,
            download_name=filename,
            mimetype=response.headers.get('content-type', 'image/jpeg')
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 400


# —— 手动模式：回传收集 ——
@app.route('/collect', methods=['GET', 'POST'])
@app.route('/collect.gif', methods=['GET', 'POST'])
def collect_link():
    try:
        url = request.args.get('u') or (request.get_json(silent=True) or {}).get('url') or request.form.get('url')
        referer = request.headers.get('Referer') or request.args.get('ref')
        if not url:
            # 返回 1x1 gif 透明像素
            pixel = base64.b64decode('R0lGODlhAQABAPAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==')
            return send_file(io.BytesIO(pixel), mimetype='image/gif')

        item = {
            'url': url,
            'referer': referer or '',
            'ts': datetime.utcnow().isoformat() + 'Z'
        }
        # 去重
        if not any(x['url'] == url for x in collected_links):
            collected_links.append(item)

        # 作为像素返回，便于 bookmarklet 用 <img> 方式上报
        pixel = base64.b64decode('R0lGODlhAQABAPAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==')
        return send_file(io.BytesIO(pixel), mimetype='image/gif')
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/collected', methods=['GET'])
def list_collected():
    return jsonify({'count': len(collected_links), 'items': collected_links})


@app.route('/collected/view')
def view_collected():
    # 简单可视化页面
    html = [
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>已收集图片链接</title>',
        '<style>body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial;padding:20px} .url{word-break:break-all;color:#2563eb} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px} .card{border:1px solid #e5e7eb;border-radius:10px;padding:12px} img{max-width:100%;height:180px;object-fit:contain;background:#f3f4f6}</style>',
        '</head><body>'
    ]
    html.append(f'<h2>已收集 {len(collected_links)} 张图片</h2>')
    html.append('<p><a href="/collected" target="_blank">查看 JSON</a></p>')
    html.append('<div class="grid">')
    for it in collected_links:
        url = it['url']
        html.append(f'<div class="card"><div><img src="{url}" onerror="this.style.display=\'none\'"/></div><div class="url">{url}</div></div>')
    html.append('</div></body></html>')
    return ''.join(html)


@app.route('/preview')
def preview_markdown():
    return render_template('preview.html')

@app.route('/preview_simple')
def preview_simple():
    return render_template('preview_simple.html')


@app.route('/extract_rendered', methods=['POST'])
def extract_images_rendered():
    data = request.get_json()
    url = data.get('url', '').strip()
    max_scrolls = int(data.get('maxScrolls', 30))
    scroll_pause_ms = int(data.get('scrollPauseMs', 700))
    timeout_ms = int(data.get('timeoutMs', 45000))
    wait_until = data.get('waitUntil', 'networkidle')  # or 'domcontentloaded'
    debug = bool(data.get('debug', False))
    cookie = data.get('cookie')

    if not url:
        return jsonify({'error': '请输入URL'})

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        # 延迟导入，避免未安装时报错阻断其他接口
        from playwright.sync_api import sync_playwright

        collected_urls = set()
        saved_local_urls = set()

        # 确保本地保存目录存在
        static_dir = Path('static') / 'captured'
        static_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            extra_headers = {
                'Accept-Language': extractor.session.headers.get('Accept-Language', 'zh-CN,zh;q=0.9'),
                'Referer': url
            }
            if cookie:
                extra_headers['Cookie'] = cookie
            context = browser.new_context(
                user_agent=extractor.session.headers.get('User-Agent'),
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                extra_http_headers=extra_headers
            )

            page = context.new_page()
            try:
                page.set_default_navigation_timeout(timeout_ms)
            except Exception:
                pass

            # 监听网络响应，收集图片；必要时直接保存响应体到本地以避免二次请求失败
            def on_response(response):
                try:
                    ct = (response.headers.get('content-type') or '').lower()
                    url_ = response.url
                    # 1) content-type 指示为 image
                    if 'image' in ct or response.request.resource_type == 'image':
                        try:
                            body = response.body()
                            # 文件扩展名
                            ext = 'jpg'
                            if 'png' in ct:
                                ext = 'png'
                            elif 'gif' in ct:
                                ext = 'gif'
                            elif 'webp' in ct:
                                ext = 'webp'
                            elif 'svg' in ct:
                                ext = 'svg'
                            elif 'bmp' in ct:
                                ext = 'bmp'
                            # 内容哈希去重
                            h = hashlib.sha256(body).hexdigest()[:16]
                            filename = f"{h}.{ext}"
                            file_path = static_dir / filename
                            if not file_path.exists():
                                file_path.write_bytes(body)
                            local_url = f"/static/captured/{filename}"
                            collected_urls.add(local_url)
                            saved_local_urls.add(local_url)
                            return
                        except Exception:
                            collected_urls.add(url_)
                            return
                    # 2) URL 后缀或域名特征判断（字节系 byteimg CDN 等）
                    if url_:
                        lower = url_.split('?')[0].lower()
                        if any(lower.endswith(ext) for ext in ['.jpg','.jpeg','.png','.gif','.webp','.svg','.bmp','.ico','.tiff']):
                            try:
                                body = response.body()
                                # 推断扩展
                                ext = lower.rsplit('.', 1)[-1]
                                if ext not in ['jpg','jpeg','png','gif','webp','svg','bmp','ico','tiff']:
                                    ext = 'jpg'
                                h = hashlib.sha256(body).hexdigest()[:16]
                                filename = f"{h}.{ext}"
                                file_path = static_dir / filename
                                if not file_path.exists():
                                    file_path.write_bytes(body)
                                local_url = f"/static/captured/{filename}"
                                collected_urls.add(local_url)
                                saved_local_urls.add(local_url)
                                return
                            except Exception:
                                collected_urls.add(url_)
                                return
                        if 'byteimg.com' in lower or 'doubao' in lower:
                            try:
                                body = response.body()
                                h = hashlib.sha256(body).hexdigest()[:16]
                                # 尝试从 content-type 推断扩展
                                ext = 'jpg'
                                if 'png' in ct:
                                    ext = 'png'
                                elif 'gif' in ct:
                                    ext = 'gif'
                                elif 'webp' in ct:
                                    ext = 'webp'
                                filename = f"{h}.{ext}"
                                file_path = static_dir / filename
                                if not file_path.exists():
                                    file_path.write_bytes(body)
                                local_url = f"/static/captured/{filename}"
                                collected_urls.add(local_url)
                                saved_local_urls.add(local_url)
                                return
                            except Exception:
                                collected_urls.add(url_)
                                return
                except Exception:
                    pass

            page.on('response', on_response)

            # 更稳健的导航：先按用户指定策略；失败则回退到 domcontentloaded，然后尽量等待一次 networkidle
            try:
                page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            except Exception:
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
                except Exception:
                    pass
            try:
                page.wait_for_load_state('networkidle', timeout=min(8000, timeout_ms))
            except Exception:
                pass

            # 尝试点击“加载更多/查看更多/展开”等按钮，帮助触发更多内容加载
            try:
                for _ in range(5):
                    candidates = page.locator("text=/加载更多|查看更多|更多|展开|Load more|More|Show more/i")
                    count = candidates.count()
                    if count == 0:
                        break
                    # 逐个点击可见按钮
                    for i in range(min(count, 3)):
                        try:
                            candidates.nth(i).click(timeout=1500)
                            time.sleep(0.5)
                        except Exception:
                            pass
                    try:
                        page.wait_for_load_state('networkidle', timeout=3000)
                    except Exception:
                        pass
            except Exception:
                pass

            # 自动滚动，触发懒加载
            last_height = 0
            same_count = 0
            for _ in range(max_scrolls):
                page.evaluate('window.scrollBy(0, Math.max(600, window.innerHeight));')
                time.sleep(scroll_pause_ms / 1000.0)
                height = page.evaluate('document.body.scrollHeight')
                if height == last_height:
                    same_count += 1
                    if same_count >= 2:
                        break
                else:
                    same_count = 0
                last_height = height
                try:
                    page.wait_for_load_state('networkidle', timeout=2500)
                except Exception:
                    pass

            # 将可能懒加载的图片元素滚动进视口，触发加载
            try:
                page.evaluate("""
                    () => {
                      const lazyAttrs = ['data-src','data-original','data-lazy-src','data-url','data-image','data-img'];
                      const nodes = Array.from(document.querySelectorAll('img, [data-src], [data-original], [data-lazy-src]'));
                      nodes.forEach(el => { try { el.scrollIntoView({behavior:'instant', block:'center'}); } catch(e){} });
                    }
                """)
                try:
                    page.wait_for_load_state('networkidle', timeout=3000)
                except Exception:
                    pass
            except Exception:
                pass

            # DOM 扫描：img/srcset/picture/source、video.poster、计算样式背景图，以及文字内容
            dom_data = page.evaluate("""
                () => {
                  const urls = new Set();
                  const abs = (u) => {
                    try { return new URL(u, location.href).href } catch { return null }
                  };

                  // img
                  document.querySelectorAll('img').forEach(img => {
                    // 使用 currentSrc 能拿到浏览器选择的实际资源
                    if (img.currentSrc) {
                      const a = abs(img.currentSrc);
                      if (a) urls.add(a);
                    }
                    const candidates = [img.getAttribute('src'), img.getAttribute('data-src'), img.getAttribute('data-lazy-src'), img.getAttribute('data-original')]
                      .filter(Boolean);
                    candidates.forEach(u => { const a = abs(u); if (a) urls.add(a); });
                  });

                  // picture/source srcset
                  document.querySelectorAll('source, img').forEach(el => {
                    const srcset = el.getAttribute('srcset') || el.getAttribute('data-srcset');
                    if (srcset) {
                      srcset.split(',').map(s => s.trim().split(' ')[0]).forEach(u => { const a = abs(u); if (a) urls.add(a); });
                    }
                  });

                  // video poster
                  document.querySelectorAll('video[poster]').forEach(v => { const a = abs(v.getAttribute('poster')); if (a) urls.add(a); });

                  // 计算样式背景图
                  Array.from(document.querySelectorAll('*')).forEach(el => {
                    const bg = getComputedStyle(el).backgroundImage;
                    if (bg && bg.includes('url(')) {
                      const m = bg.match(/url\(("|')?([^"')]+)\1?\)/gi) || [];
                      m.forEach(item => {
                        const u = item.replace(/url\(("|')?/, '').replace(/\1?\)/, '').replace(/url\(|\)|"|'/g, '');
                        const a = abs(u);
                        if (a && !a.startsWith('data:')) urls.add(a);
                      });
                    }
                  });

                  // meta og:image
                  document.querySelectorAll('meta[property="og:image"], meta[property="og:image:url"], meta[name="twitter:image"], meta[itemprop="image"]').forEach(m => {
                    const a = abs(m.getAttribute('content'));
                    if (a) urls.add(a);
                  });

                  // preload as=image
                  document.querySelectorAll('link[rel="preload"][as="image"]').forEach(l => { const a = abs(l.getAttribute('href')); if (a) urls.add(a); });

                  // 提取文字内容
                  const textContent = {
                    title: document.title || '',
                    headings: [],
                    paragraphs: [],
                    lists: [],
                    links: [],
                    full_text: ''
                  };

                  // 提取标题
                  document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
                    const text = heading.textContent.trim();
                    if (text) {
                      textContent.headings.push({
                        level: heading.tagName.toLowerCase(),
                        text: text
                      });
                    }
                  });

                  // 提取段落
                  document.querySelectorAll('p').forEach(p => {
                    const text = p.textContent.trim();
                    if (text && text.length > 10) {
                      textContent.paragraphs.push(text);
                    }
                  });

                  // 提取列表
                  document.querySelectorAll('ul, ol').forEach(list => {
                    const items = [];
                    list.querySelectorAll('li').forEach(li => {
                      const text = li.textContent.trim();
                      if (text) items.push(text);
                    });
                    if (items.length > 0) {
                      textContent.lists.push({
                        type: list.tagName.toLowerCase(),
                        items: items
                      });
                    }
                  });

                  // 提取链接
                  document.querySelectorAll('a[href]').forEach(link => {
                    const text = link.textContent.trim();
                    const href = link.getAttribute('href');
                    if (text && href) {
                      const absoluteUrl = abs(href);
                      if (absoluteUrl) {
                        textContent.links.push({
                          text: text,
                          url: absoluteUrl
                        });
                      }
                    }
                  });

                  // 提取完整文本
                  const body = document.body;
                  if (body) {
                    // 移除脚本和样式元素
                    const clone = body.cloneNode(true);
                    clone.querySelectorAll('script, style, nav, header, footer, aside').forEach(el => el.remove());
                    textContent.full_text = clone.textContent || '';
                  }

                  return {
                    urls: Array.from(urls),
                    textContent: textContent
                  };
                }
            """)

            for u in dom_data['urls']:
                collected_urls.add(u)

            # 验证与获取信息
            validated_images = []
            for img_url in collected_urls:
                if extractor.validate_image_url(img_url, referer=url, cookie=cookie):
                    info = extractor.get_image_info(img_url, referer=url, cookie=cookie)
                    img = {'url': img_url}
                    img.update(info)
                    validated_images.append(img)

            response_data = {
                'success': True,
                'url': url,
                'total_found': len(collected_urls),
                'valid_images': len(validated_images),
                'images': validated_images,
                'text_content': dom_data['textContent']
            }

            if debug:
                response_data['debug'] = {
                    'collected_urls_sample': list(collected_urls)[:10],
                    'dom_count': len(dom_data['urls'])
                }

            context.close()
            browser.close()

            return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': f'渲染模式失败: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

