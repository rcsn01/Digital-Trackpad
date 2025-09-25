#!/usr/bin/env python3
"""
萬能PC遙控器 - 功能測試腳本
用於驗證應用程式的各項功能是否正常運作
"""

import requests
import json
import time
import sys

def test_server_connection():
    """測試伺服器連接"""
    print("🔍 測試伺服器連接...")
    try:
        response = requests.get('http://localhost:5001', timeout=5)
        if response.status_code == 200:
            print("✅ 伺服器連接成功")
            return True
        else:
            print(f"❌ 伺服器返回錯誤狀態碼: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 無法連接到伺服器: {e}")
        return False

def test_api_endpoints():
    """測試API端點"""
    print("\n🔍 測試API端點...")
    
    endpoints = [
        ('/keyboard', 'POST', {'keys': ['ctrl', 'a']}),
        ('/media', 'POST', {'action': 'play_pause'}),
        ('/presentation', 'POST', {'action': 'next'}),
        ('/app', 'POST', {'app': 'calculator'}),
        ('/system', 'POST', {'action': 'sleep'})
    ]
    
    success_count = 0
    
    for endpoint in endpoints:
        url = f'http://localhost:5001{endpoint[0]}'
        method = endpoint[1]
        data = endpoint[2] if len(endpoint) > 2 else None
        
        try:
            if method == 'GET':
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, json=data, timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"✅ {method} {endpoint[0]} - 成功")
                success_count += 1
            else:
                print(f"⚠️  {method} {endpoint[0]} - 狀態碼: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {method} {endpoint[0]} - 錯誤: {e}")
    
    print(f"\n📊 API測試完成: {success_count}/{len(endpoints)} 個端點正常")
    return success_count == len(endpoints)

def test_homepage():
    """測試主頁面功能 - 從網頁介面測試"""
    try:
        # 測試載入主頁面
        response = requests.get('http://localhost:5001/', timeout=5)
        
        if response.status_code == 200:
            print("✅ 主頁面載入成功")
            
            # 檢查頁面內容是否包含關鍵元素
            content = response.text
            if '觸控板' in content and '媒體控制' in content:
                print("✅ 主頁面內容完整")
                return True
            else:
                print("⚠️  主頁面內容可能不完整")
                return False
        else:
            print(f"❌ 主頁面載入失敗: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 主頁面測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始測試萬能PC遙控器...")
    print("=" * 50)
    
    # 檢查伺服器是否運行
    if not test_server_connection():
        print("\n❌ 請先啟動伺服器: python app.py")
        sys.exit(1)
    
    # 測試API端點
    api_test_passed = test_api_endpoints()
    
    # 測試自訂按鈕
    homepage_passed = test_homepage()
    
    print("\n" + "=" * 50)
    print("📋 測試總結:")
    print(f"伺服器連接: {'✅ 通過' if True else '❌ 失敗'}")
    print(f"API端點: {'✅ 全部通過' if api_test_passed else '⚠️  部分失敗'}")
    print(f"主頁面功能: {'✅ 通過' if homepage_passed else '❌ 失敗'}")
    
    if api_test_passed and homepage_passed:
        print("\n🎉 所有測試通過！應用程式運作正常。")
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤訊息。")

if __name__ == "__main__":
    main()