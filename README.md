# Steam好友库存监控程序

自动监控Steam好友库存变化,并在检测到更新时发送手机通知。

## 功能特性

- ✅ 每分钟自动检查库存
- ✅ 检测新增、移除、数量变化的物品
- ✅ 支持多种手机推送服务
- ✅ 自动保存历史数据
- ✅ 支持公开和私密库存

## 使用步骤

### 1. 安装依赖

```bash
pip install requests schedule
```

如果需要访问私密库存,还需要安装:
```bash
pip install selenium
```

### 2. 获取Steam ID

访问你朋友的Steam个人资料页面,URL格式如下:
- `https://steamcommunity.com/profiles/76561198XXXXXXXXX/`
- 其中 `76561198XXXXXXXXX` 就是64位Steam ID

如果URL是自定义的(如 `/id/username/`),可以通过以下网站转换:
- https://steamid.io/

### 3. 选择推送服务(三选一)

#### 方案1: PushPlus (推荐,免费)
1. 访问 http://www.pushplus.plus/
2. 微信扫码登录
3. 复制你的token
4. 在代码中设置 `PUSH_TOKEN`

#### 方案2: Server酱 (备选)
1. 访问 https://sct.ftqq.com/
2. 微信登录
3. 获取SendKey
4. 在代码中修改推送函数为 `send_serverchan`

#### 方案3: Bark (iOS用户)
1. AppStore下载 Bark
2. 获取设备密钥
3. 在代码中修改推送函数为 `send_bark`

### 4. 配置程序

打开 `steam_inventory_monitor.py`,修改配置区域:

```python
# 必填: 好友的Steam ID
STEAM_ID = "76561198XXXXXXXXX"

# 必填: 推送服务Token
PUSH_TOKEN = "your_push_token_here"
```

### 5. 运行程序

```bash
python steam_inventory_monitor.py
```

程序将持续运行,每分钟检查一次库存。

## 配置说明

### 监控不同游戏

默认监控CS:GO库存,如需监控其他游戏,修改 `app_id`:

```python
# 在 check_inventory() 方法中修改
current_inventory = self.get_inventory_by_api(app_id=440)  # TF2

# 常见游戏ID:
# 730 - CS:GO
# 440 - Team Fortress 2
# 570 - Dota 2
# 753 - Steam (卡片、背景等)
```

### 修改检查频率

```python
# 在 start_monitoring() 方法中修改
schedule.every(1).minutes.do(self.check_inventory)  # 每1分钟

# 其他示例:
schedule.every(30).seconds.do(self.check_inventory)  # 每30秒
schedule.every(5).minutes.do(self.check_inventory)   # 每5分钟
```

### 访问私密库存

如果好友的库存设置为私密,需要:
1. 安装 Selenium: `pip install selenium`
2. 下载 ChromeDriver 并配置路径
3. 修改代码使用 `get_inventory_by_selenium()` 方法
4. 需要预先登录Steam账号

## 文件说明

- `steam_inventory_monitor.py` - 主程序
- `inventory_data.json` - 自动生成,保存历史库存数据
- `requirements.txt` - 依赖包列表

## 后台运行

### Windows
使用任务计划程序或创建批处理文件:
```batch
@echo off
python steam_inventory_monitor.py
```

### Linux/Mac
使用 screen 或 nohup:
```bash
nohup python steam_inventory_monitor.py > monitor.log 2>&1 &
```

或配置为系统服务(systemd)

## 注意事项

1. **访问频率**: Steam有速率限制,建议不要低于30秒检查一次
2. **网络环境**: 如果无法访问Steam,可能需要配置代理
3. **库存权限**: 仅能监控公开库存,除非使用Selenium登录
4. **Token安全**: 不要将推送token泄露给他人

## 故障排查

### 获取库存失败
- 检查Steam ID是否正确
- 确认库存设置为公开
- 检查网络连接

### 推送通知失败
- 确认token配置正确
- 检查推送服务是否正常
- 查看控制台错误信息

### 程序崩溃
- 查看错误日志
- 确认Python版本 >= 3.6
- 检查依赖包是否安装完整

## 高级功能

如需定制化开发,可扩展以下功能:
- 监控多个好友
- 数据库存储历史记录
- Web界面展示
- 价格变化监控
- 交易历史分析

## 开源协议

MIT License
