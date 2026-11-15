base:
  'web-*':
    - web.nginx
    - common.users
  'G@os_family:Debian':
    - match: compound
    - common.base
