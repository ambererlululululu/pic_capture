// api/proxy_image.js (Vercel Serverless / Next.js API 兼容)
// 用于代理小红书图片，绕过防盗链限制

export default async function handler(req, res) {
  try {
    const encoded = req.query.url || '';
    
    if (!encoded) {
      res.status(400).json({ error: 'missing url parameter' });
      return;
    }

    // 解码：浏览器用 btoa(encodeURIComponent(url))
    let raw;
    try {
      raw = decodeURIComponent(Buffer.from(encoded, 'base64').toString('utf8'));
    } catch (e) {
      // 兼容直接传 plain URL 的情况
      try {
        raw = decodeURIComponent(encoded);
      } catch (e2) {
        raw = encoded; // 如果都失败，直接使用
      }
    }

    let target = raw.trim();
    
    // 强制 https，解决 Mixed Content 问题
    if (target.startsWith('http://')) {
      target = target.replace(/^http:\/\//i, 'https://');
    }
    
    // 如果没有协议，添加 https://
    if (!target.startsWith('http://') && !target.startsWith('https://')) {
      target = 'https://' + target;
    }

    // 上游请求 headers：重要 —— 填上小红书期望的 Referer / UA
    const upstreamHeaders = {
      'Referer': 'https://www.xiaohongshu.com/',   // 小红书期望的 Referer
      'Origin': 'https://www.xiaohongshu.com',
      'User-Agent': req.headers['user-agent'] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      'Accept-Encoding': 'gzip, deflate, br',
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache',
      'Sec-Fetch-Dest': 'image',
      'Sec-Fetch-Mode': 'no-cors',
      'Sec-Fetch-Site': 'cross-site',
    };

    // 使用 fetch 请求上游图片
    // Node.js 18+ 原生支持 fetch，Vercel 环境也支持
    const upstreamResp = await fetch(target, {
      method: 'GET',
      headers: upstreamHeaders,
      redirect: 'follow', // 跟随重定向
    });

    if (!upstreamResp.ok) {
      // 把上游的状态码透传，便于调试
      console.error(`Proxy image failed: ${target}, status: ${upstreamResp.status}`);
      res.status(upstreamResp.status).json({ 
        error: `upstream ${upstreamResp.status}`,
        url: target 
      });
      return;
    }

    // 设置适当的缓存头和 CORS
    const contentType = upstreamResp.headers.get('content-type') || 'image/jpeg';
    res.setHeader('Content-Type', contentType);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    // 你可以根据业务设置更长的缓存，注意签名图片可能会过期
    res.setHeader('Cache-Control', 'public, max-age=86400, s-maxage=86400, immutable');

    // 获取图片数据并返回
    const buffer = await upstreamResp.arrayBuffer();
    res.status(200).send(Buffer.from(buffer));
    
  } catch (err) {
    console.error('proxy_image error:', err);
    res.status(500).json({ 
      error: 'proxy error: ' + (err.message || err),
      stack: process.env.NODE_ENV === 'development' ? err.stack : undefined
    });
  }
}

