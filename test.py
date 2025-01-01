import os
import requests
import certifi

# 시스템 인증서와 certifi 인증서 모두 설정
os.environ['SSL_CERT_FILE'] = '/etc/ssl/cert.pem'
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# requests 설정에서 직접 인증서 경로 지정
response = requests.get('https://api.github.com', 
    verify='/etc/ssl/cert.pem',
    headers={'User-Agent': 'DellIDRACMonitor'}
)