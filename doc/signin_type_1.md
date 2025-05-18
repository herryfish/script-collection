# 微信小程序自动签到脚本

## 功能描述

本脚本实现了微信小程序的自动登录和签到功能。主要特点：

- 支持多个微信小程序的自动签到
- 支持多账号配置
- 自动处理登录令牌
- 完整的错误处理和日志记录
- 支持消息通知

## 环境要求

- Python 3.x
- 依赖包：
  - requests
  - loguru
  - brotli（用于处理小程序的brotli压缩）

## 配置说明

### 配置文件

配置文件位于 `config/app_config.yaml`，需要根据示例配置文件 `app_config.yaml.sample` 进行配置：

```yaml
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

1. `app_configs`: 配置各个小程序应用的信息
   - `host`: 应用服务器域名
   - `app_secret`: 应用密钥
   - `headers`: 应用特定的请求头信息

2. `user_infos`: 配置用户账号信息
   - `app`: 对应的应用标识
   - `openid`: 用户的OpenID（从小程序获取）

## 使用方法

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

## 注意事项

1. 安全性
   - 请妥善保管配置文件，不要泄露 app_secret 和 OpenID
   - 建议将 `app_config.yaml` 加入 .gitignore

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

## 常见问题

1. 登录失败
   - 检查 OpenID 是否正确
   - 确认 app_secret 是否有效
   - 检查网络连接是否正常

2. 签到失败
   - 检查是否已经签到过
   - 确认请求头配置是否正确
   - 查看日志了解具体错误原因

## 代码维护

- 代码遵循 PEP 8 规范
- 使用类型注解提高代码可读性
- 详细的函数文档说明
- 模块化设计，便于扩展