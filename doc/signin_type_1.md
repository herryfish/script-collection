# 微信小程序自动签到脚本

## 功能描述

本脚本实现了微信小程序的自动登录和签到功能。主要特点：

- 支持多个微信小程序的自动签到（已知支持：LaLa station、鑫耀光环等）
- 支持多账号配置
- 自动处理登录令牌
- 完整的错误处理和日志记录
- 支持消息通知
- 支持从环境变量加载配置（适合容器化部署）

## 环境要求

- Python 3.x
- 依赖包：
  - requests
  - loguru
  - pyyaml
  - brotli（用于处理小程序的brotli压缩）

## 配置说明

### 配置文件

配置文件位于 `config/app_config.yaml`，需要根据示例配置文件 `app_config.yaml.sample` 进行配置：

```yaml
common:
  # 青龙服务器配置
  qinglong:
    host: localhost:5700
    client_id: XXXXXXXXXXXXXXXXXXXX
    client_secret: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
  # redis配置
  redis:
    host: redis配置

# 微信小程序自动签到配置文件
signin_type_1:
  app_configs:
    lalastation:  # 应用标识
      host: sjwx.lalastation-lh.com  # 应用域名
      app_secret: AE859F714A309237   # 应用密钥
      headers:    # 应用特定的请求头
        buildingid: ST0002
        Referer: https://servicewechat.com/wx136aced7fd0686b2/34/page-frame.html
  user_infos:
    - {app: lalastation, openid: XXXXXXXXXXXXXXXXXXXXXXXXXX}  # 用户配置
```

### 配置项说明

1. `common`: 通用配置
   - `qinglong`: 青龙面板配置（用于环境变量管理）
   - `redis`: Redis配置（可选）

2. `app_configs`: 配置各个小程序应用的信息
   - `host`: 应用服务器域名
   - `app_secret`: 应用密钥
   - `headers`: 应用特定的请求头信息

3. `user_infos`: 配置用户账号信息
   - `app`: 对应的应用标识
   - `openid`: 用户的OpenID（从小程序获取）

### 环境变量配置

除了YAML文件外，脚本还支持从环境变量加载配置。环境变量名称使用双下划线 `__` 分隔层级结构，例如：

```
SIGNIN_TYPE_1__APP_CONFIGS__LALASTATION__HOST=sjwx.lalastation-lh.com
SIGNIN_TYPE_1__APP_CONFIGS__LALASTATION__APP_SECRET=AE859F714A309237
SIGNIN_TYPE_1__USER_INFOS__0__APP=lalastation
SIGNIN_TYPE_1__USER_INFOS__0__OPENID=XXXXXXXXXXXXXXXXXXXXXXXXXX
```

这种配置方式特别适合容器化部署环境。

## 使用方法

### 方法一：使用配置文件

1. 复制配置文件示例并修改：
   ```bash
   cp config/app_config.yaml.sample config/app_config.yaml
   ```

2. 修改配置文件，填入正确的配置信息：
   - 设置正确的 host 和 app_secret
   - 配置正确的请求头信息
   - 填入用户的 OpenID

3. 运行脚本：
   ```bash
   python scripts/signin_type_1.py
   ```

### 方法二：使用环境变量

1. 设置必要的环境变量：
   ```bash
   export SIGNIN_TYPE_1__APP_CONFIGS__LALASTATION__HOST=sjwx.lalastation-lh.com
   export SIGNIN_TYPE_1__APP_CONFIGS__LALASTATION__APP_SECRET=AE859F714A309237
   # 设置其他必要的环境变量...
   ```

2. 运行脚本：
   ```bash
   python scripts/signin_type_1.py
   ```

## 注意事项

1. 安全性
   - 请妥善保管配置文件，不要泄露 app_secret 和 OpenID
   - 建议将 `app_config.yaml` 加入 .gitignore
   - 在共享环境中使用环境变量而非配置文件

2. 运行频率
   - 脚本在每个账号签到之间有1秒延迟，建议不要过于频繁运行
   - 建议通过定时任务每天执行一次

3. 错误处理
   - 脚本会自动处理登录失败和签到失败的情况
   - 所有错误都会记录到日志文件
   - 可通过配置通知功能接收错误通知

## 日志说明

- 使用 loguru 进行日志记录
- 记录内容包括：
  - 登录请求参数和结果
  - 签到结果
  - 错误信息

## 消息通知

脚本支持通过 `notify` 模块发送消息通知。当登录或签到失败时，会自动发送通知。

要启用通知功能，需要安装 `notify` 模块并进行相应配置。

## 常见问题

1. 登录失败
   - 检查 OpenID 是否正确
   - 确认 app_secret 是否有效
   - 检查网络连接是否正常

2. 签到失败
   - 检查是否已经签到过
   - 确认账号状态是否正常
   - 查看日志获取详细错误信息

3. 配置加载问题
   - 检查配置文件格式是否正确
   - 确认环境变量名称格式是否符合要求
   - 使用绝对路径指定配置文件位置

## 扩展支持

如需添加新的微信小程序支持，可以通过以下步骤：

1. 在配置文件的 `app_configs` 部分添加新应用的配置
2. 在 `user_infos` 部分添加对应的用户信息
3. 如果新应用的登录或签到逻辑与现有逻辑不同，可能需要扩展 `AppBase` 类

## 贡献

欢迎提交问题报告和改进建议。
