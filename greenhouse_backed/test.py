s = '''POST /api/adp610/data HTTP/1.1
Host: shijie-smartline.club
Content-Type: application/json
Content-Length: 54

{"temp":26.5,"hum":60.2,"soil":45.0,"water":18.0,"co2":420,"flame":0,"pump":1}
'''
print(len(s.encode('utf-8')))  # 输出字节数