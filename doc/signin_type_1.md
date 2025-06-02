# 微信小程序自动签到脚本

## 功能说明

本脚本用于自动完成微信小程序的签到操作。目前支持的应用包括：
- 应用A的每日签到
- 应用B的积分签到
- 更多应用支持开发中...

## 配置说明

配置文件支持两种方式：
1. YAML文件配置（默认）
2. 环境变量配置

### YAML文件配置

在 `config/app_config.yaml` 中配置以下信息：

```yaml
# 通用配置
common:
  # 青龙面板配置
  qinglong:
    host: localhost:5700
    client_id: your_client_id
    client_secret: your_client_secret
  # Redis配置（可选）
  redis:
    host: localhost
    port: 6379
    password: your_password
    db: 0

# 应用配置
app_configs:
  app_name_1:
    api_url: https://api.example.com
    login_path: /login
    signin_path: /signin
  app_name_2:
    api_url: https://api.another.com
    login_path: /auth
    signin_path: /daily-check

# 用户信息
user_infos:
  - username: user1
    password: pass1
    apps:
      - app_name_1
      - app_name_2
  - username: user2
    password: pass2
    apps:
      - app_name_1
```

### 环境变量配置

也可以使用环境变量进行配置，环境变量名使用双下划线（`__`）分隔层级：

```bash
# 通用配置
COMMON__QINGLONG__HOST=localhost:5700
COMMON__QINGLONG__CLIENT_ID=your_client_id
COMMON__QINGLONG__CLIENT_SECRET=your_client_secret

# Redis配置（可选）
COMMON__REDIS__HOST=localhost
COMMON__REDIS__PORT=6379
COMMON__REDIS__PASSWORD=your_password
COMMON__REDIS__DB=0

# 应用配置
APP_CONFIGS__APP_NAME_1__API_URL=https://api.example.com
APP_CONFIGS__APP_NAME_1__LOGIN_PATH=/login
APP_CONFIGS__APP_NAME_1__SIGNIN_PATH=/signin

# 用户信息
USER_INFOS__0__USERNAME=user1
USER_INFOS__0__PASSWORD=pass1
USER_INFOS__0__APPS__0=app_name_1
USER_INFOS__0__APPS__1=app_name_2
```

## 使用方法

1. 复制配置文件模板并修改：
```bash
cp config/app_config.yaml.sample config/app_config.yaml
```

2. 编辑配置文件，填入实际的配置信息

3. 运行脚本：
```bash
python scripts/signin_type_1.py
```

## 注意事项

1. 请确保配置文件中的敏感信息安全
2. 建议使用环境变量方式配置敏感信息
3. 如遇到签到失败，请检查：
   - 配置信息是否正确
   - 网络连接是否正常
   - 账号密码是否有效

## 常见问题

1. 如何查看运行日志？
   - 日志文件位于 `logs/signin_type_1.log`

2. 如何配置定时任务？
   - 在青龙面板中添加定时任务
   - 建议的定时规则：`0 8 * * *`（每天早上8点执行）

3. 如何扩展支持新的应用？
   - 在配置文件中添加新应用的配置信息
   - 在脚本中实现对应的登录和签到逻辑