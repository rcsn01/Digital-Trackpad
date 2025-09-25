#!/usr/bin/env python3
"""
測試應用程式連結功能
驗證 Chrome、VS Code、記事本、計算機、檔案總管的連結是否正確
"""

import requests
import json
import time

def test_app_links():
    """測試所有應用程式連結"""
    base_url = "http://localhost:5001"
    
    # 測試的應用程式
    apps_to_test = [
        'chrome',
        'vscode', 
        'notepad',
        'calculator',
        'explorer',
        'task_manager'
    ]
    
    print("🚀 開始測試應用程式連結...")
    print("=" * 50)
    
    # 首先測試服務器連接
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ 服務器連接成功")
        else:
            print(f"❌ 服務器返回狀態碼: {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ 無法連接到服務器: {e}")
        return
    
    print("\n🔍 測試應用程式控制 API...")
    
    success_count = 0
    total_count = len(apps_to_test)
    
    for app_name in apps_to_test:
        print(f"\n📱 測試 {app_name}...")
        
        try:
            # 發送應用程式控制請求
            response = requests.post(
                f"{base_url}/app",
                json={"app": app_name},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"✅ {app_name} - 成功")
                    success_count += 1
                else:
                    print(f"❌ {app_name} - 失敗: {result.get('message', '未知錯誤')}")
            else:
                print(f"❌ {app_name} - HTTP 錯誤: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {app_name} - 請求錯誤: {e}")
        
        # 等待一下再測試下一個，避免太快
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {success_count}/{total_count} 個應用程式連結成功")
    
    if success_count == total_count:
        print("🎉 所有應用程式連結測試通過！")
    else:
        print("⚠️  部分應用程式連結需要檢查")

if __name__ == '__main__':
    test_app_links()