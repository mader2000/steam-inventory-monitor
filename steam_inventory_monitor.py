#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam好友库存监控程序
功能: 每分钟检查Steam好友库存,发现变化时发送手机通知
"""

import requests
import json
import time
import schedule
from datetime import datetime
from pathlib import Path

class SteamInventoryMonitor:
    def __init__(self, steam_id, api_key=None, push_token=None):
        """
        初始化监控器
        :param steam_id: Steam好友的64位ID
        :param api_key: Steam API密钥(可选,用于API访问)
        :param push_token: 推送服务的token
        """
        self.steam_id = steam_id
        self.api_key = api_key
        self.push_token = push_token
        self.data_file = Path("inventory_data.json")
        self.previous_inventory = self.load_previous_inventory()
        
    def load_previous_inventory(self):
        """加载上次保存的库存数据"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_inventory(self, inventory):
        """保存当前库存数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, ensure_ascii=False, indent=2)
    
    def get_inventory_by_api(self, app_id=730, context_id=2):
        """
        通过Steam API获取库存(推荐方式)
        :param app_id: 游戏ID (730=CS:GO, 440=TF2, 570=Dota2)
        :param context_id: 上下文ID (通常为2)
        :return: 库存数据字典
        """
        url = f"https://steamcommunity.com/inventory/{self.steam_id}/{app_id}/{context_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'assets' in data:
                    # 提取关键信息: assetid, classid, amount
                    inventory = {
                        item['assetid']: {
                            'classid': item['classid'],
                            'amount': item['amount'],
                            'instanceid': item.get('instanceid', '0')
                        }
                        for item in data['assets']
                    }
                    
                    # 同时保存描述信息用于通知
                    if 'descriptions' in data:
                        self.descriptions = {
                            f"{desc['classid']}_{desc['instanceid']}": desc
                            for desc in data['descriptions']
                        }
                    
                    return inventory
            else:
                print(f"[错误] 获取库存失败,状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"[错误] 请求异常: {e}")
            return None
    
    def get_inventory_by_selenium(self):
        """
        通过Selenium获取库存(备用方式,需要登录)
        适用于私密库存或需要登录才能查看的情况
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # 访问库存页面
            url = f"https://steamcommunity.com/profiles/{self.steam_id}/inventory/"
            driver.get(url)
            
            # 等待库存加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "inventory_page"))
            )
            
            # 执行JS获取库存数据
            inventory_data = driver.execute_script("return g_ActiveInventory.rgInventory;")
            
            return inventory_data if inventory_data else {}
            
        except Exception as e:
            print(f"[错误] Selenium获取失败: {e}")
            return None
        finally:
            driver.quit()
    
    def compare_inventory(self, current, previous):
        """
        比较库存变化
        :return: 新增物品, 移除物品, 数量变化
        """
        current_ids = set(current.keys())
        previous_ids = set(previous.keys())
        
        # 新增的物品
        added = {k: current[k] for k in (current_ids - previous_ids)}
        
        # 移除的物品
        removed = {k: previous[k] for k in (previous_ids - current_ids)}
        
        # 数量变化的物品
        changed = {}
        for item_id in (current_ids & previous_ids):
            if current[item_id]['amount'] != previous[item_id]['amount']:
                changed[item_id] = {
                    'old_amount': previous[item_id]['amount'],
                    'new_amount': current[item_id]['amount']
                }
        
        return added, removed, changed
    
    def get_item_name(self, classid, instanceid):
        """根据classid和instanceid获取物品名称"""
        key = f"{classid}_{instanceid}"
        if hasattr(self, 'descriptions') and key in self.descriptions:
            return self.descriptions[key].get('market_hash_name', '未知物品')
        return f"物品ID: {classid}"
    
    def send_notification(self, message):
        """
        发送手机通知
        支持多种推送服务,可根据需要选择
        """
        if not self.push_token:
            print("[提示] 未配置推送token,仅控制台输出")
            print(f"[通知] {message}")
            return
        
        # 方案1: PushPlus (推荐,免费)
        self.send_pushplus(message)
        
        # 方案2: Server酱 (备选)
        # self.send_serverchan(message)
        
        # 方案3: Bark (iOS专用)
        # self.send_bark(message)
    
    def send_pushplus(self, message):
        """使用PushPlus发送通知 (http://www.pushplus.plus/)"""
        url = "http://www.pushplus.plus/send"
        data = {
            "token": self.push_token,
            "title": "Steam库存变化通知",
            "content": message,
            "template": "html"
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                print("[成功] 通知已发送")
            else:
                print(f"[失败] 发送通知失败: {response.text}")
        except Exception as e:
            print(f"[错误] 发送通知异常: {e}")
    
    def send_serverchan(self, message):
        """使用Server酱发送通知 (https://sct.ftqq.com/)"""
        url = f"https://sctapi.ftqq.com/{self.push_token}.send"
        data = {
            "title": "Steam库存变化通知",
            "desp": message
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            print("[成功] Server酱通知已发送" if response.status_code == 200 else f"[失败] {response.text}")
        except Exception as e:
            print(f"[错误] 发送通知异常: {e}")
    
    def send_bark(self, message):
        """使用Bark发送通知 (iOS) (https://bark.day.app/)"""
        # push_token格式: 设备密钥
        url = f"https://api.day.app/{self.push_token}/Steam库存变化/{message}"
        try:
            response = requests.get(url, timeout=10)
            print("[成功] Bark通知已发送" if response.status_code == 200 else f"[失败] {response.text}")
        except Exception as e:
            print(f"[错误] 发送通知异常: {e}")
    
    def format_changes_message(self, added, removed, changed):
        """格式化变化信息为消息"""
        message_parts = []
        
        if added:
            message_parts.append(f"<h3>🎁 新增物品 ({len(added)}件):</h3><ul>")
            for item_id, item_data in added.items():
                name = self.get_item_name(item_data['classid'], item_data['instanceid'])
                message_parts.append(f"<li>{name} x{item_data['amount']}</li>")
            message_parts.append("</ul>")
        
        if removed:
            message_parts.append(f"<h3>📤 移除物品 ({len(removed)}件):</h3><ul>")
            for item_id, item_data in removed.items():
                name = self.get_item_name(item_data['classid'], item_data['instanceid'])
                message_parts.append(f"<li>{name} x{item_data['amount']}</li>")
            message_parts.append("</ul>")
        
        if changed:
            message_parts.append(f"<h3>🔄 数量变化 ({len(changed)}件):</h3><ul>")
            for item_id, change_data in changed.items():
                current_item = self.previous_inventory.get(item_id, {})
                name = self.get_item_name(current_item.get('classid'), current_item.get('instanceid'))
                message_parts.append(
                    f"<li>{name}: {change_data['old_amount']} → {change_data['new_amount']}</li>"
                )
            message_parts.append("</ul>")
        
        return "".join(message_parts)
    
    def check_inventory(self):
        """检查库存并对比变化"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] 开始检查库存...")
        
        # 获取当前库存
        current_inventory = self.get_inventory_by_api()
        
        if current_inventory is None:
            print("[警告] 获取库存失败,跳过本次检查")
            return
        
        print(f"[信息] 当前库存物品数: {len(current_inventory)}")
        
        # 如果是第一次运行
        if not self.previous_inventory:
            print("[提示] 首次运行,保存初始库存")
            self.save_inventory(current_inventory)
            self.previous_inventory = current_inventory
            return
        
        # 对比变化
        added, removed, changed = self.compare_inventory(current_inventory, self.previous_inventory)
        
        # 如果有变化,发送通知
        if added or removed or changed:
            print(f"[发现变化] 新增:{len(added)}, 移除:{len(removed)}, 变化:{len(changed)}")
            
            message = f"<p>检测时间: {timestamp}</p>"
            message += self.format_changes_message(added, removed, changed)
            
            self.send_notification(message)
            
            # 更新保存的库存
            self.save_inventory(current_inventory)
            self.previous_inventory = current_inventory
        else:
            print("[无变化] 库存未发生变化")
    
    def start_monitoring(self):
        """启动定时监控"""
        print("=" * 60)
        print("Steam库存监控程序已启动")
        print(f"监控Steam ID: {self.steam_id}")
        print(f"检查间隔: 每1分钟")
        print(f"推送状态: {'已配置' if self.push_token else '未配置'}")
        print("=" * 60)
        
        # 首次立即执行
        self.check_inventory()
        
        # 设置每分钟执行一次
        schedule.every(1).minutes.do(self.check_inventory)
        
        # 保持运行
        while True:
            schedule.run_pending()
            time.sleep(1)


def main():
    """主函数 - 配置并启动监控"""
    
    # ========== 配置区域 ==========
    # 必填: Steam好友的64位ID (在好友的个人资料页面URL中)
    STEAM_ID = "76561199088392199"  # 请替换为实际的Steam ID
    
    # 可选: Steam API密钥 (从 https://steamcommunity.com/dev/apikey 获取)
    STEAM_API_KEY = None  # 目前直接访问公开库存不需要
    
    # 必填(推荐): 推送服务Token
    # 选项1: PushPlus - 访问 http://www.pushplus.plus/ 获取token
    # 选项2: Server酱 - 访问 https://sct.ftqq.com/ 获取SendKey
    # 选项3: Bark - iOS用户可使用 Bark App
    PUSH_TOKEN = "6bf65b2c8966446794c740a45765a9c8"  # 请替换为实际的token
    
    # ========== 配置结束 ==========
    
    # 创建监控器实例
    monitor = SteamInventoryMonitor(
        steam_id=STEAM_ID,
        api_key=STEAM_API_KEY,
        push_token=PUSH_TOKEN
    )
    
    # 启动监控
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n[退出] 程序已停止")
    except Exception as e:
        print(f"\n[错误] 程序异常: {e}")


if __name__ == "__main__":
    main()
