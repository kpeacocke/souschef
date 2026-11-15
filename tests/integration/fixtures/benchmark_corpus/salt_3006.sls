# Salt 3006 state syntax.
nginx:
  pkg.installed:
    - name: nginx

nginx_service:
  service.running:
    - name: nginx
    - enable: true
    - require:
      - pkg: nginx
