import requests
import json
base = 'http://127.0.0.1:8000'

def pretty(r):
    try:
        return json.dumps(r.json(), ensure_ascii=False)
    except Exception:
        return r.text

print('registering user...')
r = requests.post(base+'/auth/register', json={'email':'test@example.com','password':'secret'})
print('status', r.status_code, pretty(r))

print('logging in...')
r = requests.post(base+'/auth/login', json={'email':'test@example.com','password':'secret'})
print('status', r.status_code, pretty(r))

if r.status_code==200:
    token = r.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    print('\ncreating tariff...')
    r2 = requests.post(base+'/tariffs/', json={'id':1,'name':'basic','price':100}, headers=headers)
    print('tariff create status', r2.status_code, pretty(r2))
    print('\nassign tariff...')
    r3 = requests.post(base+f'/auth/assign_tariff?user_id=1', json={'tariff_id':1}, headers=headers)
    print('assign status', r3.status_code, pretty(r3))
    print('\nget /auth/me')
    r4 = requests.get(base+'/auth/me', headers=headers)
    print('me status', r4.status_code, pretty(r4))
else:
    print('login failed, cannot continue')
