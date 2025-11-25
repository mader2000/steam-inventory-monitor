#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam库存监控程序 - GitHub Actions版本
专为GitHub Actions环境优化,单次执行
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path

class SteamInventoryMonitor:
    def __init__(self, steam_id, push_token=None):
        self.steam_id = steam_id
        self.push_token = push_token
        self.data_file = Path("inventory_data.json")
        self.previous_inventory = self.load_previous_inventory()
        self.descriptions = {}
        
    def load_previous_inventory(self):
        """从GitHub Artifacts或本地加载上次保存的库存数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_inventory(self, inventory):
        """保存当前库存数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, ensure_ascii=False, indent=2)
    
    def get_inventory_by_api(self, app_id=730, context_id=2):
        """通过Steam API获取库存"""
        url = f"https://steamcommunity.com/inventory/{self.steam_id}/{app_id}/{context_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'assets' in data:
                    inventory = {
                        item['assetid']: {
                            'classid': item['classid'],
                            'amount': item['amount'],
                            'instanceid': item.get('instanceid', '0')
                        }
                        for item in data['assets']
                    }
                    
                    if 'descriptions' in data:
                        self.descriptions = {
                            f"{desc['classid']}_{desc['instanceid']}": desc
                            for desc in data['descriptions']
                        }
                    
                    return inventory
            else:
                print(f"❌ 获取库存失败,状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None
    
    def compare_inventory(self, current, previous):
        """比较库存变化"""
        current_ids = set(current.keys())
        previous_ids = set(previous.keys())
        
        added = {k: current[k] for k in (current_ids - previous_ids)}
        removed = {k: previous[k] for k in (previous_ids - current_ids)}
        
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
        if key in self.descriptions:
            return self.descriptions[key].get('market_hash_name', '未知物品')
        return f"物品ID: {classid}"
    
    def send_pushplus(self, message):
        """使用PushPlus发送通知"""
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
                print("✅ 通知已发送")
            else:
                print(f"❌ 发送通知失败: {response.text}")
        except Exception as e:
            print(f"❌ 发送通知异常: {e}")
    
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
        """检查库存并对比变化 - 单次执行版本"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"⏰ [{timestamp}] 开始检查库存...")
        print(f"{'='*60}")
        
        current_inventory = self.get_inventory_by_api()
        
        if current_inventory is None:
            print("⚠️  获取库存失败,跳过本次检查")
            return
        
        print(f"📦 当前库存物品数: {len(current_inventory)}")
        
        if not self.previous_inventory:
            print("🆕 首次运行,保存初始库存")
            self.save_inventory(current_inventory)
            return
        
        added, removed, changed = self.compare_inventory(current_inventory, self.previous_inventory)
        
        if added or removed or changed:
            print(f"🔍 发现变化! 新增:{len(added)}, 移除:{len(removed)}, 变化:{len(changed)}")
            
            message = f"<p>⏰ 检测时间: {timestamp}</p>"
            message += self.format_changes_message(added, removed, changed)
            
            if self.push_token:
                self.send_pushplus(message)
            else:
                print("⚠️  未配置推送token,仅控制台输出")
                print(message.replace('<h3>', '\n').replace('</h3>', '').replace('<ul>', '').replace('</ul>', '').replace('<li>', '  • ').replace('</li>', '').replace('<p>', '').replace('</p>', ''))
            
            self.save_inventory(current_inventory)
            print("✅ 库存数据已更新")
        else:
            print("✨ 库存未发生变化")
        
        print(f"{'='*60}\n")


def main():
    """主函数 - GitHub Actions版本"""
    
    # 从环境变量读取配置
    steam_id = os.environ.get('STEAM_ID')
    push_token = os.environ.get('PUSH_TOKEN')
    
    if not steam_id:
        print("❌ 错误: 未设置 STEAM_ID 环境变量")
        print("请在GitHub仓库设置中添加 Secrets:")
        print("  Settings -> Secrets and variables -> Actions -> New repository secret")
        exit(1)
    
    print("🚀 Steam库存监控程序 - GitHub Actions版本")
    print(f"📋 监控Steam ID: {steam_id}")
    print(f"📱 推送状态: {'已配置' if push_token else '未配置'}")
    
    monitor = SteamInventoryMonitor(
        steam_id=steam_id,
        push_token=push_token
    )
    
    try:
        monitor.check_inventory()
        print("✅ 执行完成")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        exit(1)


if __name__ == "__main__":
    main()
