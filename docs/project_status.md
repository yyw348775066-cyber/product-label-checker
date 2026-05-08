# 当前项目状态

## 项目名称
产品标签审核对比工具

## 当前技术栈
- Flask
- HTML
- CSS
- JavaScript
- pytest

## 当前已完成功能

### 基础功能
- 上传标签图片
- 五个平台AI结果输入
- 字段对比表
- 差异判断
- 风险高亮
- 审核汇总
- CSV导出
- 人工备注
- 最终审核结论

### AI平台
- ChatGPT
- DeepSeek
- 通义千问
- 豆包
- 文心一言

### 第三方检验报告审核
- 报告文件上传
- 五平台AI结果输入
- 报告字段对比表
- CMA/CNAS资质结论
- 风险提示
- 人工备注
- 最终审核结论

### 已优化
- 紧凑文本字段提取
- 执行标准空格标准化
- 风险提示自动分段
- 单元格级差异高亮
- 响应式布局
- textarea粘贴风险提示自动补编号

## 当前项目结构

- app.py
- templates/index.html
- tests/
- data/real_cases/

## 当前开发原则

- 不重构项目
- 小步迭代
- 优先真实案例验证
- 不新增复杂依赖

### DeepSeek 网页辅助功能（MVP）
- Playwright 已接入
- Chromium 浏览器已安装
- DeepSeek 持久化浏览器环境已跑通
- 支持保存登录态
- Flask 可启动 DeepSeek 浏览器脚本
- 已验证“打开 DeepSeek”流程

### 当前 DeepSeek 使用流程
1. 在审核工具中上传标签/报告
2. 点击“打开 DeepSeek”
3. DeepSeek 浏览器自动打开
4. 手动上传对应文件
5. 点击“复制提示词”
6. 在 DeepSeek 中粘贴并发送
7. 将回答复制回对应 textarea
8. 生成对比表