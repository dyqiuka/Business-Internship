import requests

api_key = "AIzaSyDxv-FfnzSWA1ma6NaI4itkWNgQl9_l1ig"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
headers = {'Content-Type': 'application/json'}
data = {
    "contents": [{"parts": [{"text": "Xin chào Gemini"}]}]
}

print("Đang gọi Google API...")
response = requests.post(url, headers=headers, json=data)
print(f"Mã trạng thái: {response.status_code}")
print(f"Kết quả: {response.text}")
