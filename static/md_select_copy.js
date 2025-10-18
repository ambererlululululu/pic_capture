(function () {
  const TOAST = (m) => {
    try {
      const d = document.createElement('div');
      d.textContent = m;
      d.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);background:#000;color:#fff;padding:8px 14px;border-radius:6px;z-index:2147483647;font:14px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial';
      document.body.appendChild(d);
      setTimeout(() => d.remove(), 2200);
    } catch {}
  };

  const inter = (a, b) => !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
  const mid = (r) => ({ y: (r.top + r.bottom) / 2, x: (r.left + r.right) / 2 });

  async function copyText(s) {
    try {
      await navigator.clipboard.writeText(s);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = s;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
  }

  function exportSelection() {
    const sel = getSelection();
    if (!sel || !sel.rangeCount) {
      TOAST('请选择一段文字/图片');
      return;
    }
    const r = sel.getRangeAt(0);
    const SR = r.getBoundingClientRect();
    if (((SR.width | 0) == 0) && ((SR.height | 0) == 0)) {
      TOAST('选区矩形为空');
      return;
    }

    // 首选：用 cloneContents 精确保序（DOM 顺序 == 视觉阅读顺序）
    let out = [];
    try {
      const frag = r.cloneContents();
      const walker = document.createTreeWalker(
        frag,
        NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
        {
          acceptNode(node) {
            if (node.nodeType === 1 && ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(node.nodeName)) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          },
        }
      );

      let node;
      let buffer = '';
      const flushBuf = () => { if (buffer.trim()) { out.push(buffer.trim()); } buffer = ''; };
      while ((node = walker.nextNode())) {
        if (node.nodeType === 1 && node.nodeName === 'IMG') {
          const src = node.currentSrc || node.src || '';
          if (src && !/^data:image\/svg/i.test(src)) {
            flushBuf();
            out.push('![](' + src + ')');
          }
          continue;
        }
        if (node.nodeType === 3) {
          const t = (node.nodeValue || '').replace(/\s+/g, ' ').trim();
          if (t) buffer += (buffer ? ' ' : '') + t;
        }
      }
      flushBuf();
    } catch (e) {
      // 回退：使用几何排序
      const items = [];
      document.querySelectorAll('img').forEach((img) => {
        const br = img.getBoundingClientRect();
        if ((br.width || br.height) && inter(br, SR)) {
          const u = img.currentSrc || img.src || '';
          if (u && !/^data:image\/svg/i.test(u)) items.push({ t: 'img', c: u, m: mid(br) });
        }
      });
      const root = r.commonAncestorContainer.nodeType === 1 ? r.commonAncestorContainer : r.commonAncestorContainer.parentElement;
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode(n) {
          const v = (n.nodeValue || '').replace(/\s+/g, ' ').trim();
          if (!v) return NodeFilter.FILTER_REJECT;
          const rr = document.createRange();
          rr.selectNodeContents(n);
          for (const q of rr.getClientRects()) if (inter(q, SR)) return NodeFilter.FILTER_ACCEPT;
          return NodeFilter.FILTER_REJECT;
        },
      });
      let n;
      while ((n = w.nextNode())) {
        const rr = document.createRange();
        rr.selectNodeContents(n);
        const txt = (n.nodeValue || '').replace(/\s+/g, ' ').trim();
        if (!txt) continue;
        for (const q of rr.getClientRects()) {
          if (inter(q, SR)) {
            items.push({ t: 'txt', c: txt, m: mid(q) });
          }
        }
      }
      if (!items.length) {
       TOAST('选区内未检测到文本/图片');
       return;
      }
      items.sort((a, b) => (a.m.y !== b.m.y ? a.m.y - b.m.y : a.m.x - b.m.x));
      const rowTh = 20;
      const grouped = [];
      items.forEach((it) => {
        const g = grouped[grouped.length - 1];
        if (g && Math.abs(g.y - it.m.y) < rowTh) g.list.push(it);
        else grouped.push({ y: it.m.y, list: [it] });
      });
      let buf = '';
      const flush = () => { if (buf) { out.push(buf); buf = ''; } };
      for (const g of grouped) {
        for (const it of g.list) {
          if (it.t === 'txt') buf += (buf ? ' ' : '') + it.c;
          else { flush(); out.push('![](' + it.c + ')'); }
        }
        flush();
      }
    }
    const md = out.join('\n\n') + '\n';
    copyText(md).then(() => TOAST('已复制（Cmd/Ctrl+V粘贴）'));
    alert('完整内容：\n\n' + md);
  }

  // 热键：Mac Cmd+Shift+M / Win Ctrl+Shift+M
  if (!window.__md_sel_handler__) {
    window.__md_sel_handler__ = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'M' || e.key === 'm')) {
        e.preventDefault();
        exportSelection();
      }
    };
    document.addEventListener('keydown', window.__md_sel_handler__);
    TOAST('已就绪：选中 → Cmd/Ctrl+Shift+M 导出并复制');
  } else {
    TOAST('已激活：选中 → Cmd/Ctrl+Shift+M');
  }
})();


