import requests, json
base = 'http://127.0.0.1:8000'

def pretty(r):
    try:
        return json.dumps(r.json(), ensure_ascii=False)
    except:
        return r.text

print('register user...')
r = requests.post(base+'/auth/register', json={'email':'user@example.com','password':'pwd'})
print('user register', r.status_code, pretty(r))
print('register admin...')
r = requests.post(base+'/auth/register', json={'email':'admin@example.com','password':'pwd'})
print('admin register', r.status_code, pretty(r))

# promote admin via new endpoint; if PROMOTE_SECRET is set on server, provide it as the 'secret' query param
# otherwise current implementation requires an existing admin to promote; since no admin exists yet, server may accept secret.
print('promote admin (bootstrap) ...')
# we don't have the admin token yet; use a dummy token header if needed. The endpoint accepts secret param for bootstrapping.
PROMOTE_SECRET = 'bootstrap-secret'
promote_resp = requests.post(base + '/auth/admin/promote?user_id=2', params={'secret': PROMOTE_SECRET})
print('promote admin response', promote_resp.status_code, pretty(promote_resp))

print('login user...')
r = requests.post(base+'/auth/login', json={'email':'user@example.com','password':'pwd'})
user_token = r.json().get('access_token')
print('user login', r.status_code, pretty(r))

print('login admin...')
r = requests.post(base+'/auth/login', json={'email':'admin@example.com','password':'pwd'})
admin_token = r.json().get('access_token')
print('admin login', r.status_code, pretty(r))

# create tariff as admin
headers_admin = {'Authorization': f'Bearer {admin_token}'}
r = requests.post(base+'/tariffs/', json={'id':2,'name':'pro','price':500}, headers=headers_admin)
print('create tariff', r.status_code, pretty(r))

# user tries to assign tariff -> should 403
headers_user = {'Authorization': f'Bearer {user_token}'}
r = requests.post(base+f"/auth/assign_tariff?user_id=1", json={'tariff_id':2}, headers=headers_user)
print('user assign attempt', r.status_code, pretty(r))

# admin assigns tariff -> should success
r = requests.post(base+f"/auth/assign_tariff?user_id=1", json={'tariff_id':2}, headers=headers_admin)
print('admin assign attempt', r.status_code, pretty(r))

r = requests.get(base+'/auth/me', headers=headers_admin)
print('/auth/me (admin)', r.status_code, pretty(r))
