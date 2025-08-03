## 🔍 Google API 密钥配置

!!! note
    本节为可选内容。当搜索多次尝试返回 429 错误时，可使用官方 Google API。要使用 `google_official_search` 命令，你需要在环境变量中设置 Google API 密钥。

创建项目：

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)。
2. 如果还没有账号，请注册并登录。
3. 点击页面顶部的 *Select a Project* 下拉菜单，选择 *New Project* 创建新项目。
4. 为项目命名并点击 *Create*。
5. 设置自定义搜索 API 并在 `.env` 中添加：
    5. 前往 [APIs & Services Dashboard](https://console.cloud.google.com/apis/dashboard)
    6. 点击 *Enable APIs and Services*
    7. 搜索 *Custom Search API* 并点击进入
    8. 点击 *Enable*
    9. 转到 [Credentials](https://console.cloud.google.com/apis/credentials) 页面
    10. 点击 *Create Credentials*
    11. 选择 *API Key*
    12. 复制生成的 API 密钥
    13. 在 `.env` 文件中将其设置为 `GOOGLE_API_KEY`
14. [启用](https://console.developers.google.com/apis/api/customsearch.googleapis.com) 项目中的 Custom Search API（可能需要等待几分钟才能生效）。
    设置自定义搜索引擎并在 `.env` 中添加：
    15. 前往 [Custom Search Engine](https://cse.google.com/cse/all) 页面
    16. 点击 *Add*
    17. 按提示设置搜索引擎，你可以选择搜索整个网络或特定网站
    18. 创建完成后，点击 *Control Panel*
    19. 点击 *Basics*
    20. 复制 *Search engine ID*
    21. 在 `.env` 文件中将其设置为 `CUSTOM_SEARCH_ENGINE_ID`

_请记住，免费自定义搜索每日配额仅允许最多 100 次搜索。若想提升限额，需要为项目绑定结算账号，可获得每日最多 1 万次搜索。_

