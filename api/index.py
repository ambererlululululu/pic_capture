from app import app

# Vercel需要这个文件作为入口点
# 导出 app 对象供 Vercel 使用
handler = app
