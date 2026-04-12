"""Scalar 文档页面 UI 组件（HTML / CSS / JS 常量）"""


DOCS_CAPTCHA_PANEL_HTML = """
<div id="scalar-captcha-panel" aria-live="polite" hidden>
  <div class="scalar-captcha-panel__header" id="scalar-captcha-drag-handle">
    <div>
      <div class="scalar-captcha-panel__title">验证码预览</div>
      <div class="scalar-captcha-panel__desc">调用 <code>GET /auth/captcha</code> 后，最新验证码会显示在这里，方便继续调登录接口。</div>
    </div>
    <button id="scalar-captcha-close" type="button" aria-label="关闭验证码预览">×</button>
  </div>
  <div class="scalar-captcha-panel__image-wrap">
    <img id="scalar-captcha-image" alt="验证码预览" />
  </div>
  <div id="scalar-captcha-id" class="scalar-captcha-panel__meta"></div>
  <div class="scalar-captcha-panel__hint">登录时把上面图片里的字符填到 <code>captchaCode</code>，把返回的 <code>captchaId</code> 填到登录参数中。</div>
</div>
"""

DOCS_CAPTCHA_PANEL_SCRIPT = """
<script>
(() => {
  const CAPTCHA_PANEL_ID = 'scalar-captcha-panel';
  const CAPTCHA_IMAGE_ID = 'scalar-captcha-image';
  const CAPTCHA_META_ID = 'scalar-captcha-id';

  const isCaptchaRequest = (rawUrl) => {
    try {
      const url = new URL(rawUrl, window.location.origin);
      return url.origin === window.location.origin && url.pathname === '/auth/captcha';
    } catch {
      return false;
    }
  };

  const showCaptchaPanel = (payload) => {
    const panel = document.getElementById(CAPTCHA_PANEL_ID);
    const image = document.getElementById(CAPTCHA_IMAGE_ID);
    const meta = document.getElementById(CAPTCHA_META_ID);
    if (!panel || !image || !meta) return;

    const data = payload?.data ?? {};
    const captchaId = data.captchaId || '';
    const svg = data.captchaSvg || '';
    if (!captchaId || !svg) return;

    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    meta.textContent = `captchaId: ${captchaId}`;
    panel.style.zIndex = '2147483647';
    panel.hidden = false;
  };

  const tryHandleCaptchaResponse = async (rawUrl, response) => {
    if (!isCaptchaRequest(rawUrl)) return;
    try {
      const cloned = response.clone();
      const contentType = cloned.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) return;
      const payload = await cloned.json();
      showCaptchaPanel(payload);
    } catch {}
  };

  const mountPanelEvents = () => {
    const closeButton = document.getElementById('scalar-captcha-close');
    const panel = document.getElementById(CAPTCHA_PANEL_ID);
    if (!closeButton || !panel) return;
    closeButton.addEventListener('click', () => {
      panel.hidden = true;
    });
  };

  const initDrag = () => {
    const panel = document.getElementById(CAPTCHA_PANEL_ID);
    const handle = document.getElementById('scalar-captcha-drag-handle');
    if (!panel || !handle) return;

    let isDragging = false;
    let offsetX = 0, offsetY = 0;

    handle.style.cursor = 'grab';

    handle.addEventListener('mousedown', (e) => {
      if (e.target.closest('#scalar-captcha-close')) return;
      isDragging = true;
      panel.style.zIndex = '2147483647';
      handle.style.cursor = 'grabbing';
      const rect = panel.getBoundingClientRect();
      offsetX = e.clientX - rect.left;
      offsetY = e.clientY - rect.top;
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      let newX = e.clientX - offsetX;
      let newY = e.clientY - offsetY;
      newX = Math.max(0, Math.min(newX, window.innerWidth - panel.offsetWidth));
      newY = Math.max(0, Math.min(newY, window.innerHeight - panel.offsetHeight));
      panel.right = 'auto';
      panel.bottom = 'auto';
      panel.left = newX + 'px';
      panel.top = newY + 'px';
    });

    document.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        handle.style.cursor = 'grab';
      }
    });
  };

  const patchFetch = () => {
    if (window.__scalarCaptchaFetchPatched) return;
    window.__scalarCaptchaFetchPatched = true;
    const originalFetch = window.fetch.bind(window);

    window.fetch = async (input, init) => {
      const requestUrl = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input);
      const response = await originalFetch(input, init);
      await tryHandleCaptchaResponse(requestUrl, response);
      return response;
    };
  };

  const patchXHR = () => {
    if (window.__scalarCaptchaXHRPatched) return;
    window.__scalarCaptchaXHRPatched = true;

    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
      this.__scalarDocsUrl = url;
      return originalOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function(body) {
      this.addEventListener('load', () => {
        if (!isCaptchaRequest(this.__scalarDocsUrl || '')) return;
        try {
          const contentType = this.getResponseHeader('content-type') || '';
          if (!contentType.includes('application/json')) return;
          showCaptchaPanel(JSON.parse(this.responseText));
        } catch {}
      }, { once: true });
      return originalSend.call(this, body);
    };
  };

  const init = () => {
    mountPanelEvents();
    patchFetch();
    patchXHR();
    initDrag();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
</script>
"""

DOCS_CAPTCHA_PANEL_STYLE = """
<style>
#scalar-captcha-panel {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 2147483647;
  width: min(420px, calc(100vw - 32px));
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
  padding: 14px;
  color: #0f172a;
  font-family: Inter, system-ui, sans-serif;
}

#scalar-captcha-panel code {
  font-family: "JetBrains Mono", Consolas, monospace;
}

.scalar-captcha-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  cursor: grab;
}

.scalar-captcha-panel__header:active {
  cursor: grabbing;
}

.scalar-captcha-panel__title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}

.scalar-captcha-panel__desc {
  font-size: 13px;
  line-height: 1.5;
  color: #475569;
}

#scalar-captcha-close {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.scalar-captcha-panel__image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
}

.scalar-captcha-panel__image-wrap img {
  max-width: 100%;
  height: auto;
  display: block;
}

.scalar-captcha-panel__meta {
  font-size: 12px;
  color: #0f172a;
  font-family: "JetBrains Mono", Consolas, monospace;
  margin-bottom: 8px;
}

.scalar-captcha-panel__hint {
  font-size: 12px;
  line-height: 1.5;
  color: #334155;
}
</style>
"""

DOCS_DOWNLOAD_BTN_HTML = """
<div id="scalar-docs-download-bar" style="position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:2147483647;display:flex;gap:8px;">
  <a href="/docs/download?format=md" target="_blank"
     style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;border-radius:8px;border:1px solid #e2e8f0;background:#fff;color:#334155;font-size:13px;font-family:Inter,system-ui,sans-serif;text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:all .15s;"
     onmouseover="this.style.background='#f1f5f9';this.style.borderColor='#cbd5e1';"
     onmouseout="this.style.background='#fff';this.style.borderColor='#e2e8f0';">
    <span>&#x2B07;</span> <span>Download API Doc (MD)</span>
  </a>
</div>
"""
